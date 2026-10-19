from decimal import Decimal
from django.contrib.auth import authenticate
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, serializers
from rest_framework.authtoken.models import Token
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .geo import CO2_KG_PER_KM, DEMO_SPEED_KMH, RATES, ROAD_FACTOR, km, lerp
from .models import KYC, Booking, PartnerProfile, Ride, User, Vehicle


# ---------- auth ----------
class RegisterSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)
    password = serializers.CharField(min_length=6, write_only=True)
    name = serializers.CharField(required=False, allow_blank=True)
    role = serializers.ChoiceField(choices=["renter", "partner"], default="renter")

    def validate_phone(self, v):
        if User.objects.filter(phone=v).exists():
            raise serializers.ValidationError("Phone already registered")
        return v

    def create(self, d):
        return User.objects.create_user(username=d["phone"], phone=d["phone"], password=d["password"],
                                        first_name=d.get("name", ""), role=d["role"])


def auth_payload(user):
    token, _ = Token.objects.get_or_create(user=user)
    return {"token": token.key, "role": user.role}


class RegisterView(APIView):  # TODO: replace password signup with phone OTP (Firebase/MSG91)
    permission_classes = [permissions.AllowAny]

    def post(self, r):
        s = RegisterSerializer(data=r.data)
        s.is_valid(raise_exception=True)
        return Response(auth_payload(s.save()), 201)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, r):
        u = authenticate(username=r.data.get("phone"), password=r.data.get("password"))
        if not u:
            return Response({"detail": "Invalid phone or password"}, 400)
        return Response(auth_payload(u))


# ---------- renter KYC ----------
class KYCView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def get(self, r):
        k = getattr(r.user, "kyc", None)
        return Response({"status": k.status if k else "none"})

    def post(self, r):
        if "document" not in r.data or "selfie" not in r.data:
            return Response({"detail": "document and selfie are required"}, 400)
        k, _ = KYC.objects.update_or_create(user=r.user, defaults={
            "doc_type": r.data.get("doc_type", "licence"), "document": r.data["document"],
            "selfie": r.data["selfie"], "status": "pending"})
        return Response({"status": k.status}, 201)


# ---------- vehicles & bookings ----------
class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = ["id", "name", "vtype", "reg_number", "daily_price", "deposit", "hub", "lat", "lng",
                  "status", "approved"]
        read_only_fields = ["status", "approved"]


def available(kind=None):
    qs = Vehicle.objects.filter(approved=True, status="available", partner__status="approved")
    if kind == "4w":
        return qs.filter(vtype="car")
    return qs.exclude(vtype="car") if kind == "2w" else qs


class VehicleList(APIView):
    """Public. ?kind=2w|4w&lat=..&lng=.. returns vehicles with distance_km, nearest first."""
    permission_classes = [permissions.AllowAny]

    def get(self, r):
        data = VehicleSerializer(available(r.query_params.get("kind")), many=True).data
        try:
            lat, lng = float(r.query_params["lat"]), float(r.query_params["lng"])
        except (KeyError, ValueError):
            lat = lng = None
        for d in data:
            d["distance_km"] = round(km(lat, lng, d["lat"], d["lng"]), 1) if lat is not None and d["lat"] is not None else None
        if lat is not None:
            data.sort(key=lambda d: (d["distance_km"] is None, d["distance_km"] or 0))
        return Response(data)


class BookingSerializer(serializers.ModelSerializer):
    vehicle_name = serializers.CharField(source="vehicle.name", read_only=True)

    class Meta:
        model = Booking
        fields = ["id", "vehicle", "vehicle_name", "days", "amount", "deposit", "status", "started_at", "ended_at"]
        read_only_fields = ["amount", "deposit", "status", "started_at", "ended_at"]


class BookingListCreate(generics.ListCreateAPIView):
    serializer_class = BookingSerializer

    def get_queryset(self):
        return Booking.objects.filter(renter=self.request.user).order_by("-created_at")

    def perform_create(self, s):
        u = self.request.user
        if getattr(getattr(u, "kyc", None), "status", None) != "approved":
            raise serializers.ValidationError("KYC not approved yet")
        v = s.validated_data["vehicle"]
        if v.status != "available" or not v.approved:
            raise serializers.ValidationError("Vehicle not available")
        # TODO: take payment (Razorpay) before confirming; lock the row to avoid double booking
        s.save(renter=u, amount=v.daily_price * s.validated_data["days"], deposit=v.deposit)
        v.status = "rented"
        v.save(update_fields=["status"])


class BookingAction(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, r, pk, action):
        b = get_object_or_404(Booking, pk=pk, renter=r.user)
        if action == "pickup":
            if b.status != "booked":
                return Response({"detail": "Booking is not waiting for pickup"}, 400)
            if str(b.vehicle.qr_token) != r.data.get("qr_token"):
                return Response({"detail": "QR code does not match this vehicle"}, 400)
            b.pickup_photo, b.status, b.started_at = r.data.get("photo"), "active", timezone.now()
        elif action == "return":
            if b.status != "active":
                return Response({"detail": "Booking is not active"}, 400)
            b.return_photo, b.status, b.ended_at = r.data.get("photo"), "completed", timezone.now()
            b.vehicle.status = "available"
            b.vehicle.save(update_fields=["status"])
        else:
            return Response(status=404)
        b.save()
        return Response(BookingSerializer(b).data)


# ---------- fleet partner onboarding ----------
class IsApprovedPartner(permissions.BasePermission):
    def has_permission(self, request, view):
        p = getattr(request.user, "partner", None)
        return bool(p and p.status == "approved")


class PartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartnerProfile
        fields = ["company_name", "city", "gst_number", "fleet_size", "agreement_accepted", "status",
                  "revenue_share_percent"]
        read_only_fields = ["status", "revenue_share_percent"]


class PartnerMe(APIView):
    def get(self, r):
        p = getattr(r.user, "partner", None)
        return Response(PartnerSerializer(p).data if p else {"status": "none"})

    def post(self, r):  # apply to become a partner; admin approves in the admin panel
        if hasattr(r.user, "partner"):
            return Response({"detail": "You have already applied"}, 400)
        s = PartnerSerializer(data=r.data)
        s.is_valid(raise_exception=True)
        if not s.validated_data.get("agreement_accepted"):
            return Response({"detail": "Please accept the partner agreement"}, 400)
        s.save(user=r.user)
        r.user.role = "partner"
        r.user.save(update_fields=["role"])
        return Response(s.data, 201)


class PartnerVehicles(generics.ListCreateAPIView):
    permission_classes = [IsApprovedPartner]
    serializer_class = VehicleSerializer

    def get_queryset(self):
        return Vehicle.objects.filter(partner=self.request.user.partner)

    def perform_create(self, s):
        s.save(partner=self.request.user.partner)  # approved=False until admin checks it


class PartnerEarnings(APIView):
    permission_classes = [IsApprovedPartner]

    def get(self, r):
        p = r.user.partner
        done = Booking.objects.filter(vehicle__partner=p, status="completed")
        gross = done.aggregate(t=Sum("amount"))["t"] or Decimal("0")
        return Response({
            "vehicles": p.vehicles.count(), "completed_bookings": done.count(),
            "active_bookings": Booking.objects.filter(vehicle__partner=p, status="active").count(),
            "gross": gross, "partner_share": gross * p.revenue_share_percent / 100})


# ---------- on-demand rides with (simulated) live tracking ----------
def _num(data, key):
    try:
        return float(data[key])
    except (KeyError, TypeError, ValueError):
        raise serializers.ValidationError({key: "A number is required"})


class RideView(APIView):
    def get(self, r):
        return Response([{"id": x.id, "kind": x.kind, "status": x.status, "fare": x.fare, "distance_km": x.distance_km,
                          "vehicle": x.vehicle.name, "created_at": x.created_at} for x in Ride.objects.filter(rider=r.user).order_by("-created_at")])

    def post(self, r):
        d = r.data
        kind = d.get("kind", "2w")
        if kind not in RATES:
            return Response({"detail": "kind must be 2w or 4w"}, 400)
        plat, plng, dlat, dlng = (_num(d, k) for k in ("pickup_lat", "pickup_lng", "drop_lat", "drop_lng"))
        dist = round(km(plat, plng, dlat, dlng) * ROAD_FACTOR, 1)
        if dist < 0.2:
            return Response({"detail": "Drop-off is too close to pickup"}, 400)
        cands = [v for v in available(kind) if v.lat is not None]
        if not cands:
            return Response({"detail": "No EV available nearby right now"}, 404)
        v = min(cands, key=lambda x: km(plat, plng, x.lat, x.lng))
        base, per = RATES[kind]
        d1 = round(km(v.lat, v.lng, plat, plng) * ROAD_FACTOR, 1)
        info = {"fare": round(base + per * dist), "distance_km": dist, "pickup_eta_min": round(d1 / DEMO_SPEED_KMH * 60, 1),
                "co2_saved_kg": round(dist * CO2_KG_PER_KM[kind], 2),
                "vehicle": {"id": v.id, "name": v.name, "vtype": v.vtype, "reg_number": v.reg_number, "distance_km": d1}}
        if d.get("estimate") in (True, "true", "1", 1):
            return Response(info)
        ride = Ride.objects.create(rider=r.user, vehicle=v, kind=kind, start_lat=v.lat, start_lng=v.lng, pickup_lat=plat, pickup_lng=plng,
                                   drop_lat=dlat, drop_lng=dlng, distance_km=dist, fare=info["fare"])
        v.status = "rented"
        v.save(update_fields=["status"])
        return Response({"id": ride.id, **info}, 201)


def _progress(ride):
    d1 = km(ride.start_lat, ride.start_lng, ride.pickup_lat, ride.pickup_lng) * ROAD_FACTOR
    total = d1 + ride.distance_km
    speed = DEMO_SPEED_KMH / 3600  # km per second (demo speed, so rides finish in minutes)
    return d1, total, speed, min((timezone.now() - ride.created_at).total_seconds() * speed, total)


class RideTrack(APIView):
    def get(self, r, pk):
        ride = get_object_or_404(Ride, pk=pk, rider=r.user)
        v = ride.vehicle
        d1, total, speed, done = _progress(ride)
        if ride.status == "cancelled":
            phase, lat, lng = "cancelled", ride.start_lat, ride.start_lng
        elif done < d1:
            phase, f = "arriving", done / d1
            lat, lng = lerp(ride.start_lat, ride.pickup_lat, f), lerp(ride.start_lng, ride.pickup_lng, f)
        elif done < total:
            phase, f = "on_trip", (done - d1) / ride.distance_km
            lat, lng = lerp(ride.pickup_lat, ride.drop_lat, f), lerp(ride.pickup_lng, ride.drop_lng, f)
        else:
            phase, lat, lng = "completed", ride.drop_lat, ride.drop_lng
            if ride.status != "completed":
                ride.status = "completed"
                ride.save(update_fields=["status"])
                v.status, v.lat, v.lng = "available", ride.drop_lat, ride.drop_lng
                v.save(update_fields=["status", "lat", "lng"])
        return Response({"phase": phase, "lat": lat, "lng": lng, "progress": round(done / total * 100) if total else 100,
                         "eta_seconds": max(0, round((total - done) / speed)), "fare": ride.fare, "distance_km": ride.distance_km,
                         "co2_saved_kg": round(ride.distance_km * CO2_KG_PER_KM[ride.kind], 2),
                         "vehicle": {"name": v.name, "vtype": v.vtype, "reg_number": v.reg_number}})


class RideCancel(APIView):
    def post(self, r, pk):
        ride = get_object_or_404(Ride, pk=pk, rider=r.user)
        d1, total, speed, done = _progress(ride)
        if ride.status != "assigned" or done >= d1:
            return Response({"detail": "This ride can no longer be cancelled"}, 400)
        ride.status = "cancelled"
        ride.save(update_fields=["status"])
        ride.vehicle.status = "available"
        ride.vehicle.save(update_fields=["status"])
        return Response({"status": "cancelled"})


class VehicleLocation(APIView):
    """GPS trackers / the partner app post live positions here."""
    permission_classes = [IsApprovedPartner]

    def post(self, r, pk):
        v = get_object_or_404(Vehicle, pk=pk, partner=r.user.partner)
        v.lat, v.lng = _num(r.data, "lat"), _num(r.data, "lng")
        v.save(update_fields=["lat", "lng"])
        return Response({"ok": True})

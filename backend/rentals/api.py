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

from .models import KYC, Booking, PartnerProfile, User, Vehicle


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


class VehicleList(generics.ListAPIView):
    serializer_class = VehicleSerializer
    queryset = Vehicle.objects.filter(approved=True, status="available", partner__status="approved")


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

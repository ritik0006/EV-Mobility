import hashlib
import hmac
import re
import secrets
from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.contrib.auth import authenticate
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, serializers
from rest_framework.authtoken.models import Token
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .geo import CO2_KG_PER_KM, DEMO_SPEED_KMH, RATES, ROAD_FACTOR, km, lerp
from .models import KYC, Booking, PartnerProfile, PhoneOTP, Ride, User, Vehicle


# ---------- auth ----------
class RegisterSerializer(serializers.Serializer):
    phone = serializers.RegexField(r"^[6-9]\d{9}$", error_messages={"invalid": "Enter a valid 10-digit mobile number"})
    password = serializers.CharField(min_length=8, write_only=True, error_messages={"min_length": "Password must be at least 8 characters"})
    email = serializers.EmailField(required=False, allow_blank=True)
    name = serializers.CharField(required=False, allow_blank=True, max_length=60)
    role = serializers.ChoiceField(choices=["renter", "partner"], default="renter")

    def validate_phone(self, v):
        if User.objects.filter(phone=v).exists():
            raise serializers.ValidationError("Phone already registered")
        return v

    def validate_email(self, v):
        if v and User.objects.filter(email__iexact=v).exists():
            raise serializers.ValidationError("Email already registered")
        return v.lower()

    def create(self, d):
        return User.objects.create_user(username=d["phone"], phone=d["phone"], password=d["password"], email=d.get("email", ""),
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
        ident = str(r.data.get("identifier") or r.data.get("phone") or "").strip()
        u = authenticate(username=ident.lower() if "@" in ident else ident, password=r.data.get("password"))
        if not u:
            return Response({"detail": "Wrong phone/email or password"}, 400)
        return Response(auth_payload(u))


# ---------- renter KYC ----------
class KYCView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def get(self, r):
        k = getattr(r.user, "kyc", None)
        return Response({"status": k.status if k else "none"})

    def post(self, r):
        if "document" not in r.data or "selfie" not in r.data:
            return Response({"detail": "Please upload your licence photo and a selfie"}, 400)
        for f in (r.data["document"], r.data["selfie"]):
            if not str(getattr(f, "content_type", "")).startswith("image/") or f.size > 5 * 1024 * 1024:
                return Response({"detail": "Upload clear photos (JPG or PNG, up to 5 MB each)"}, 400)
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
        k = getattr(r.user, "kyc", None)
        if not k or k.status == "rejected":
            return Response({"detail": "Complete your KYC first", "code": "KYC_REQUIRED"}, 400)
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
        if not r.user.phone_verified:
            return Response({"detail": "Verify your mobile number to book a ride", "code": "PHONE_NOT_VERIFIED"}, 403)
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


class GoogleLoginView(APIView):
    """Sign in / sign up with a Google ID token (from Google Identity Services on the website)."""
    permission_classes = [permissions.AllowAny]

    def post(self, r):
        if not settings.GOOGLE_CLIENT_ID:
            return Response({"detail": "Google sign-in is not set up yet"}, 503)
        try:
            from google.auth.transport import requests as grequests
            from google.oauth2 import id_token
            info = id_token.verify_oauth2_token(str(r.data.get("credential", "")), grequests.Request(), settings.GOOGLE_CLIENT_ID)
        except Exception as e:
            print("GOOGLE LOGIN ERROR:", repr(e), flush=True)
            return Response({"detail": "Google sign-in failed. Please try again."}, status=400)
        if not info.get("email_verified"):
            return Response({"detail": "Your Google email is not verified"}, 400)
        email = info["email"].lower()
        user, created = User.objects.get_or_create(username=email, defaults={"email": email, "first_name": info.get("given_name", ""), "role": "renter"})
        if created:
            user.set_unusable_password()
            user.save()
        return Response(auth_payload(user))


# ---------- mobile number OTP: phone login for everyone, and number verification for Google users ----------
PHONE_RE = re.compile(r"^[6-9]\d{9}$")


def _otp_hash(phone, code):
    return hashlib.sha256(f"{settings.SECRET_KEY}:{phone}:{code}".encode()).hexdigest()


def _twilio(path, data):
    import requests
    return requests.post(f"https://verify.twilio.com/v2/Services/{settings.TWILIO_VERIFY_SID}/{path}", data=data,
                         auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN), timeout=15)


def issue_otp(phone, user=None):
    """Send a code to `phone`. Demo mode returns it in the response; Twilio mode sends an SMS or WhatsApp message."""
    if not PHONE_RE.match(phone):
        return Response({"detail": "Enter a valid 10-digit mobile number"}, 400)
    mode = settings.OTP_PROVIDER
    if mode not in ("demo", "twilio"):
        return Response({"detail": "SMS service is not set up yet"}, 503)
    now = timezone.now()
    recent = PhoneOTP.objects.filter(phone=phone, created_at__gte=now - timedelta(hours=1)).order_by("-created_at")
    if recent.count() >= 5:
        return Response({"detail": "Too many codes requested. Try again in an hour."}, 429)
    if recent.first() and (now - recent.first().created_at).total_seconds() < 30:
        return Response({"detail": "Please wait 30 seconds before asking for a new code"}, 429)
    code = ""
    if mode == "twilio":
        try:
            ok = _twilio("Verifications", {"To": "+91" + phone, "Channel": settings.TWILIO_CHANNEL}).status_code in (200, 201)
        except Exception:
            ok = False
        if not ok:
            return Response({"detail": "Could not send the code. Please try again."}, 502)
    else:
        code = f"{secrets.randbelow(10 ** 6):06d}"
    PhoneOTP.objects.create(user=user, phone=phone, code_hash=_otp_hash(phone, code) if code else "")
    return Response({"sent": True, "expires_in": 300, **({"demo_otp": code} if mode == "demo" else {})})


def check_otp(phone, code):
    """Returns (ok, error message). Codes last 5 minutes and allow 5 tries."""
    code = str(code).strip()
    if not re.fullmatch(r"\d{6}", code):
        return False, "Enter the 6-digit code"
    otp = PhoneOTP.objects.filter(phone=phone, used=False).order_by("-created_at").first()
    if not otp or (timezone.now() - otp.created_at).total_seconds() > 300:
        return False, "Code expired. Please request a new one."
    if otp.attempts >= 5:
        return False, "Too many wrong attempts. Please request a new code."
    otp.attempts += 1
    if settings.OTP_PROVIDER == "twilio":
        try:
            ok = _twilio("VerificationCheck", {"To": "+91" + phone, "Code": code}).json().get("status") == "approved"
        except Exception:
            return False, "Could not check the code. Please try again."
    else:
        ok = hmac.compare_digest(otp.code_hash, _otp_hash(phone, code))
    if not ok:
        otp.save(update_fields=["attempts"])
        return False, "That code is not correct"
    otp.used = True
    otp.save(update_fields=["attempts", "used"])
    return True, ""


class OTPRequest(APIView):
    """Public. Step 1 of phone login (same for new and returning users)."""
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "otp"

    def post(self, r):
        return issue_otp(str(r.data.get("phone", "")).strip())


class OTPLogin(APIView):
    """Public. Step 2: a correct code logs the user in, creating the account on first use."""
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "otp"

    def post(self, r):
        phone = str(r.data.get("phone", "")).strip()
        ok, msg = check_otp(phone, r.data.get("code", ""))
        if not ok:
            return Response({"detail": msg}, 400)
        user = User.objects.filter(phone=phone).first() or User.objects.filter(username=phone).first()
        if not user:
            user = User.objects.create_user(username=phone, phone=phone)  # no password: customers sign in with OTP
        if not user.phone_verified or user.phone != phone:
            user.phone, user.phone_verified = phone, True
            user.save(update_fields=["phone", "phone_verified"])
        return Response({**auth_payload(user), "new": not user.first_name})


class MeView(APIView):
    def get(self, r):
        u, k = r.user, getattr(r.user, "kyc", None)
        return Response({"name": u.first_name, "phone": u.phone, "phone_verified": u.phone_verified, "role": u.role, "kyc": k.status if k else "none"})

    def post(self, r):  # set display name
        r.user.first_name = str(r.data.get("name", "")).strip()[:60]
        r.user.save(update_fields=["first_name"])
        return Response({"name": r.user.first_name})


class OTPSend(APIView):
    """Logged-in users (e.g. Google sign-in) who still need a verified number before their first ride."""

    def post(self, r):
        u = r.user
        phone = str(u.phone or r.data.get("phone") or "").strip()
        if User.objects.filter(phone=phone).exclude(pk=u.pk).exists():
            return Response({"detail": "This number already has an account. Log out and log in with this number instead."}, 400)
        return issue_otp(phone, u)


class OTPVerify(APIView):
    def post(self, r):
        u = r.user
        last = PhoneOTP.objects.filter(user=u).order_by("-created_at").first()
        phone = str(u.phone or (last.phone if last else "")).strip()
        ok, msg = check_otp(phone, r.data.get("code", ""))
        if not ok:
            return Response({"detail": msg}, 400)
        u.phone, u.phone_verified = phone, True
        u.save(update_fields=["phone", "phone_verified"])
        return Response({"verified": True, "phone": u.phone})

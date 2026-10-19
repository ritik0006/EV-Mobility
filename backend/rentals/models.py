import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLES = [("renter", "Renter"), ("partner", "Fleet partner")]
    phone = models.CharField(max_length=15, unique=True, null=True, blank=True)
    role = models.CharField(max_length=10, choices=ROLES, default="renter")


class KYC(models.Model):
    STATUS = [("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="kyc")
    doc_type = models.CharField(max_length=20, default="licence")
    document = models.FileField(upload_to="kyc/")
    selfie = models.FileField(upload_to="kyc/")
    status = models.CharField(max_length=10, choices=STATUS, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.status}"


class PartnerProfile(models.Model):
    STATUS = [("applied", "Applied"), ("approved", "Approved"), ("rejected", "Rejected")]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="partner")
    company_name = models.CharField(max_length=120)
    city = models.CharField(max_length=60)
    gst_number = models.CharField(max_length=20, blank=True)
    fleet_size = models.PositiveIntegerField(default=0)
    revenue_share_percent = models.DecimalField(max_digits=5, decimal_places=2, default=70)  # partner's share
    agreement_accepted = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=STATUS, default="applied")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.company_name


class Vehicle(models.Model):
    TYPES = [("scooter", "Scooter"), ("bike", "Bike"), ("car", "Car (4W)")]
    STATUS = [("available", "Available"), ("rented", "Rented"), ("maintenance", "Maintenance")]
    partner = models.ForeignKey(PartnerProfile, on_delete=models.CASCADE, related_name="vehicles")
    name = models.CharField(max_length=80)
    vtype = models.CharField(max_length=10, choices=TYPES, default="scooter")
    reg_number = models.CharField(max_length=20, unique=True)
    daily_price = models.DecimalField(max_digits=8, decimal_places=2)
    deposit = models.DecimalField(max_digits=8, decimal_places=2, default=2000)
    hub = models.CharField(max_length=80, blank=True)
    lat = models.FloatField(null=True, blank=True)  # updated from GPS tracker later
    lng = models.FloatField(null=True, blank=True)
    qr_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    status = models.CharField(max_length=12, choices=STATUS, default="available")
    approved = models.BooleanField(default=False)  # admin must approve partner vehicles

    def __str__(self):
        return f"{self.name} ({self.reg_number})"


class Booking(models.Model):
    STATUS = [("booked", "Booked"), ("active", "Active"), ("completed", "Completed"), ("cancelled", "Cancelled")]
    renter = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bookings")
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name="bookings")
    days = models.PositiveIntegerField(default=1)
    amount = models.DecimalField(max_digits=9, decimal_places=2)
    deposit = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=STATUS, default="booked")
    pickup_photo = models.FileField(upload_to="handover/", null=True, blank=True)
    return_photo = models.FileField(upload_to="handover/", null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Ride(models.Model):
    STATUS = [("assigned", "Assigned"), ("completed", "Completed"), ("cancelled", "Cancelled")]
    rider = models.ForeignKey(User, on_delete=models.CASCADE, related_name="rides")
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name="rides")
    kind = models.CharField(max_length=2, default="2w")  # 2w or 4w
    start_lat = models.FloatField()  # where the vehicle was when booked
    start_lng = models.FloatField()
    pickup_lat = models.FloatField()
    pickup_lng = models.FloatField()
    drop_lat = models.FloatField()
    drop_lng = models.FloatField()
    distance_km = models.FloatField()
    fare = models.IntegerField()
    status = models.CharField(max_length=10, choices=STATUS, default="assigned")
    created_at = models.DateTimeField(auto_now_add=True)

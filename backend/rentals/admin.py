from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import KYC, Booking, PartnerProfile, Ride, User, Vehicle

admin.site.site_header = "EV Rent Admin"


@admin.register(User)
class EvUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("EV Rent", {"fields": ("phone", "role")}),)
    list_display = ("username", "phone", "role", "is_staff")


@admin.register(KYC)
class KYCAdmin(admin.ModelAdmin):
    list_display = ("user", "doc_type", "status", "created_at")
    list_filter = ("status",)
    actions = ["approve", "reject"]

    @admin.action(description="Approve selected KYC")
    def approve(self, request, qs):
        qs.update(status="approved")

    @admin.action(description="Reject selected KYC")
    def reject(self, request, qs):
        qs.update(status="rejected")


@admin.register(PartnerProfile)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ("company_name", "city", "fleet_size", "revenue_share_percent", "status")
    list_filter = ("status", "city")
    actions = ["approve", "reject"]

    @admin.action(description="Approve selected partners")
    def approve(self, request, qs):
        qs.update(status="approved")

    @admin.action(description="Reject selected partners")
    def reject(self, request, qs):
        qs.update(status="rejected")


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("name", "reg_number", "partner", "hub", "daily_price", "status", "approved")
    list_filter = ("status", "approved", "vtype", "partner")
    readonly_fields = ("qr_token",)  # print this as the QR code stuck on the vehicle
    actions = ["approve"]

    @admin.action(description="Approve selected vehicles")
    def approve(self, request, qs):
        qs.update(approved=True)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "renter", "vehicle", "days", "amount", "status", "created_at")
    list_filter = ("status",)


admin.site.register(Ride)

from decimal import Decimal

from rest_framework.test import APITestCase

from .models import Booking, KYC, PartnerProfile, User, Vehicle


class RentalBookingWorkflowTests(APITestCase):
    def setUp(self):
        self.renter = User.objects.create_user(
            username="renter-1",
            password="test-password-123",
            phone="9876543210",
        )
        KYC.objects.create(
            user=self.renter,
            document="kyc/test-document.jpg",
            selfie="kyc/test-selfie.jpg",
            status="approved",
        )
        self.partner_user = User.objects.create_user(
            username="partner-1",
            password="test-password-123",
            phone="9876543211",
            role="partner",
        )
        self.partner = PartnerProfile.objects.create(
            user=self.partner_user,
            company_name="Test Fleet",
            city="Noida",
            fleet_size=1,
            agreement_accepted=True,
            status="approved",
        )
        self.vehicle = Vehicle.objects.create(
            partner=self.partner,
            name="Test Electric Scooter",
            vtype="scooter",
            reg_number="UP16TEST01",
            daily_price=Decimal("500.00"),
            deposit=Decimal("2000.00"),
            status="available",
            approved=True,
        )

    def test_renter_can_create_booking_and_vehicle_becomes_unavailable(self):
        self.client.force_authenticate(self.renter)
        response = self.client.post(
            "/api/bookings/",
            {"vehicle": self.vehicle.pk, "days": 2},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, "rented")
        booking = Booking.objects.get(pk=response.data["id"])
        self.assertEqual(booking.amount, Decimal("1000.00"))
        self.assertEqual(booking.deposit, Decimal("2000.00"))

    def test_second_booking_is_rejected_while_vehicle_is_reserved(self):
        self.client.force_authenticate(self.renter)
        first = self.client.post(
            "/api/bookings/",
            {"vehicle": self.vehicle.pk, "days": 1},
            format="json",
        )
        self.assertEqual(first.status_code, 201)

        second_renter = User.objects.create_user(
            username="renter-2",
            password="test-password-123",
            phone="9876543212",
        )
        KYC.objects.create(
            user=second_renter,
            document="kyc/test-document-2.jpg",
            selfie="kyc/test-selfie-2.jpg",
            status="approved",
        )
        self.client.force_authenticate(second_renter)
        second = self.client.post(
            "/api/bookings/",
            {"vehicle": self.vehicle.pk, "days": 1},
            format="json",
        )
        self.assertEqual(second.status_code, 400)
        self.assertEqual(Booking.objects.filter(vehicle=self.vehicle).count(), 1)

    def test_renter_can_cancel_unpicked_booking_and_release_vehicle(self):
        booking = Booking.objects.create(
            renter=self.renter,
            vehicle=self.vehicle,
            days=1,
            amount=Decimal("500.00"),
            deposit=Decimal("2000.00"),
            status="booked",
        )
        self.vehicle.status = "rented"
        self.vehicle.save(update_fields=["status"])

        self.client.force_authenticate(self.renter)
        response = self.client.post(f"/api/bookings/{booking.pk}/cancel/")

        self.assertEqual(response.status_code, 200)
        booking.refresh_from_db()
        self.vehicle.refresh_from_db()
        self.assertEqual(booking.status, "cancelled")
        self.assertEqual(self.vehicle.status, "available")

    def test_renter_cannot_cancel_an_active_booking(self):
        booking = Booking.objects.create(
            renter=self.renter,
            vehicle=self.vehicle,
            days=1,
            amount=Decimal("500.00"),
            deposit=Decimal("2000.00"),
            status="active",
        )
        self.client.force_authenticate(self.renter)
        response = self.client.post(f"/api/bookings/{booking.pk}/cancel/")

        self.assertEqual(response.status_code, 400)
        booking.refresh_from_db()
        self.assertEqual(booking.status, "active")

    def test_partner_can_only_list_own_fleet_bookings(self):
        booking = Booking.objects.create(
            renter=self.renter,
            vehicle=self.vehicle,
            days=1,
            amount=Decimal("500.00"),
            deposit=Decimal("2000.00"),
        )
        self.client.force_authenticate(self.partner_user)
        response = self.client.get("/api/partner/bookings/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.data], [booking.pk])

    def test_booking_days_must_be_between_one_and_thirty(self):
        self.client.force_authenticate(self.renter)
        response = self.client.post(
            "/api/bookings/",
            {"vehicle": self.vehicle.pk, "days": 31},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Booking.objects.count(), 0)

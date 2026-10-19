from django.core.management.base import BaseCommand
from rentals.models import KYC, PartnerProfile, User, Vehicle

VEHICLES = [  # name, type, reg, price/day, deposit, hub, lat, lng (approximate)
    ("Volt S1 Scooter", "scooter", "UP16-DEMO-01", 299, 2000, "Knowledge Park, Greater Noida", 28.4744, 77.5040),
    ("Volt S2 Scooter", "scooter", "UP16-DEMO-02", 349, 2500, "Sector 62, Noida", 28.6270, 77.3650),
    ("Spark B1 Bike", "bike", "UP16-DEMO-03", 399, 3000, "Sector 18 Metro, Noida", 28.5700, 77.3219),
    ("Spark B2 Bike", "bike", "UP16-DEMO-04", 449, 3500, "Alpha 1, Greater Noida", 28.4700, 77.5100),
    ("Volt S3 Scooter", "scooter", "UP16-DEMO-05", 249, 1500, "Sector 125, Noida", 28.5450, 77.3340),
    ("Volt C1 Hatchback", "car", "UP16-DEMO-C1", 1299, 6000, "Sector 62, Noida", 28.6280, 77.3660),
    ("Volt C2 Sedan", "car", "UP16-DEMO-C2", 1499, 8000, "Sector 18 Metro, Noida", 28.5710, 77.3230),
    ("Spark C3 SUV", "car", "UP16-DEMO-C3", 1999, 10000, "Knowledge Park, Greater Noida", 28.4750, 77.5050),
]


class Command(BaseCommand):
    help = "Create demo partner, renter and vehicles (safe to run repeatedly). Demo password: demo1234"

    def handle(self, *args, **opts):
        partner, created = User.objects.get_or_create(username="9000000001", defaults={"phone": "9000000001", "role": "partner", "first_name": "Demo Partner"})
        if created:
            partner.set_password("demo1234")
            partner.save()
        profile, _ = PartnerProfile.objects.get_or_create(user=partner, defaults={
            "company_name": "GreenWheels Fleet", "city": "Noida", "fleet_size": 5, "agreement_accepted": True, "status": "approved"})
        renter, created = User.objects.get_or_create(username="9000000002", defaults={"phone": "9000000002", "role": "renter", "first_name": "Demo Renter"})
        if created:
            renter.set_password("demo1234")
            renter.save()
        KYC.objects.get_or_create(user=renter, defaults={"doc_type": "licence", "document": "kyc/demo.txt", "selfie": "kyc/demo.txt", "status": "approved"})
        for name, vtype, reg, price, dep, hub, lat, lng in VEHICLES:
            Vehicle.objects.get_or_create(reg_number=reg, defaults={
                "partner": profile, "name": name, "vtype": vtype, "daily_price": price, "deposit": dep,
                "hub": hub, "lat": lat, "lng": lng, "approved": True})
        self.stdout.write(self.style.SUCCESS("Demo data ready: partner 9000000001 / renter 9000000002 (password demo1234)"))

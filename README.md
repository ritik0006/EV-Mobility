# EV Rent MVP (Flutter + Django)

Renter app, admin panel (Django admin) and fleet partner onboarding.

## Backend
```
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```
Admin panel: http://localhost:8000/admin (approve KYC, partners and vehicles; edit partner revenue share).
The vehicle `qr_token` is shown in the vehicle page; print it as the QR/code stuck on each scooter.

## Flutter app
```
flutter create ev_rent_app
# copy flutter_app/lib and flutter_app/pubspec.yaml into ev_rent_app (replace the originals)
cd ev_rent_app && flutter pub get && flutter run
```
- Android emulator reaches your PC at `10.0.2.2` (set in `lib/api.dart`). On a real phone use your PC's LAN IP.
- For plain-HTTP dev, add `android:usesCleartextTraffic="true"` to `<application>` in `android/app/src/main/AndroidManifest.xml`, and add the CAMERA permission.
- iOS: add `NSCameraUsageDescription` to `Info.plist`.

## Flow
1. Partner signs up (toggle "fleet partner") -> applies -> admin approves in /admin -> partner adds vehicles -> admin approves vehicles.
2. Renter signs up -> uploads KYC -> admin approves -> books -> picks up (vehicle code + photo) -> returns (photo).
3. Partner dashboard shows vehicles, active/completed rides, gross and the partner's revenue share.

## Not built yet (next)
Phone OTP login, Razorpay payments and deposit refunds, real QR scanning (mobile_scanner), GPS tracker feed into `lat/lng`, push notifications, double-booking row locks, production settings (PostgreSQL, secrets, HTTPS, private media storage).

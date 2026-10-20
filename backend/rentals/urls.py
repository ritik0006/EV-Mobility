from django.urls import path
from . import api

urlpatterns = [
    path("auth/register/", api.RegisterView.as_view()),
    path("auth/login/", api.LoginView.as_view()),
    path("auth/google/", api.GoogleLoginView.as_view()),
    path("auth/me/", api.MeView.as_view()),
    path("auth/otp/request/", api.OTPRequest.as_view()),
    path("auth/otp/login/", api.OTPLogin.as_view()),
    path("auth/otp/send/", api.OTPSend.as_view()),
    path("auth/otp/verify/", api.OTPVerify.as_view()),
    path("kyc/", api.KYCView.as_view()),
    path("vehicles/", api.VehicleList.as_view()),
    path("vehicles/<int:pk>/location/", api.VehicleLocation.as_view()),
    path("rides/", api.RideView.as_view()),
    path("rides/<int:pk>/track/", api.RideTrack.as_view()),
    path("rides/<int:pk>/cancel/", api.RideCancel.as_view()),
    path("bookings/", api.BookingListCreate.as_view()),
    path("bookings/<int:pk>/<slug:action>/", api.BookingAction.as_view()),
    path("partner/me/", api.PartnerMe.as_view()),
    path("partner/vehicles/", api.PartnerVehicles.as_view()),
    path("partner/earnings/", api.PartnerEarnings.as_view()),
]

from django.urls import path
from . import api

urlpatterns = [
    path("auth/register/", api.RegisterView.as_view()),
    path("auth/login/", api.LoginView.as_view()),
    path("kyc/", api.KYCView.as_view()),
    path("vehicles/", api.VehicleList.as_view()),
    path("bookings/", api.BookingListCreate.as_view()),
    path("bookings/<int:pk>/<slug:action>/", api.BookingAction.as_view()),
    path("partner/me/", api.PartnerMe.as_view()),
    path("partner/vehicles/", api.PartnerVehicles.as_view()),
    path("partner/earnings/", api.PartnerEarnings.as_view()),
]

from django.conf import settings
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.urls import include, path, re_path
from django.views.static import serve


def home(request):  # also used as Render's health check
    return JsonResponse({"service": "EV Rent API", "status": "ok", "admin": "/admin/", "api": "/api/"})


urlpatterns = [
    path("", home),
    path("admin/", admin.site.urls),
    path("api/", include("rentals.urls")),
    # Uploaded KYC / handover photos are private: only logged-in admin staff can open them.
    re_path(r"^media/(?P<path>.*)$", staff_member_required(serve), {"document_root": settings.MEDIA_ROOT}),
]

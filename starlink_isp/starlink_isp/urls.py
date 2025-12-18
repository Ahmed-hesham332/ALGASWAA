"""
URL configuration for starlink_isp project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("", include("landing.urls")), # Root URL
    path('starlink-admin/', admin.site.urls),
    path("accounts/", include("account.urls")),
    path("servers/", include("servers.urls")),
    path("vouchers/", include("vouchers.urls")),
    path("offers/", include("offers.urls")),
    path("online/", include("online.urls")),
    path("design/", include("design.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("adminpanel/", include("adminpanel.urls")), 
    path("profile/", include("profiles.urls")),
    path("income/", include("income.urls")),
    path("radius-integration/", include("radius_integration.urls")),
    path("distributers/", include("distributers.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


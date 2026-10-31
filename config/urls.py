from django.contrib import admin
from django.urls import include, path

from billing.dashboard import dashboard

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("catalog/", include("catalog.urls")),
    path("subscriptions/", include("subscriptions.urls")),
    path("invoices/", include("billing.urls")),
     path("dashboard/", dashboard, name="dashboard"),
]
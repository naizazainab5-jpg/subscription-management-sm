from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("catalog/", include("catalog.urls")),
    path("subscriptions/", include("subscriptions.urls")),
    path("invoices/", include("billing.urls")),
]
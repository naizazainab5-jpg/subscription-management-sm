from django.urls import path

from . import views

urlpatterns = [
    path("", views.invoice_list, name="invoice_list"),
    path("run/", views.run_billing, name="run_billing"),
    path("<int:pk>/", views.invoice_detail, name="invoice_detail"),
    path("<int:pk>/confirm/", views.invoice_confirm, name="invoice_confirm"),
    path("<int:pk>/cancel/", views.invoice_cancel, name="invoice_cancel"),
    path("<int:pk>/pay/", views.payment_add, name="payment_add"),
]

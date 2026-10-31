from django.urls import path

from . import views

urlpatterns = [
    path("products/", views.product_list, name="product_list"),
    path("products/new/", views.product_edit, name="product_create"),
    path("products/<int:pk>/edit/", views.product_edit, name="product_edit"),
    path("products/<int:pk>/delete/", views.product_delete, name="product_delete"),
    path("plans/", views.plan_list, name="plan_list"),
    path("plans/new/", views.plan_edit, name="plan_create"),
    path("plans/<int:pk>/edit/", views.plan_edit, name="plan_edit"),
    path("plans/<int:pk>/delete/", views.plan_delete, name="plan_delete"),
        path("taxes/", views.tax_list, name="tax_list"),
    path("taxes/new/", views.tax_edit, name="tax_create"),
    path("taxes/<int:pk>/edit/", views.tax_edit, name="tax_edit"),
    path("taxes/<int:pk>/delete/", views.tax_delete, name="tax_delete"),
        path("discounts/", views.discount_list, name="discount_list"),
    path("discounts/new/", views.discount_edit, name="discount_create"),
    path("discounts/<int:pk>/edit/", views.discount_edit, name="discount_edit"),
    path("discounts/<int:pk>/delete/", views.discount_delete, name="discount_delete"),
]
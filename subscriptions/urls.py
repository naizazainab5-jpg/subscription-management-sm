from django.urls import path

from . import views

urlpatterns = [
    path("", views.subscription_list, name="subscription_list"),
    path("mine/", views.my_subscriptions, name="my_subscriptions"),
    path("new/", views.subscription_create, name="subscription_create"),
    path("from-template/", views.subscription_from_template, name="subscription_from_template"),
    path("<int:pk>/", views.subscription_detail, name="subscription_detail"),
    path("<int:pk>/edit/", views.subscription_edit, name="subscription_edit"),
    path("<int:pk>/status/", views.subscription_change_status, name="subscription_change_status"),
]
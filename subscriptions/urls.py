from django.urls import path

from . import views

urlpatterns = [
    path("", views.subscription_list, name="subscription_list"),
    path("new/", views.subscription_create, name="subscription_create"),
    path("<int:pk>/edit/", views.subscription_edit, name="subscription_edit"),
]
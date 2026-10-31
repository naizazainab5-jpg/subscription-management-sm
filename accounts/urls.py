from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

FORM = "accounts/form_page.html"

urlpatterns = [
    path("", views.home, name="home"),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="accounts/login.html",
            authentication_form=views.EmailLoginForm,
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),
    path("signup/", views.signup, name="signup"),

    # Password reset (the email link prints in the terminal during development)
    path("password-reset/", auth_views.PasswordResetView.as_view(
        template_name=FORM,
        extra_context={"title": "Reset your password", "button": "Send reset link"}),
        name="password_reset"),
    path("password-reset/sent/", auth_views.PasswordResetDoneView.as_view(
        template_name=FORM,
        extra_context={"title": "Check your email",
                       "message": "If that email is registered, a reset link is on its way."}),
        name="password_reset_done"),
    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name=FORM,
        extra_context={"title": "Choose a new password", "button": "Save password"}),
        name="password_reset_confirm"),
    path("reset/done/", auth_views.PasswordResetCompleteView.as_view(
        template_name=FORM,
        extra_context={"title": "Password changed",
                       "message": "Your password has been updated. You can log in now."}),
        name="password_reset_complete"),
]
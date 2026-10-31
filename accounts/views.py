from django.contrib import messages
from functools import wraps
from django.contrib.auth.decorators import login_required, user_passes_test
from django import forms
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render

from .models import User


def role_required(*roles):
    """Usage: @role_required("admin", "staff"). Logged-out users go to login; wrong role gets 403."""
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapper(request, *args, **kwargs):
            if not request.user.is_superuser and request.user.role not in roles:
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return wrapper
    return decorator


class EmailLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Email"


class SignupForm(forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ("first_name", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 and p2:
            if p1 != p2:
                self.add_error("password2", "Passwords do not match.")
            else:
                try:
                    validate_password(p1, user=User(email=cleaned.get("email", "")))
                except forms.ValidationError as e:
                    self.add_error("password1", e)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = user.email      # this starter logs in with username
        user.role = "customer"          # signup always creates customers
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


def signup(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        auth_login(request, user)
        return redirect("home")
    return render(request, "accounts/signup.html", {"form": form})


@login_required
def home(request):
    invoices = []
    if request.user.role == "customer":
        from billing.models import Invoice
        invoices = (
            Invoice.objects.filter(customer=request.user)
            .select_related("subscription")
            .order_by("-issue_date")[:25]
        )
    return render(request, "accounts/home.html", {"invoices": invoices})
class StaffForm(SignupForm):
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = "staff"
        if commit:
            user.save()
        return user


@role_required("admin")
@login_required
@user_passes_test(lambda u: u.is_admin_role)
def add_staff(request):
    form = StaffForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.save()
        messages.success(
            request,
            f"Staff account created for {user.email}."
        )
        return redirect("add_staff")

    return render(
        request,
        "accounts/form_page.html",
        {
            "form": form,
            "title": "Add staff member",
            "button": "Create staff account"
        }
    )
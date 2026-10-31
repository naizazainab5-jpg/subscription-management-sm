from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Log in with username; set username = email at signup. Email is unique."""

    ADMIN, STAFF, CUSTOMER = "admin", "staff", "customer"
    ROLES = [(ADMIN, "Admin"), (STAFF, "Internal staff"), (CUSTOMER, "Customer")]

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=ROLES, default=CUSTOMER)

    @property
    def is_admin_role(self):
        return self.role == self.ADMIN or self.is_superuser

    @property
    def is_staff_role(self):
        return self.role in (self.ADMIN, self.STAFF) or self.is_superuser

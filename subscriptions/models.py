from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from catalog.models import Plan, Product, ProductVariant, Tax


class QuotationTemplate(models.Model):
    name = models.CharField(max_length=120)
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    validity_days = models.PositiveIntegerField(default=30)

    def __str__(self):
        return self.name


class QuotationTemplateLine(models.Model):
    template = models.ForeignKey(QuotationTemplate, related_name="lines", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    variant = models.ForeignKey(ProductVariant, null=True, blank=True, on_delete=models.SET_NULL)
    quantity = models.PositiveIntegerField(default=1)


class Subscription(models.Model):
    DRAFT, QUOTATION, CONFIRMED, ACTIVE, CLOSED = "draft", "quotation", "confirmed", "active", "closed"
    STATUSES = [(s, s.title()) for s in (DRAFT, QUOTATION, CONFIRMED, ACTIVE, CLOSED)]
    ALLOWED = {
        DRAFT: [QUOTATION],
        QUOTATION: [CONFIRMED, DRAFT],
        CONFIRMED: [ACTIVE],
        ACTIVE: [CLOSED],
        CLOSED: [],
    }

    number = models.CharField(max_length=20, unique=True, blank=True, editable=False)
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="subscriptions", on_delete=models.PROTECT)
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    start_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    payment_terms = models.CharField(max_length=100, default="Net 15")
    payment_days = models.PositiveIntegerField(default=15, help_text="Days until invoice is due")
    status = models.CharField(max_length=10, choices=STATUSES, default=DRAFT, db_index=True)
    next_billing_date = models.DateField(null=True, blank=True, db_index=True)

    def save(self, *args, **kwargs):
        if not self.next_billing_date:
            self.next_billing_date = self.start_date
        super().save(*args, **kwargs)
        if not self.number:
            self.number = f"SUB-{self.pk:05d}"
            super().save(update_fields=["number"])

    def change_status(self, new_status):
        if new_status not in self.ALLOWED[self.status]:
            raise ValidationError(f"Cannot go from {self.status} to {new_status}.")
        self.status = new_status
        self.save(update_fields=["status"])

    def __str__(self):
        return self.number or "New subscription"


class SubscriptionLine(models.Model):
    subscription = models.ForeignKey(Subscription, related_name="lines", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    variant = models.ForeignKey(ProductVariant, null=True, blank=True, on_delete=models.SET_NULL)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.ForeignKey(Tax, null=True, blank=True, on_delete=models.SET_NULL)

    @property
    def amount(self):
        return self.quantity * self.unit_price

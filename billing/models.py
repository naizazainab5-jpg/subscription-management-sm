from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Sum

from subscriptions.models import Subscription


class Invoice(models.Model):
    DRAFT, CONFIRMED, PAID, CANCELLED = "draft", "confirmed", "paid", "cancelled"
    STATUSES = [(s, s.title()) for s in (DRAFT, CONFIRMED, PAID, CANCELLED)]

    number = models.CharField(max_length=20, unique=True, blank=True, editable=False)
    subscription = models.ForeignKey(Subscription, related_name="invoices", on_delete=models.PROTECT)
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="invoices", on_delete=models.PROTECT)
    period_start = models.DateField()
    period_end = models.DateField()
    issue_date = models.DateField()
    due_date = models.DateField(db_index=True)
    status = models.CharField(max_length=10, choices=STATUSES, default=DRAFT, db_index=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        # Guarantees "nothing billed twice": one invoice per subscription per period.
        constraints = [models.UniqueConstraint(fields=["subscription", "period_start"], name="one_invoice_per_period")]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.number:
            self.number = f"INV-{self.pk:06d}"
            super().save(update_fields=["number"])

    @property
    def amount_paid(self):
        return self.payments.aggregate(s=Sum("amount"))["s"] or Decimal("0")

    @property
    def amount_due(self):
        return self.total - self.amount_paid

    def __str__(self):
        return self.number


class InvoiceLine(models.Model):
    invoice = models.ForeignKey(Invoice, related_name="lines", on_delete=models.CASCADE)
    description = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=12, decimal_places=2)  # negative for discounts


class Payment(models.Model):
    METHODS = [("card", "Card"), ("bank", "Bank transfer"), ("upi", "UPI"), ("cash", "Cash"), ("cheque", "Cheque")]

    invoice = models.ForeignKey(Invoice, related_name="payments", on_delete=models.PROTECT)
    method = models.CharField(max_length=10, choices=METHODS)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    note = models.CharField(max_length=255, blank=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        inv = self.invoice
        if inv.status == Invoice.CONFIRMED and inv.amount_paid >= inv.total:
            inv.status = Invoice.PAID
            inv.save(update_fields=["status"])

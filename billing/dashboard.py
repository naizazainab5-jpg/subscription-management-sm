from decimal import Decimal

from django import forms
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import render
from django.utils import timezone

from accounts.views import role_required
from subscriptions.models import Subscription

from .models import Invoice, Payment

MONEY = DecimalField(max_digits=14, decimal_places=2)
ZERO = Decimal("0")


class DashboardFilter(forms.Form):
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}, format="%Y-%m-%d"),
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}, format="%Y-%m-%d"),
    )
    status = forms.ChoiceField(
        required=False,
        choices=[("", "All statuses")] + list(Invoice.STATUSES),
        widget=forms.Select(attrs={"class": "form-select"}),
    )


def _with_amounts(queryset):
    """Add paid and due amounts to each invoice in ONE query (no loops)."""
    return (
        queryset.select_related("customer", "subscription")
        .annotate(paid=Coalesce(Sum("payments__amount"), Value(ZERO, output_field=MONEY), output_field=MONEY))
        .annotate(due=ExpressionWrapper(F("total") - F("paid"), output_field=MONEY))
    )


@role_required("admin", "staff")
def dashboard(request):
    today = timezone.localdate()
    form = DashboardFilter(request.GET or None)
    date_from = date_to = None
    status = ""
    if form.is_valid():
        date_from = form.cleaned_data["date_from"]
        date_to = form.cleaned_data["date_to"]
        status = form.cleaned_data["status"]

    payments = Payment.objects.all()
    invoices = Invoice.objects.all()
    if date_from:
        payments = payments.filter(date__gte=date_from)
        invoices = invoices.filter(issue_date__gte=date_from)
    if date_to:
        payments = payments.filter(date__lte=date_to)
        invoices = invoices.filter(issue_date__lte=date_to)

    # Subscriptions
    subscription_counts = {
        row["status"]: row["n"]
        for row in Subscription.objects.values("status").annotate(n=Count("id"))
    }
    active_subscriptions = subscription_counts.get(Subscription.ACTIVE, 0)

    # Revenue = money actually received
    pay = payments.aggregate(total=Sum("amount"), n=Count("id"))
    revenue = pay["total"] or ZERO

    # Outstanding = confirmed invoices minus what was paid on them
    confirmed = invoices.filter(status=Invoice.CONFIRMED)
    billed = confirmed.aggregate(t=Sum("total"))["t"] or ZERO
    received = Payment.objects.filter(invoice__in=confirmed).aggregate(t=Sum("amount"))["t"] or ZERO
    outstanding = billed - received

    # Overdue = confirmed and past the due date
    overdue_qs = confirmed.filter(due_date__lt=today)
    overdue_count = overdue_qs.count()
    overdue_billed = overdue_qs.aggregate(t=Sum("total"))["t"] or ZERO
    overdue_received = Payment.objects.filter(invoice__in=overdue_qs).aggregate(t=Sum("amount"))["t"] or ZERO
    overdue_amount = overdue_billed - overdue_received

    labels = dict(Invoice.STATUSES)
    invoice_breakdown = [
        {"label": labels.get(r["status"], r["status"]), "n": r["n"], "total": r["total"] or ZERO}
        for r in invoices.values("status").annotate(n=Count("id"), total=Sum("total")).order_by("status")
    ]

    shown = invoices.filter(status=status) if status else invoices
    overdue_rows = _with_amounts(overdue_qs).order_by("due_date")[:25]
    invoice_rows = _with_amounts(shown).order_by("-issue_date", "-id")[:25]
    recent_payments = payments.select_related("invoice").order_by("-date", "-id")[:10]

    return render(request, "billing/dashboard.html", {
        "form": form,
        "today": today,
        "active_subscriptions": active_subscriptions,
        "subscription_counts": subscription_counts,
        "revenue": revenue,
        "payment_count": pay["n"],
        "outstanding": outstanding,
        "overdue_count": overdue_count,
        "overdue_amount": overdue_amount,
        "invoice_breakdown": invoice_breakdown,
        "overdue_rows": overdue_rows,
        "invoice_rows": invoice_rows,
        "recent_payments": recent_payments,
    })
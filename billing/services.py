"""All billing logic lives here: generate_invoice(subscription)."""
from datetime import timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.utils import timezone

from catalog.models import Discount, Plan
from subscriptions.models import Subscription
from .models import Invoice, InvoiceLine

CENT = Decimal("0.01")


def add_period(d, period):
    return d + {
        Plan.DAILY: timedelta(days=1),
        Plan.WEEKLY: timedelta(weeks=1),
        Plan.MONTHLY: relativedelta(months=1),
        Plan.YEARLY: relativedelta(years=1),
    }[period]


def _discount_amount(disc, base):
    amt = base * disc.value / 100 if disc.kind == Discount.PERCENT else disc.value
    return min(amt, base).quantize(CENT)


@transaction.atomic
def generate_invoice(sub_id, today=None):
    """Create the invoice for the sub's current period. Returns None if nothing is due.
    Safe to run repeatedly: the lock + unique constraint prevent double billing."""
    today = today or timezone.localdate()
    sub = Subscription.objects.select_for_update().select_related("plan").get(pk=sub_id)

    if sub.status != Subscription.ACTIVE or sub.next_billing_date > today:
        return None
    if Invoice.objects.filter(subscription=sub, period_start=sub.next_billing_date).exists():
        return None

    period_start = sub.next_billing_date
    next_start = add_period(period_start, sub.plan.billing_period)
    inv = Invoice.objects.create(
        subscription=sub, customer=sub.customer,
        period_start=period_start, period_end=next_start - timedelta(days=1),
        issue_date=today, due_date=today + timedelta(days=sub.payment_days),
    )

    lines = list(sub.lines.select_related("product", "tax", "variant"))
    subtotal = tax_total = Decimal("0")
    for l in lines:
        amount = (l.amount).quantize(CENT)
        tax = (amount * l.tax.rate / 100).quantize(CENT) if l.tax else Decimal("0")
        InvoiceLine.objects.create(invoice=inv, description=str(l.product), quantity=l.quantity,
                                   unit_price=l.unit_price, tax_amount=tax, amount=amount)
        subtotal += amount
        tax_total += tax

    # Discounts apply automatically if active, in date range, under usage limit, thresholds met.
    discount_total = Decimal("0")
    for d in Discount.objects.filter(start_date__lte=today, end_date__gte=today):
        if d.usage_limit is not None and d.used_count >= d.usage_limit:
            continue
        if d.applies_to == Discount.PRODUCT:
            ids = set(d.products.values_list("id", flat=True))
            matched = [l for l in lines if l.product_id in ids]
        else:
            matched = lines
        base = sum((l.amount for l in matched), Decimal("0"))
        qty = sum(l.quantity for l in matched)
        if not matched or base < d.min_purchase or qty < d.min_quantity:
            continue
        amt = _discount_amount(d, base)
        InvoiceLine.objects.create(invoice=inv, description=f"Discount: {d.name}",
                                   quantity=1, unit_price=-amt, amount=-amt)
        discount_total += amt
        Discount.objects.filter(pk=d.pk).update(used_count=d.used_count + 1)

    inv.subtotal, inv.tax_total, inv.discount_total = subtotal, tax_total, discount_total
    inv.total = subtotal + tax_total - discount_total
    inv.status = Invoice.CONFIRMED
    inv.save()

    sub.next_billing_date = next_start
    if sub.expiry_date and next_start > sub.expiry_date and sub.plan.auto_close:
        sub.status = Subscription.CLOSED
    sub.save(update_fields=["next_billing_date", "status"])
    return inv

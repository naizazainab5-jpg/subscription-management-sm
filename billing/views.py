from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import DecimalField, ExpressionWrapper, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.views import role_required
from subscriptions.models import Subscription

from .forms import PaymentForm
from .models import Invoice
from .services import generate_invoice

MONEY = DecimalField(max_digits=12, decimal_places=2)

# Invoice -> Paid happens automatically when payments cover the total (Payment.save).
ALLOWED = {
    Invoice.DRAFT: [Invoice.CONFIRMED, Invoice.CANCELLED],
    Invoice.CONFIRMED: [Invoice.CANCELLED],
}


@role_required("admin", "staff")
def invoice_list(request):
    today = timezone.localdate()
    invoices = (
        Invoice.objects.select_related("customer", "subscription")
        .annotate(paid=Coalesce(Sum("payments__amount"), Value(Decimal("0"), output_field=MONEY), output_field=MONEY))
        .annotate(due=ExpressionWrapper(F("total") - F("paid"), output_field=MONEY))
        .order_by("-id")
    )
    status = request.GET.get("status", "")
    q = request.GET.get("q", "").strip()
    overdue = request.GET.get("overdue") == "1"

    if status in dict(Invoice.STATUSES):
        invoices = invoices.filter(status=status)
    else:
        status = ""
    if q:
        invoices = invoices.filter(Q(number__icontains=q) | Q(customer__email__icontains=q))
    if overdue:
        invoices = invoices.filter(status=Invoice.CONFIRMED, due_date__lt=today)

    page_obj = Paginator(invoices, 25).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "billing/invoice_list.html", {
        "page_obj": page_obj, "statuses": Invoice.STATUSES, "status": status,
        "q": q, "overdue": overdue, "today": today, "querystring": params.urlencode(),
    })


@login_required
def invoice_detail(request, pk):
    invoice = get_object_or_404(Invoice.objects.select_related("customer", "subscription"), pk=pk)
    # Customers can only ever open their OWN invoices.
    if not request.user.is_staff_role and invoice.customer_id != request.user.id:
        raise Http404
    payments = list(invoice.payments.order_by("date", "id"))
    paid = sum((p.amount for p in payments), Decimal("0"))
    due = invoice.total - paid
    today = timezone.localdate()
    staff = request.user.is_staff_role
    form = None
    if staff and invoice.status == Invoice.CONFIRMED and due > 0:
        form = PaymentForm(initial={"date": today, "amount": due})
    return render(request, "billing/invoice_detail.html", {
        "invoice": invoice, "lines": invoice.lines.all(), "payments": payments,
        "paid": paid, "due": due, "form": form, "staff": staff,
        "is_overdue": invoice.status == Invoice.CONFIRMED and invoice.due_date < today,
        "can_cancel": staff and invoice.status in (Invoice.DRAFT, Invoice.CONFIRMED) and not payments,
    })


def _move(request, pk, new_status, done_msg):
    invoice = get_object_or_404(Invoice, pk=pk)
    if new_status not in ALLOWED.get(invoice.status, []):
        messages.warning(request, f"Can't move an invoice from {invoice.status} to {new_status}.")
    elif new_status == Invoice.CANCELLED and invoice.payments.exists():
        messages.warning(request, "This invoice has payments and can't be cancelled.")
    else:
        invoice.status = new_status
        invoice.save(update_fields=["status"])
        messages.success(request, done_msg)
    return redirect("invoice_detail", pk=pk)


@role_required("admin", "staff")
@require_POST
def invoice_confirm(request, pk):
    return _move(request, pk, Invoice.CONFIRMED, "Invoice confirmed.")


@role_required("admin", "staff")
@require_POST
def invoice_cancel(request, pk):
    return _move(request, pk, Invoice.CANCELLED, "Invoice cancelled.")


@role_required("admin", "staff")
@require_POST
def payment_add(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    if invoice.status != Invoice.CONFIRMED:
        messages.warning(request, "Payments can only be recorded on confirmed invoices.")
        return redirect("invoice_detail", pk=pk)
    form = PaymentForm(request.POST)
    if form.is_valid():
        if form.cleaned_data["amount"] > invoice.amount_due:
            messages.error(request, f"Amount is more than the {invoice.amount_due} still due.")
        else:
            payment = form.save(commit=False)
            payment.invoice = invoice
            payment.save()  # marks the invoice Paid once fully covered
            messages.success(request, "Payment recorded.")
    else:
        for errs in form.errors.values():
            messages.error(request, " ".join(errs))
    return redirect("invoice_detail", pk=pk)


@role_required("admin", "staff")
@require_POST
def run_billing(request):
    today = timezone.localdate()
    ids = list(Subscription.objects.filter(
        status=Subscription.ACTIVE, next_billing_date__lte=today).values_list("id", flat=True))
    created = 0
    for sid in ids:
        for _ in range(24):  # catch up several missed periods, but never loop forever
            if not generate_invoice(sid, today):
                break
            created += 1
    messages.success(request, f"Billing run finished: {created} invoice(s) created.")
    return redirect("invoice_list")

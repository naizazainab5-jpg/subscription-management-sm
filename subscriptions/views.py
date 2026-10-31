from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.views import role_required
from catalog.models import Plan, Product, ProductVariant, Tax

from .forms import FromTemplateForm, LineFormSet, SubscriptionForm
from .models import Subscription, SubscriptionLine

ACTION_LABELS = {
    Subscription.QUOTATION: ("Send as quotation", "btn-info"),
    Subscription.CONFIRMED: ("Confirm", "btn-primary"),
    Subscription.DRAFT: ("Back to draft", "btn-outline-secondary"),
    Subscription.ACTIVE: ("Activate", "btn-success"),
    Subscription.CLOSED: ("Close subscription", "btn-danger"),
}


@role_required("admin", "staff")
def subscription_list(request):
    subscriptions = Subscription.objects.select_related("customer", "plan").order_by("-id")

    status = request.GET.get("status", "")
    q = request.GET.get("q", "").strip()

    if status in dict(Subscription.STATUSES):
        subscriptions = subscriptions.filter(status=status)
    else:
        status = ""

    if q:
        subscriptions = subscriptions.filter(
            Q(number__icontains=q) | Q(customer__email__icontains=q)
        )

    page_obj = Paginator(subscriptions, 25).get_page(request.GET.get("page"))

    params = request.GET.copy()
    params.pop("page", None)

    return render(request, "subscriptions/subscription_list.html", {
        "page_obj": page_obj,
        "statuses": Subscription.STATUSES,
        "status": status,
        "q": q,
        "querystring": params.urlencode(),
    })


def _price_data():
    """Prices the page's JavaScript needs to fill unit prices and totals."""
    variants = {}
    for v in ProductVariant.objects.all():
        variants.setdefault(str(v.product_id), []).append({
            "id": v.id,
            "label": f"{v.attribute}: {v.value} (+{v.extra_price})",
            "extra": str(v.extra_price),
        })
    return {
        "products": {str(p.id): str(p.sales_price) for p in Product.objects.all()},
        "variants": variants,
        "taxes": {str(t.id): str(t.rate) for t in Tax.objects.all()},
        "plans": {str(p.id): p.min_quantity for p in Plan.objects.all()},
    }


def _subscription_form_view(request, subscription=None):
    form = SubscriptionForm(request.POST or None, instance=subscription)
    formset = LineFormSet(request.POST or None, instance=subscription, prefix="lines")

    if request.method == "POST":
        form_ok = form.is_valid()
        if form_ok:
            formset.min_quantity = form.cleaned_data["plan"].min_quantity
        formset_ok = formset.is_valid()
        if form_ok and formset_ok:
            with transaction.atomic():
                saved = form.save()
                formset.instance = saved
                formset.save()
            return redirect("subscription_detail", pk=saved.pk)

    return render(request, "subscriptions/subscription_form.html", {
        "form": form,
        "formset": formset,
        "subscription": subscription,
        "price_data": _price_data(),
    })


@role_required("admin", "staff")
def subscription_create(request):
    return _subscription_form_view(request)


@role_required("admin", "staff")
def subscription_edit(request, pk):
    subscription = get_object_or_404(Subscription, pk=pk)
    if subscription.status not in (Subscription.DRAFT, Subscription.QUOTATION):
        messages.error(request, "Only Draft or Quotation subscriptions can be edited.")
        return redirect("subscription_detail", pk=pk)
    return _subscription_form_view(request, subscription)


@role_required("admin", "staff")
def subscription_from_template(request):
    form = FromTemplateForm(request.POST or None, initial={"start_date": timezone.localdate()})

    if request.method == "POST" and form.is_valid():
        template = form.cleaned_data["template"]
        start = form.cleaned_data["start_date"]
        template_lines = list(template.lines.select_related("product", "variant"))

        if not template_lines:
            form.add_error("template", "This template has no product lines. Add some in the admin first.")
        else:
            plan = template.plan
            with transaction.atomic():
                subscription = Subscription.objects.create(
                    customer=form.cleaned_data["customer"],
                    plan=plan,
                    start_date=start,
                    expiry_date=start + timedelta(days=template.validity_days),
                )
                SubscriptionLine.objects.bulk_create([
                    SubscriptionLine(
                        subscription=subscription,
                        product=line.product,
                        variant=line.variant,
                        quantity=max(line.quantity, plan.min_quantity),
                        unit_price=line.product.sales_price
                        + (line.variant.extra_price if line.variant else 0),
                    )
                    for line in template_lines
                ])
            return redirect("subscription_edit", pk=subscription.pk)

    return render(request, "subscriptions/subscription_from_template.html", {"form": form})


@login_required
def subscription_detail(request, pk):
    queryset = Subscription.objects.select_related("customer", "plan")
    is_staff = request.user.is_staff_role
    if not is_staff:
        queryset = queryset.filter(customer=request.user)  # others' subscriptions -> 404
    subscription = get_object_or_404(queryset, pk=pk)

    rows = []
    subtotal = tax_total = Decimal("0")
    for line in subscription.lines.select_related("product", "variant", "tax"):
        amount = line.amount
        tax_amount = amount * line.tax.rate / 100 if line.tax else Decimal("0")
        subtotal += amount
        tax_total += tax_amount
        rows.append({"line": line, "amount": amount, "tax_amount": tax_amount})

    actions = []
    if is_staff:
        for nxt in Subscription.ALLOWED[subscription.status]:
            label, css = ACTION_LABELS[nxt]
            actions.append({"value": nxt, "label": label, "css": css})

    return render(request, "subscriptions/subscription_detail.html", {
        "subscription": subscription,
        "rows": rows,
        "subtotal": subtotal,
        "tax_total": tax_total,
        "total": subtotal + tax_total,
        "actions": actions,
        "is_staff": is_staff,
        "can_edit": is_staff and subscription.status in (Subscription.DRAFT, Subscription.QUOTATION),
    })


@role_required("admin", "staff")
@require_POST
def subscription_change_status(request, pk):
    subscription = get_object_or_404(Subscription.objects.select_related("plan"), pk=pk)
    new_status = request.POST.get("status", "")
    plan = subscription.plan
    today = timezone.localdate()

    try:
        if new_status not in dict(Subscription.STATUSES):
            raise ValidationError("Unknown status.")
        if new_status == Subscription.ACTIVE and not subscription.lines.exists():
            raise ValidationError("Add at least one product line before activating.")
        if (
            new_status == Subscription.CLOSED
            and not plan.allow_early_close
            and (subscription.expiry_date is None or subscription.expiry_date > today)
        ):
            raise ValidationError("This plan does not allow closing early.")
        subscription.change_status(new_status)
        messages.success(request, f"{subscription.number} is now {subscription.get_status_display()}.")
    except ValidationError as error:
        messages.error(request, " ".join(error.messages))

    return redirect("subscription_detail", pk=pk)


@login_required
def my_subscriptions(request):
    subscriptions = (
        Subscription.objects.filter(customer=request.user)
        .select_related("plan")
        .order_by("-id")
    )
    return render(request, "subscriptions/my_subscriptions.html", {"subscriptions": subscriptions})
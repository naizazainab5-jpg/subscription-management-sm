from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.views import role_required
from catalog.models import Plan, Product, ProductVariant, Tax

from .forms import LineFormSet, SubscriptionForm
from .models import Subscription


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
            return redirect("subscription_list")

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
        return redirect("subscription_list")  # only draft/quotation can be edited
    return _subscription_form_view(request, subscription)
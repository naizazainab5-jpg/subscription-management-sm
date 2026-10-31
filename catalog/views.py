from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, ProtectedError, RestrictedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.views import role_required

from .forms import DiscountForm, PlanForm, ProductForm, TaxForm, VariantFormSet
from .models import Discount, Plan, Product, Tax


# ---------- Products ----------

@role_required("admin", "staff")
def product_list(request):
    q = request.GET.get("q", "").strip()
    products = Product.objects.annotate(variant_count=Count("variants")).order_by("name")
    if q:
        products = products.filter(name__icontains=q)
    page = Paginator(products, 25).get_page(request.GET.get("page"))
    return render(request, "catalog/product_list.html", {"page": page, "q": q})


@role_required("admin", "staff")
def product_edit(request, pk=None):
    product = get_object_or_404(Product, pk=pk) if pk else Product()
    form = ProductForm(request.POST or None, instance=product)
    formset = VariantFormSet(request.POST or None, instance=product)
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            product = form.save()
            formset.instance = product
            formset.save()
        messages.success(request, f"Product '{product.name}' saved.")
        return redirect("product_list")
    return render(request, "catalog/product_form.html", {
        "form": form, "formset": formset, "product": product if pk else None,
    })


@role_required("admin", "staff")
@require_POST
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    try:
        product.delete()
        messages.success(request, "Product deleted.")
    except (ProtectedError, RestrictedError):
        messages.warning(request, "This product is used in subscriptions and can't be deleted.")
    return redirect("product_list")


# ---------- Plans ----------

@role_required("admin", "staff")
def plan_list(request):
    q = request.GET.get("q", "").strip()
    plans = Plan.objects.order_by("name")
    if q:
        plans = plans.filter(name__icontains=q)
    page = Paginator(plans, 25).get_page(request.GET.get("page"))
    return render(request, "catalog/plan_list.html", {"page": page, "q": q})


@role_required("admin", "staff")
def plan_edit(request, pk=None):
    plan = get_object_or_404(Plan, pk=pk) if pk else None
    form = PlanForm(request.POST or None, instance=plan)
    if request.method == "POST" and form.is_valid():
        plan = form.save()
        messages.success(request, f"Plan '{plan.name}' saved.")
        return redirect("plan_list")
    return render(request, "catalog/plan_form.html", {"form": form, "plan": plan})


@role_required("admin", "staff")
@require_POST
def plan_delete(request, pk):
    plan = get_object_or_404(Plan, pk=pk)
    try:
        plan.delete()
        messages.success(request, "Plan deleted.")
    except (ProtectedError, RestrictedError):
        messages.warning(request, "This plan is used in subscriptions and can't be deleted.")
    return redirect("plan_list")
# ---------- Taxes ----------

@role_required("admin", "staff")
def tax_list(request):
    taxes = Tax.objects.order_by("name")
    page = Paginator(taxes, 25).get_page(request.GET.get("page"))
    return render(request, "catalog/tax_list.html", {"page": page})


@role_required("admin", "staff")
def tax_edit(request, pk=None):
    tax = get_object_or_404(Tax, pk=pk) if pk else None
    form = TaxForm(request.POST or None, instance=tax)
    if request.method == "POST" and form.is_valid():
        tax = form.save()
        messages.success(request, f"Tax '{tax.name}' saved.")
        return redirect("tax_list")
    return render(request, "catalog/tax_form.html", {"form": form, "tax": tax})


@role_required("admin", "staff")
@require_POST
def tax_delete(request, pk):
    tax = get_object_or_404(Tax, pk=pk)
    try:
        tax.delete()
        messages.success(request, "Tax deleted.")
    except (ProtectedError, RestrictedError):
        messages.warning(request, "This tax is used on subscription lines and can't be deleted.")
    return redirect("tax_list")
# ---------- Discounts ----------

@role_required("admin", "staff")
def discount_list(request):
    q = request.GET.get("q", "").strip()
    discounts = Discount.objects.order_by("name")
    if q:
        discounts = discounts.filter(name__icontains=q)
    page = Paginator(discounts, 25).get_page(request.GET.get("page"))
    return render(request, "catalog/discount_list.html", {"page": page, "q": q})


@role_required("admin", "staff")
def discount_edit(request, pk=None):
    discount = get_object_or_404(Discount, pk=pk) if pk else None
    form = DiscountForm(request.POST or None, instance=discount)
    if request.method == "POST" and form.is_valid():
        discount = form.save()
        messages.success(request, f"Discount '{discount.name}' saved.")
        return redirect("discount_list")
    return render(request, "catalog/discount_form.html", {"form": form, "discount": discount})


@role_required("admin", "staff")
@require_POST
def discount_delete(request, pk):
    discount = get_object_or_404(Discount, pk=pk)
    try:
        discount.delete()
        messages.success(request, "Discount deleted.")
    except (ProtectedError, RestrictedError):
        messages.warning(request, "This discount is in use and can't be deleted.")
    return redirect("discount_list")
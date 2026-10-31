from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, ProtectedError, RestrictedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.views import role_required

from .forms import PlanForm, ProductForm, VariantFormSet
from .models import Plan, Product


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
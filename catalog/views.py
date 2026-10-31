from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.views import role_required

from .forms import ProductForm, VariantFormSet
from .models import Product


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
    except ProtectedError:
        messages.warning(request, "This product is used in subscriptions and can't be deleted.")
    return redirect("product_list")
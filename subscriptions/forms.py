from django import forms
from django.contrib.auth import get_user_model
from django.forms import BaseInlineFormSet, inlineformset_factory

from catalog.models import Product, ProductVariant

from .models import Subscription, SubscriptionLine

User = get_user_model()


def style_fields(form):
    """Give every field a Bootstrap look."""
    for field in form.fields.values():
        widget = field.widget
        if isinstance(widget, forms.CheckboxInput):
            widget.attrs["class"] = "form-check-input"
        elif isinstance(widget, forms.Select):
            widget.attrs["class"] = "form-select"
        else:
            widget.attrs["class"] = "form-control"


class SubscriptionForm(forms.ModelForm):
    class Meta:
        model = Subscription
        fields = ["customer", "plan", "start_date", "expiry_date", "payment_terms", "payment_days"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "expiry_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["customer"].queryset = User.objects.filter(role="customer").order_by("email")
        self.fields["customer"].label_from_instance = lambda user: user.email
        style_fields(self)

    def clean(self):
        cleaned = super().clean()
        start, expiry = cleaned.get("start_date"), cleaned.get("expiry_date")
        if start and expiry and expiry < start:
            self.add_error("expiry_date", "Expiry date cannot be before the start date.")
        return cleaned


class SubscriptionLineForm(forms.ModelForm):
    class Meta:
        model = SubscriptionLine
        fields = ["product", "variant", "quantity", "unit_price", "tax"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["unit_price"].required = False  # filled automatically if empty
        self.fields["product"].queryset = Product.objects.order_by("name")
        self.fields["variant"].queryset = ProductVariant.objects.select_related("product")
        style_fields(self)

    def clean(self):
        cleaned = super().clean()
        product, variant = cleaned.get("product"), cleaned.get("variant")
        if product and variant and variant.product_id != product.id:
            self.add_error("variant", "This variant does not belong to the selected product.")
        if product and cleaned.get("unit_price") in (None, ""):
            extra = variant.extra_price if variant else 0
            cleaned["unit_price"] = product.sales_price + extra
        return cleaned


class BaseLineFormSet(BaseInlineFormSet):
    min_quantity = None  # the view sets this from the chosen plan

    def clean(self):
        super().clean()
        used = 0
        for form in self.forms:
            data = getattr(form, "cleaned_data", None)
            if not data or data.get("DELETE") or not data.get("product"):
                continue
            used += 1
            qty = data.get("quantity")
            if self.min_quantity and qty is not None and qty < self.min_quantity:
                form.add_error("quantity", f"Minimum quantity for this plan is {self.min_quantity}.")
        if used == 0:
            raise forms.ValidationError("Add at least one product line.")


LineFormSet = inlineformset_factory(
    Subscription,
    SubscriptionLine,
    form=SubscriptionLineForm,
    formset=BaseLineFormSet,
    extra=1,
    can_delete=True,
)
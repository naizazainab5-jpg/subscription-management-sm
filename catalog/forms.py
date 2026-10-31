from .models import Discount, Plan, Product, ProductVariant, Tax
from django import forms
from django.forms import inlineformset_factory

from .models import Plan, Product, ProductVariant


class BootstrapModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            else:
                field.widget.attrs["class"] = "form-control"


class ProductForm(BootstrapModelForm):
    class Meta:
        model = Product
        fields = ["name", "product_type", "sales_price", "cost_price", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}


class VariantForm(BootstrapModelForm):
    class Meta:
        model = ProductVariant
        fields = ["attribute", "value", "extra_price"]


VariantFormSet = inlineformset_factory(
    Product, ProductVariant, form=VariantForm, extra=2, can_delete=True
)


class PlanForm(BootstrapModelForm):
    class Meta:
        model = Plan
        fields = [
            "name", "price", "billing_period", "min_quantity",
            "start_date", "end_date",
            "auto_close", "allow_early_close", "allow_pause", "allow_renew",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "end_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }
        labels = {
            "auto_close": "Auto close when end date passes",
            "allow_early_close": "Allow early close",
            "allow_pause": "Allow pause",
            "allow_renew": "Allow renew",
        }

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("start_date"), cleaned.get("end_date")
        if start and end and end < start:
            self.add_error("end_date", "End date cannot be before the start date.")
        return cleaned
class TaxForm(BootstrapModelForm):
    class Meta:
        model = Tax
        fields = ["name", "rate"]

    def clean_rate(self):
        rate = self.cleaned_data["rate"]
        if rate < 0 or rate > 100:
            raise forms.ValidationError("Rate must be between 0 and 100.")
        return rate
class DiscountForm(BootstrapModelForm):
    class Meta:
        model = Discount
        fields = [
            "name", "kind", "value", "applies_to", "products",
            "min_purchase", "min_quantity", "start_date", "end_date", "usage_limit",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "end_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "products": forms.SelectMultiple(attrs={"size": 6}),
        }
        help_texts = {"products": "Only used when 'Applies to' is Specific products. Hold Ctrl to pick several."}

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("start_date"), cleaned.get("end_date")
        if start and end and end < start:
            self.add_error("end_date", "End date cannot be before the start date.")
        if cleaned.get("kind") == Discount.PERCENT and (cleaned.get("value") or 0) > 100:
            self.add_error("value", "A percentage cannot be more than 100.")
        if cleaned.get("applies_to") == Discount.PRODUCT and not cleaned.get("products"):
            self.add_error("products", "Pick at least one product.")
        return cleaned
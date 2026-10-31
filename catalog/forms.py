from django import forms
from django.forms import inlineformset_factory

from .models import Product, ProductVariant


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
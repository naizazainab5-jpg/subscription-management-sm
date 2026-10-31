from decimal import Decimal

from django import forms

from .models import Payment


class PaymentForm(forms.ModelForm):
    amount = forms.DecimalField(min_value=Decimal("0.01"), max_digits=12, decimal_places=2)

    class Meta:
        model = Payment
        fields = ["method", "amount", "date", "note"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs["class"] = "form-select" if isinstance(f.widget, forms.Select) else "form-control"
        self.fields["note"].required = False

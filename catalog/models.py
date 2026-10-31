from django.db import models


class Tax(models.Model):
    name = models.CharField(max_length=50)
    rate = models.DecimalField(max_digits=5, decimal_places=2, help_text="Percent, e.g. 18")

    def __str__(self):
        return f"{self.name} ({self.rate}%)"


class Product(models.Model):
    name = models.CharField(max_length=120)
    product_type = models.CharField(max_length=50)
    sales_price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.name


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, related_name="variants", on_delete=models.CASCADE)
    attribute = models.CharField(max_length=50, default="Brand")
    value = models.CharField(max_length=50)  # e.g. Odoo
    extra_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # e.g. 560

    def __str__(self):
        return f"{self.product} - {self.value} (+{self.extra_price})"


class Plan(models.Model):
    DAILY, WEEKLY, MONTHLY, YEARLY = "daily", "weekly", "monthly", "yearly"
    PERIODS = [(DAILY, "Daily"), (WEEKLY, "Weekly"), (MONTHLY, "Monthly"), (YEARLY, "Yearly")]

    name = models.CharField(max_length=120)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    billing_period = models.CharField(max_length=10, choices=PERIODS, default=MONTHLY)
    min_quantity = models.PositiveIntegerField(default=1)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    # Admin decides per plan:
    auto_close = models.BooleanField(default=False)
    allow_early_close = models.BooleanField(default=False)
    allow_pause = models.BooleanField(default=False)
    allow_renew = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.billing_period})"


class Discount(models.Model):
    FIXED, PERCENT = "fixed", "percent"
    PRODUCT, SUBSCRIPTION = "product", "subscription"

    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=10, choices=[(FIXED, "Fixed amount"), (PERCENT, "Percentage")])
    value = models.DecimalField(max_digits=10, decimal_places=2)
    applies_to = models.CharField(max_length=15, choices=[(PRODUCT, "Specific products"), (SUBSCRIPTION, "Whole subscription")])
    products = models.ManyToManyField(Product, blank=True)
    min_purchase = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    min_quantity = models.PositiveIntegerField(default=0)
    start_date = models.DateField()
    end_date = models.DateField()
    usage_limit = models.PositiveIntegerField(null=True, blank=True, help_text="Blank = unlimited")
    used_count = models.PositiveIntegerField(default=0, editable=False)

    def __str__(self):
        return self.name

import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from catalog.models import Plan, Product, ProductVariant, Tax
from subscriptions.models import Subscription, SubscriptionLine

User = get_user_model()
PREFIX = "DEMO-"


class Command(BaseCommand):
    help = "Create demo customers and Active subscriptions with lines. Safe to run again (adds more)."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=2000, help="How many subscriptions to add")

    def handle(self, *args, **options):
        count = options["count"]
        today = timezone.localdate()

        tax = Tax.objects.first() or Tax.objects.create(name="GST", rate=Decimal("18"))

        products = list(Product.objects.all())
        if not products:
            for name, price in (("Demo CRM", 1000), ("Demo Billing", 1500), ("Demo Support", 500)):
                products.append(Product.objects.create(
                    name=name, product_type="Software",
                    sales_price=Decimal(price), cost_price=Decimal(price) * Decimal("0.4"),
                ))

        plans = list(Plan.objects.all())
        if not plans:
            plans = [Plan.objects.create(
                name="Demo Monthly", price=Decimal("1000"), billing_period=Plan.MONTHLY,
                start_date=today - timedelta(days=365),
            )]

        variants = {}
        for v in ProductVariant.objects.all():
            variants.setdefault(v.product_id, []).append(v)

        last = (
            Subscription.objects.filter(number__startswith=PREFIX)
            .order_by("-number").values_list("number", flat=True).first()
        )
        first_index = int(last[len(PREFIX):]) + 1 if last else 1
        indexes = range(first_index, first_index + count)

        # Customers (one password hash is reused so this stays fast)
        password_hash = make_password("Test@12345")
        emails = {i: f"demo{i:06d}@demo.test" for i in indexes}
        User.objects.bulk_create(
            [
                User(username=email, email=email, first_name=f"Demo {i}", role="customer",
                     password=password_hash, is_active=True)
                for i, email in emails.items()
            ],
            batch_size=500, ignore_conflicts=True,
        )
        by_email = {u.email: u for u in User.objects.filter(email__in=list(emails.values()))}

        # Subscriptions (bulk_create skips save(), so number and next_billing_date are set here)
        subscriptions = []
        for i in indexes:
            plan = random.choice(plans)
            start = today - timedelta(days=random.randint(1, 180))
            subscriptions.append(Subscription(
                number=f"{PREFIX}{i:06d}", customer=by_email[emails[i]], plan=plan,
                start_date=start, expiry_date=start + timedelta(days=365),
                status=Subscription.ACTIVE, next_billing_date=start,
            ))

        with transaction.atomic():
            Subscription.objects.bulk_create(subscriptions, batch_size=500)
            lines = []
            for sub in subscriptions:
                for product in random.sample(products, k=min(len(products), random.randint(1, 3))):
                    variant = None
                    if product.id in variants and random.random() < 0.3:
                        variant = random.choice(variants[product.id])
                    lines.append(SubscriptionLine(
                        subscription=sub, product=product, variant=variant,
                        quantity=max(random.randint(1, 5), sub.plan.min_quantity),
                        unit_price=product.sales_price + (variant.extra_price if variant else 0),
                        tax=tax,
                    ))
            SubscriptionLine.objects.bulk_create(lines, batch_size=1000)

        self.stdout.write(self.style.SUCCESS(
            f"Created {len(subscriptions)} active subscriptions and {len(lines)} lines "
            f"(customers demo{first_index:06d}@demo.test onward, password Test@12345)."
        ))
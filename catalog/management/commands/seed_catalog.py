from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand

from catalog.models import Plan, Product, ProductVariant, Tax


class Command(BaseCommand):
    help = "Create sample taxes, products and plans (safe to re-run)."

    def handle(self, *args, **options):
        Tax.objects.get_or_create(name="GST 18%", defaults={"rate": Decimal("18")})
        Tax.objects.get_or_create(name="GST 5%", defaults={"rate": Decimal("5")})

        products = [
            ("Odoo ERP", "Software", "1000", "600", [("Brand", "Pro", "560"), ("Brand", "Enterprise", "1200")]),
            ("Support Pack", "Service", "500", "200", [("Level", "Gold", "250")]),
            ("Cloud Hosting", "Service", "300", "120", []),
            ("Training Session", "Service", "150", "60", []),
        ]
        for name, ptype, sales, cost, variants in products:
            product, _ = Product.objects.get_or_create(
                name=name,
                defaults={"product_type": ptype, "sales_price": Decimal(sales), "cost_price": Decimal(cost)},
            )
            for attr, value, extra in variants:
                ProductVariant.objects.get_or_create(
                    product=product, attribute=attr, value=value,
                    defaults={"extra_price": Decimal(extra)},
                )

        plans = [
            ("Monthly Basic", "499", Plan.MONTHLY, 1, dict(allow_renew=True)),
            ("Monthly Pro", "999", Plan.MONTHLY, 1, dict(allow_pause=True, allow_renew=True)),
            ("Yearly Business", "9999", Plan.YEARLY, 5, dict(allow_early_close=True, allow_renew=True)),
            ("Weekly Trial", "99", Plan.WEEKLY, 1, dict(auto_close=True)),
        ]
        for name, price, period, min_qty, flags in plans:
            Plan.objects.get_or_create(
                name=name,
                defaults=dict(
                    price=Decimal(price), billing_period=period, min_quantity=min_qty,
                    start_date=date.today(), **flags,
                ),
            )

        self.stdout.write(self.style.SUCCESS("Sample catalog data ready."))
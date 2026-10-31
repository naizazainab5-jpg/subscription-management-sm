from django.core.management.base import BaseCommand
from django.utils import timezone

from billing.services import generate_invoice
from subscriptions.models import Subscription


class Command(BaseCommand):
    help = "Generate invoices for every active subscription that is due. Safe to re-run."

    def handle(self, *args, **opts):
        today = timezone.localdate()
        ids = Subscription.objects.filter(status="active", next_billing_date__lte=today).values_list("id", flat=True)
        made = 0
        for sid in ids:
            # loop so a subscription that is several periods behind catches up
            while generate_invoice(sid, today):
                made += 1
        self.stdout.write(self.style.SUCCESS(f"Created {made} invoice(s)."))

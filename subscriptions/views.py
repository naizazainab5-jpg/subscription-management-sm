from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render

from accounts.views import role_required

from .models import Subscription


@role_required("admin", "staff")
def subscription_list(request):
    subscriptions = Subscription.objects.select_related("customer", "plan").order_by("-id")

    status = request.GET.get("status", "")
    q = request.GET.get("q", "").strip()

    if status in dict(Subscription.STATUSES):
        subscriptions = subscriptions.filter(status=status)
    else:
        status = ""

    if q:
        subscriptions = subscriptions.filter(
            Q(number__icontains=q) | Q(customer__email__icontains=q)
        )

    page_obj = Paginator(subscriptions, 25).get_page(request.GET.get("page"))

    params = request.GET.copy()
    params.pop("page", None)

    return render(request, "subscriptions/subscription_list.html", {
        "page_obj": page_obj,
        "statuses": Subscription.STATUSES,
        "status": status,
        "q": q,
        "querystring": params.urlencode(),
    })
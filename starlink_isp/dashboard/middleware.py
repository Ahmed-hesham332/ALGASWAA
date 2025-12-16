from django.utils.deprecation import MiddlewareMixin
from django.contrib import messages

class DashboardMessageMiddleware(MiddlewareMixin):
    """
    Adds a tag `dashboard_msg` to all messages created in dashboard views.
    Prevents login/admin messages from showing inside dashboard pages.
    """

    def process_template_response(self, request, response):
        if request.path.startswith("/dashboard") or request.path.startswith("/servers") \
           or request.path.startswith("/vouchers") or request.path.startswith("/offers"):
            
            for m in messages.get_messages(request):
                m.extra_tags += " dashboard_msg"
                messages.add_message(request, m.level, m.message, extra_tags=m.extra_tags)

        return response

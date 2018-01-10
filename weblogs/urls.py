from django.urls import path, re_path
from log import views

urlpatterns = [
    # Lack of specificity redirects
    path('', views.root),
    re_path(r'^api/(?P<channel>[^,/ ]{1,200})/(?P<latest_id>\d*)(?:|/)$', views.api),
    re_path(r'^log(?:|/)$', views.log),
    # Legacy redirects
    re_path(r'^weblog(?:|/)$', views.log),
    re_path(r'^weblog/(?P<channel>[^,/ ]{1,200})(?:|/)$', views.weblogs),
    # New URL patterns
    re_path(r'log/(?P<channel>[^/ ]{1,200})(?:|/)$', views.channel),
    re_path(r'log/(?P<channel>[^/ ]{1,200})/dl(?:|/)$', views.download),
    re_path(r'log/(?P<channel>[^/ ]{1,200})/dl/(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2}).(?P<format>(html|json|yaml|xml))(?:|/)$', views.download),
]

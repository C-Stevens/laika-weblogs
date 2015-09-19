from django.conf.urls import url
from . import views

urlpatterns = [
	url(r'^$', views.weblogs, name='weblogs'),
	url(r'^(?P<channel>[^,/ ]{1,200})/$', views.channel, name="channel"),
	url(r'^(?P<channel>[^,/ ]{1,200})/dl/$', views.download),
	url(r'^(?P<channel>[^,/ ]{1,200})/dl/(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2}).(?P<format>(html|json|yaml|xml))', views.download),
]

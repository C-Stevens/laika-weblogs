from django.conf.urls import url
from . import views

urlpatterns = [
	url(r'^$', views.weblogs, name='weblogs'),
	#url(r'^/download/$', views.download, name='download'),
	#url(r'^weblog/(?P<channel>[^, ]{1,200})/', views.channel, name='channel'),
	url(r'^(?P<channel>[^, ]{1,200})/', views.channel, name="channel"),
]
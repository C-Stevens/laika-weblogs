from django.http import HttpResponseRedirect, HttpResponse, HttpResponseNotFound
from django.shortcuts import render
from django.template import RequestContext, loader
from django.contrib import messages
from django.core import serializers
from django.utils import timezone
from ipware.ip import get_ip
from .forms import weblog_userForm
from .forms import weblog_dlForm
from .models import Line
from .models import webLine
from .models import banned_ips
from log import webloglib
from log import xml_log
import datetime
import yaml
import time
import json

SOCKET_ADDR = 'localhost'
SOCKET_PORT = 9989

def weblogs(request):
	return HttpResponse("Index! :3")

def channel(request, channel):
	# Disabed for suspected performance issues:
	#if not Line.objects.filter(channel=channel): # If there's no lines, don't bother rendering a log_page
		#return render(request, 'log/err.html', RequestContext(request, {'errName': "No log data", 'errDetails': "No IRC lines could be found for this channel.",}))
	if request.method == 'POST':
		user_form = weblog_userForm(request.POST)
		if user_form.is_valid():
			json_response = {}
			for i in banned_ips.objects.order_by('bannedIp'): # User is banned from posting messages with the web form
				if get_ip(request) == i.bannedIp:
					json_response['user_can_post'] = False
					return HttpResponse(json.dumps(json_response), content_type="application/json")
			json_response['user_can_post'] = True
			json_response['valid_nickname'] = user_form.cleaned_data['nickname'] not in ('Nickname', '',)
			json_response['valid_message'] = user_form.cleaned_data['message'] not in ('Message..', '',)
			l = webLine(ipAddress=get_ip(request), user=user_form.cleaned_data['nickname'], message=user_form.cleaned_data['message'])
			l.save()
			if not json_response['valid_nickname'] or not json_response['valid_message']:
				json_response['valid_password'] = None
				return HttpResponse(json.dumps(json_response), content_type="application/json")

			weblog = webloglib.weblog_manager(SOCKET_ADDR, SOCKET_PORT)
			weblog.auth(user_form.cleaned_data['password'].encode('utf-8'))
			json_response['valid_password'] = weblog.send_line(channel, user_form.cleaned_data['nickname'], user_form.cleaned_data['message'])
			return HttpResponse(json.dumps(json_response), content_type="application/json")
		else: # Generate a JSON response to draw a useful error message
			json_response = {}
			for key in user_form.errors.as_data():
				json_response['valid_'+key] = False
			return HttpResponse(json.dumps(json_response), content_type="application/json")
	else:
		user_form = weblog_userForm()
	if (request.is_ajax()):
		latest_line_id = request.GET.get('latest_id', '')
		if latest_line_id == '-1': # Return all lines
			json_data = serializers.serialize("json", list(reversed(Line.objects.filter(channel=channel).order_by('-id')[:100])))
		else:
			json_data = serializers.serialize("json", list(reversed(Line.objects.filter(id__gt=latest_line_id, channel=channel).order_by('-id')[:100])))
		return HttpResponse(json_data, content_type="application/json")

	context_dict = {
		'channel' : channel,
		'user_form' : user_form,
		'dl_form' : weblog_dlForm(),
	}
	context = RequestContext(request, context_dict)
	return render(request, 'log/log_page.html', context)

def download(request, channel, **kwargs):
	if request.method == "POST":
		dl_form = weblog_dlForm(request.POST)
		if dl_form.is_valid():
			formDate = dl_form.cleaned_data['date']
			date_requested = {
				'year' : formDate.year,
				'month' : formDate.month,
				'day' : formDate.day,
			}
			dl_format = dl_form.cleaned_data['log_format']
		else:
			return render(request, 'log/err.html', RequestContext(request, {'errName': "Invalid form data", 'errDetails': "Form data failed to be validated (contains one or more errors).",}))
	elif request.method == "GET":
		if not kwargs.get('date'): # A request to just .../dl/
			return HttpResponseRedirect("/weblog/{0}".format(channel))

		splitDate = kwargs.get('date').split('-') # Date format: YYYY-MM-DD
		date_requested = {
			'year' : int(splitDate[0]),
			'month' : int(splitDate[1]),
			'day' : int(splitDate[2]),
		}
		dl_format = kwargs.get('format')
	startDate = datetime.date(date_requested['year'], date_requested['month'], date_requested['day'])
	try:
		endDate = datetime.date(date_requested['year'], date_requested['month'], date_requested['day']+1)
	except ValueError: # Day requested is at the end of the month. Bump month or roll it over to January
		nextMonth = date_requested['month']+1 if date_requested['month'] < 12 else 1
		endDate = datetime.date(date_requested['year'], nextMonth, 1)

	logLines = Line.objects.filter(channel=channel, timestamp__range=(startDate, endDate))
	if not logLines:
			return render(request, 'log/err.html', RequestContext(request, {'errName': "No lines returned", 'errDetails': "Failed to fetch any IRC lines for this channel.",}))
	if dl_format == 'xml':
		line_data = xml_log.createLog(logLines)
		formatType = "application/xml"
	elif dl_format == 'json':
		line_data = serializers.serialize("json", logLines)
		formatType = "application/json"
	elif dl_format == 'yaml':
		line_data = serializers.serialize("yaml", logLines)
		formatType = "text/x-yaml"
	elif dl_format == 'html':
		formatType = "text/html"

	if request.method == "POST": # Redirect request, making it a GET
		return HttpResponseRedirect("/weblog/{0}/dl/{1:0>4}-{2:0>2}-{3:0>2}.{4}".format(channel, date_requested['year'], date_requested['month'], date_requested['day'], dl_format))
	elif request.method == "GET": # Serve the log
		if formatType == 'text/html': # Special case requiring a template render
			context_dict = {
				'channel' : channel,
				'lines' : logLines,
			}
			context = RequestContext(request, context_dict)
			return render(request, 'log/log_dl.html', context)
		else:
			return HttpResponse(line_data, formatType)

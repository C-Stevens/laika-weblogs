from django.http import HttpResponseRedirect, HttpResponse, HttpResponseNotFound
from django.views.decorators.http import require_GET
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
SOCKET_PORT = 9977

def root(request):
    return HttpResponseRedirect('/log') # Default starting URL

def weblogs(request, channel): # Legacy redirect
    return HttpResponseRedirect('/log/%s' % channel)

def log(request):
    return HttpResponseRedirect('/log/pwiki') # Default channel

@require_GET
def api(request, channel, latest_id):
    latest_id = int(latest_id)
    requestedLines = requestedLines = Line.objects.filter(channel=channel).order_by('-id')
    if latest_id:
        requestedLines = requestedLines.filter(id__gt=latest_id)

    # Django does not allow for negative indexing while filtering queries, so they are sorted ascending in the query [order_by(-id)] and limited to 100 items
    # However this produces a list with newest entry first, which is not useful for a chronological log. Once the set is obtained from the query, reverse it for the view.
    json_data = serializers.serialize('json', list(requestedLines[:100])[::-1])
    return HttpResponse(json_data, content_type="application/json")

def channel(request, channel):
    # Disabed for suspected performance issues:
    #if not Line.objects.filter(channel=channel): # If there's no lines, don't bother rendering a log_page
        #return render(request, 'log/err.html', RequestContext(request, {'errName': "No log data", 'errDetails': "No IRC lines could be found for this channel.",}))
    user_form = weblog_userForm(request.POST or None)
    if request.method == 'POST' and user_form.is_valid():
        nickname = user_form.cleaned_data['nickname']
        message = user_form.cleaned_data['message']
        password = user_form.cleaned_data['password']
        ip = get_ip(request)
        timestamp = datetime.datetime.now()
        postDetails = { 'user_not_banned'           : True,
                        'nickname_not_default'  : nickname not in ["Nickname", ""],
                        'message_not_default'   : message not in ["Message...", ""],
                        'backend_alive'     : None, # connect
                        'valid_password'    : None, # auth
                        'send_success'      : None, # send_line
                        
            }
        # Check to see if this IP is banned from posting messages. If it is, mark the error and return
        for i in banned_ips.objects.order_by('bannedIp'):
            if ip == i.bannedIp:
                postDetails['user_not_banned'] = False
                return HttpResponse(json.dumps(postDetails), content_type="application/json")
        # Check to make sure a default (empty) form was submitted. If it was, do not bother processing and return
        if not postDetails['nickname_not_default'] or not postDetails['message_not_default']:
            return HttpResponse(json.dumps(postDetails), content_type="application/json")

        client = webloglib.weblog_client(SOCKET_ADDR, SOCKET_PORT)
        try:
            client.connect()
        except (ConnectionError, TimeoutError, OSError):
            postDetails['backend_alive'] = False
            return HttpResponse(json.dumps(postDetails), content_type="application/json")
        try:
            client.auth(password)
        except webloglib.invalidProofError:
            postDetails['valid_password'] = False
            return HttpResponse(json.dumps(postDetails), content_type="application/json")
        postDetails['valid_password'] = True
        
        lineData = {'nickname'  : nickname,
                    'timestamp' : timestamp,
                    'message'   : message,
                    'channel'   : channel }
        try:
            client.send_line(lineData)
        except Exception:
            postDetails['send_success'] = False
            return HttpResponse(json.dumps(postDetails), content_type="application/json")
        # Log this successfully sent line to the special database for weblog lines
        webLine(user=nickname, ipAddress=ip, timestamp=timestamp, message=message, channel=channel).save()

        return HttpResponse(json.dumps(postDetails), content_type="application/json")
    if request.method == "GET":
        context_dict = {'channel' : channel,
                        'user_form' : weblog_userForm(),
                        'dl_form' : weblog_dlForm(),
        }
        return render(request, 'log/log_page.html', context_dict)

def download(request, channel, **kwargs):
    date = kwargs.get('date')
    format = kwargs.get('format')
    date_requested = {
        'year' : 0,
        'month' : 0,
        'day'   : 0,
    }

    if request.method == "POST":
        # Extract request data from POST form, then redirect the request to be a GET
        f = weblog_dlForm(request.POST)
        if f.is_valid():
            date_requested['year'] = f.cleaned_data['date'].year
            date_requested['month'] = f.cleaned_data['date'].month
            date_requested['day'] = f.cleaned_data['date'].day
        format = f.cleaned_data['log_format']
        return HttpResponseRedirect("%d-%02d-%02d.%s" % (date_requested.get('year'), date_requested.get('month'), date_requested.get('day'), format))
    splitDate = date.split('-')
    try:
        date_requested['year'] = int(splitDate[0])
        date_requested['month'] = int(splitDate[1])
        date_requested['day'] = int(splitDate[2])
    except ValueError:
        return render(request, 'log/err.html', RequestContext(request, {'errName': "No lines returned", 'errDetails': "Failed to fetch any IRC lines for this channel.",}))
    
    startDate = datetime.date(date_requested['year'], date_requested['month'], date_requested['day'])
    try:
        endDate = datetime.date(date_requested['year'], date_requested['month'], date_requested['day']+1)
    except ValueError: # Day requested is at the end of the month. Bump to the first of the next month
        nextMonth = date_requested['month']+1 if date_requested['month'] < 12 else 1
        endDate = datetime.date(date_requested['year'], nextMonth, 1)
    logLines = Line.objects.filter(channel=channel, timestamp__range=(startDate, endDate))
    
    if format == 'xml':
        line_data = xml_log.createLog(logLines)
        formatType = "application/xml"
    elif format == 'json':
        line_data = serializers.serialize("json", logLines)
        formatType = "application/json"
    elif format == 'yaml':
        line_data = serializers.serialize("yaml", logLines)
        formatType = "text/x-yaml"
    elif format == 'html':
        line_data = serializers.serialize('json', logLines)
        return render(request, 'log/log_dl.html', {'channel': channel, 'lines' : line_data,})
    return HttpResponse(line_data, formatType)

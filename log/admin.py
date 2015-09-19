from django.contrib import admin
from .models import Line
from .models import webLine
from .models import banned_ips

class LineAdmin(admin.ModelAdmin):
	fieldsets = (
		(None, {
			'fields' : ('nick', 'channel', 'msgType', 'message',),
		}),
	)
class webLineAdmin(admin.ModelAdmin):
	pass
class banned_ipsAdmin(admin.ModelAdmin):
	pass

admin.site.register(Line, LineAdmin)
admin.site.register(webLine, webLineAdmin)
admin.site.register(banned_ips, banned_ipsAdmin)


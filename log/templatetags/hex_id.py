from django import template
import hashlib

register = template.Library()

@register.simple_tag
def hexId(nick):
	return hashlib.sha1(nick.lower().encode()).hexdigest()[0]
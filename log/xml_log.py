import xml.etree.ElementTree as xml
import re

def createLog(lines):
	root = xml.Element('django-objects', attrib={'version' : '1.0'})
	for l in lines:
		child_line = xml.SubElement(root, 'object', attrib={'pk' : str(l.id), 'model': "log.line"})
		line_message = xml.SubElement(child_line, 'field', attrib={'type' : "TextField", 'name' : "message"})
		line_message.text = formatMsg(l.message)
		line_nick = xml.SubElement(child_line, 'field', attrib={'type' : "CharField", 'name' : "nick"})
		line_nick.text = formatMsg(l.nick)
		line_hostname = xml.SubElement(child_line, 'field', attrib={'type' : "CharField", 'name' : "hostname"})
		line_hostname.text = formatMsg(l.hostname)
		line_channel = xml.SubElement(child_line, 'field', attrib={'type' : "CharField", 'name' : "channel"})
		line_channel.text = formatMsg(l.channel)
		line_timestamp = xml.SubElement(child_line, 'field', attrib={'type' : "DateTimeField", 'name' : "timestamp"})
		line_timestamp.text = str(l.timestamp)
		line_msgType = xml.SubElement(child_line, 'field', attrib={'type' : "CharField", 'name' : "msgType"})
		line_msgType.text = formatMsg(l.msgType)
	return xml.tostringlist(root, encoding="utf8", method='xml', short_empty_elements=False)

def stripColors(message):
	regex = '/\x03(\d\d?)(?:,(\d\d?))?'
	return re.sub(r'/\x03(\d\d?)(?:,(\d\d?))?', '', message)

def formatMsg(message):
	cc_list = ['\x02','\x1D','\x1F','\x16','\x03','\x0F',]
	for i in cc_list:
		message = message.replace(i, '')
	return stripColors(message)

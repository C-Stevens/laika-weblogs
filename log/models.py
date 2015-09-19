from django.db import models

class Line(models.Model):
	message = models.TextField() 
	nick = models.CharField(max_length=50)
	hostname = models.CharField(max_length=300)
	channel = models.CharField(max_length=200)
	timestamp = models.DateTimeField(auto_now_add=True)
	PRIVMSG = 'PMSG'
	NOTICE = 'NTCE'
	ACTION = 'ACTN'
	JOIN = 'JOIN'
	PART = 'PART'
	QUIT = 'QUIT'
	NICK = 'NICK'
	TOPIC = 'TPIC'
	msgType_choices = (
		(PRIVMSG, 'PRIVMSG'),
		(NOTICE, 'NOTICE'),
		(ACTION, 'ACTION'),
		(JOIN, 'JOIN'),
		(PART, 'PART'),
		(QUIT, 'QUIT'),
		(NICK, 'NICK'),
		(TOPIC, 'TOPIC'),
	)
	msgType = models.CharField(max_length=4, choices=msgType_choices, default=PRIVMSG)

	def __str__(self):
		return self.message

class webLine(models.Model):
	user = models.CharField(max_length=50)
	ipAddress = models.GenericIPAddressField()
	timestamp = models.DateTimeField(auto_now_add=True)
	message = models.TextField()

class banned_ips(models.Model):
	bannedIp = models.GenericIPAddressField()


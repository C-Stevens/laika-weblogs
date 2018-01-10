from django.db import models

class Line(models.Model):
    message = models.TextField(blank=True, default="") # Allow blank entries as not all lines will have a message (QUIT, JOIN, etc.) 
    nick = models.CharField(max_length=50)
    hostname = models.CharField(max_length=300)
    channel = models.CharField(max_length=200)
    timestamp = models.DateTimeField(auto_now_add=True)
    LINE_TYPES = (
        ('PMSG', 'PRIVMSG'),
        ('SMSG', 'SOCKETMSG'),
        ('WMSG', 'WEBMSG'),
        ('NTCE', 'NOTICE'),
        ('ACTN', 'ACTION'),
        ('JOIN', 'JOIN'),
        ('PART', 'PART'),
        ('QUIT', 'QUIT'),
        ('NICK', 'NICK'),
        ('TPIC', 'TOPIC'),
    )
    msgType = models.CharField(max_length=4, choices=LINE_TYPES, default='PRIVMSG')

    def __str__(self):
        return "(%s / %s) %s - %s" % (self.timestamp, self.channel, self.nick, self.message)

class webLine(models.Model):
    user = models.CharField(max_length=50)
    channel = models.CharField(max_length=200)
    ipAddress = models.GenericIPAddressField()
    timestamp = models.DateTimeField(auto_now_add=True)
    message = models.TextField()

class banned_ips(models.Model):
    bannedIp = models.GenericIPAddressField()


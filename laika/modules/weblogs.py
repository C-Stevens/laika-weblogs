import threading
import datetime
import MySQLdb
import socket
import struct
import time
import os
import sys
import hashlib

class weblog_manager(object):
	def __init__(self, ircLog, botLog, socket, commandManager):
		self.ircLog = ircLog
		self.botLog = botLog
		self.socket = socket
		self.commandManager = commandManager
		self.logPoster = log_poster(self, self.ircLog)
		self.socketListener = socket_listener(self)
		self.threadPool = []
		self.spawn_threads()
	def spawn_threads(self):
		'''Spawn threads for parent objects.'''
		posterThread = threading.Thread(target=self.logPoster.run, name="logPoster_thread")
		socketThread = threading.Thread(target=self.socketListener.listen_loop, name="socketListener_thread")
		self.threadPool.append(socketThread)
		self.threadPool.append(posterThread)
		for t in self.threadPool:
			t.start()
		for t in self.threadPool:
			t.join()

class irc_line:
	def __init__(self):
		'''All variables except self.timestamp are either None, or relevant strings.'''
		self.message = None
		self.nickname = None
		self.hostname = None
		self.timestamp = datetime.datetime.now() # Automatically generate on instance spawn
		self.channel = None
		self.messageType = None
	def determine_messageType(self, split_line):
		'''Attempts to determine nature of the line.'''
		if split_line[0] == "PRIVMSG" or split_line[1] == "PRIVMSG": # PRIVMSG can be in index 0 (self user) or index 1 (other user).
			if split_line[3] == ":\x01ACTION":
				return "ACTN"
			else:
				return "PMSG"
		elif split_line[1] == "JOIN":
			return "JOIN"
		elif split_line[1] == "PART":
			return "PART"
		elif split_line[1] == "QUIT":
			return "QUIT"
		elif split_line[1] == "TOPIC":
			return "TPIC"
		elif split_line[1] == "NOTICE":
			return "NTCE"
		else:
			raise RuntimeError("Couldn't determine message type")
			return
	def extract_message(self, split_line):
		'''Reconstructs message string based upon messageType.'''
		if self.messageType == "JOIN":
			return "has joined the channel."
		elif self.messageType == "PART":
			if len(split_line) > 3: # Part message was supplied
				return "has left the channel: {0}".format(' '.join(split_line[3:])[1:])
			else:
				return "has left the channel."
		elif self.messageType == "QUIT":
			if len(split_line) > 2: # Quit message was supplied
				return "has quit ({0}).".format(' '.join(split_line[2:])[1:])
			else:
				return "has quit."
		elif self.messageType == "TPIC":
			return "has changed the topic to: {0}".format(' '.join(split_line[3:])[1:])
		elif self.messageType == "NTCE":
			return "has issued a channel notice: \"{0}\"".format(' '.join(split_line[3:])[1:])
		elif self.messageType == "PMSG":
			if split_line[0] == "PRIVMSG": # Socket PRIVMSG
				return ' '.join(split_line[2:])[1:]
			else: # Server PRIVMSG
				return ' '.join(split_line[3:])[1:]
		elif self.messageType == "ACTN":
			return ' '.join(split_line[4:])
	def extract_hostname(self, split_line):
		'''Extracts user hostname out of an IRC server line.'''
		## This will report a false hostname for lines coming out of the socket log,
		## the socketLog object instance is meant to have more knowledge than this
		## line object, and should take responsibility of correcting this incorrect
		## parsing.
		return split_line[0][1:]
	def extract_nickname(self, split_line):
		## Ditto above. This will incorrectly report the nickname due to differing
		## syntax of socket and server log formatting.
		return self.hostname.split('!', 1)[0]
	def extract_channel(self, split_line):
		if split_line[0] == "PRIVMSG": # Socket line formatting
			return split_line[1].replace('#','') # Strip off '#' to avoid HTML anchors in URL
		elif self.messageType == "QUIT":
			## Quit messages have no channel data, this will be filled in with logic not present here
			return
		else:
			if split_line[2].replace('#','').startswith(':'): # Some server lines will format channel as :(&/#)<channel> instead of just (&/#)<channel>
				return split_line[2].replace('#','')[1:]
			else:
				return split_line[2].replace('#','')
	def set_timestamp(self, new_timestamp):
		'''Provides a method to replace the automatically generated timestamp.'''
		if type(new_timestamp) == datetime.datetime:
			self.timestamp = new_timestamp
		else: # User provided something unusable
			raise NotImplementedError("Cannot assign object to timestamp (expects datetime.datetime object).")
	def parseLine(self, line):
		'''Accepts a raw, unsplit IRC line and parses it into relevant internal variables.'''
		if type(line) is list: # Someone has pre-split the line
			split_line = line
		elif type(line) is str:
			split_line = line.split(' ')
		else:
			raise NotImplementedError("Provided line is of invalid type.")
		#try:
			#self.messageType = self.determine_messageType(split_line)
			#self.message = self.extract_message(split_line)
			#self.hostname = self.extract_hostname(split_line)
			#self.nickname = self.extract_nickname(split_line)
			#self.channel = self.extract_channel(split_line)
		#except Exception as e:
			#print("Could not automatically parse line.",e)
			#return
		self.messageType = self.determine_messageType(split_line)
		self.message = self.extract_message(split_line)
		self.hostname = self.extract_hostname(split_line)
		self.nickname = self.extract_nickname(split_line)
		self.channel = self.extract_channel(split_line)
	def printData(self):
		'''Prints out all stored instance variables. Useful for debug.'''
		print("messageType: {0}\nmessage: {1}\nhostname: {2}\nnickname: {3}\nchannel: {4}\ntimestamp: {5}".format(self.messageType, self.message, self.hostname, self.nickname, self.channel, self.timestamp))

class socketLog(object):
	def __init__(self, parent):
		self.parent = parent
		self.ownHostname = "Laika@unaffiliated/mogdog66" # ownHostname and ownNick cannot be determined through the message elements, they must be supplied manually
		self.ownNick = "Laika"
	def log(self, line):
		split_line = line.split(' ')
		if split_line[0] == "PRIVMSG":
			if not split_line[1].startswith(("#","&",)): # Avoid logging private messages
				return
			l = irc_line()
			l.parseLine(split_line)
			l.hostname = self.ownHostname
			l.nickname = self.ownNick
			self.parent.log_line(l)

class serverLog(object):
	def __init__(self, parent):
		self.parent = parent # Allow upward passing messages
	def log(self, line):
		try:
			l = irc_line()
			l.parseLine(line)
			if l.messageType == "QUIT": # Craft a QUIT line for all channels the nickname was known to be in
				try:
					for chan in self.parent.parent.nickInfo[l.nickname]:
						l.channel = chan
						self.parent.log_line(l)
					del self.parent.parent.nickInfo[l.nickname]
					return
				except KeyError:
					## Nickname quit before we had a chance to log what channel(s) they were in.
					## Since we don't know what channels they're in, we can't insert anything
					## into the db
					return
			self.parent.parent.mapNick(l.nickname, l.channel)
			self.parent.log_line(l)
		except RuntimeError:
			## Not all server lines are useful for DB logging (MOTD, etc.), so writing in every server case is pointless.
			## Instead, this exception catch catches irc_line.parseLine()'s RuntimeError when it cannot figure out the
			## type of message. We know that this line can be safely ignored.
			return

class dummy_logger(object):
	def __init__(self, parent):
		self.parent = parent
		self.serverLog = serverLog(self)
		self.socketLog = socketLog(self)
	def channelLog(self, channel, line):
		'''Method to catch channel messages coming from Laika's log observer.'''
		l = irc_line()
		l.parseLine(line)
		self.log_line(l)
	def log_line(self, l):
		'''Method for self and children to send lines upward for DB logging.'''
		self.parent.log(l)

class log_poster(object):
	def __init__(self, parent, ircLog):
		self.parent = parent
		self.ircLog = ircLog
		self.db = None
		self.cursor = None
		self.failedMesages = []
		self.backoff = 0.5
		self.backoffMax = 300 # 5 minutes
		self.ownNick = "Laika"
		self.bouncer_hostname = "***!znc@znc.in"
		self.nickInfo = {} # Dict for storing what channels nicknames are in, to properly deal with QUIT messages
	def run(self):
		self.db = MySQLdb.connect(host="localhost", user="", passwd="", db="irc-weblogs") # Production login omitted
		channel_logs = dummy_logger(self)
		self.cursor = self.db.cursor()
		self.ircLog.register(channel_logs)
	def insert_into_db(self, data_line):
		insert_line = (	"INSERT INTO `irc-weblogs`.log_line "
				"(message, nick, timestamp, channel, msgType, hostname)"
				"VALUES (%s, %s, %s, %s, %s, %s)")
		try:
			for fm in self.failedMesages: # Always make sure failed messages are sent before any new ones
				self.cursor.execute(insert_line, fm)
			self.cursor.execute(insert_line, data_line)
			self.db.commit()
		except MySQLdb.Error as e:
			print("MySQLdb Error %d: %s"%(e.args[0], e.args[1]))
			self.failedMesages.append(data_line)
			self.backoff_timer()
	def mapNick(self, nickname, channel):
		if not nickname in self.nickInfo: # No dict mapping for this nickname, make one
			self.nickInfo[nickname] = []
			self.nickInfo[nickname].append(channel) # No existence checking required
		else: # Dict mapping exists, add this channel to their array of channels if not present
			if not channel in self.nickInfo[nickname]:
				self.nickInfo[nickname].append(channel)
	def log(self, line):
		if line.channel == self.ownNick or line.channel == self.ownNick[1:]: # Also check against nickname[1:], due to how channel parsing works
			return # Do not log private messages
		if line.hostname == self.bouncer_hostname:
			return # Don't bother logging bouncer messages
		self.mapNick(line.nickname, line.channel)
		#try:
			#line.printData() ## DEBUG
		#except:
			#pass
		data_line = (line.message, line.nickname, line.timestamp, line.channel, line.messageType, line.hostname,)
		self.insert_into_db(data_line)
	def backoff_timer(self):
		print("Sleeping for {0} seconds.".format(min(self.backoff * 2, self.backoffMax))) ##DEBUG
		time.sleep(min(self.backoff * 2, self.backoffMax))
		self.backoff = self.backoff * 2

class socket_listener(object):
	def __init__(self, parent):
		self.parent = parent
		self.socketServer = None
		self.runState = True
		self.port = 9989
		self.encoding = 'utf-8'
		self.create_socket()
	def create_socket(self):
		self.socketServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			self.socketServer.bind(('', self.port)) # Bind to any address this machine can be reached on, port `self.port`
		except socket.error as e:
			print("Socking binding failed:",e)
			self.runState = False
			return
		self.socketServer.listen(5) # Connect request queue of 5
	def receive(self, connection, bytes_requested):
		data = b''
		while len(data) != bytes_requested:
			data += connection.recv(bytes_requested - len(data))
		return data
	def client_thread(self, connection):
		__password = b"" # Production password omitted
		while True:
			data = connection.recv(1024)
			if data == b'WOOF':
				client_time, client_salt = struct.unpack('!L10s', self.receive(connection, struct.calcsize('!L10s')))
				server_time = int(time.time()) # Cast as int to remove decimal inaccuracies in pack/unpacking
				if not abs(client_time - server_time) < 120: # System times too far apart (2min threshold)
					break

				server_salt = os.urandom(10)
				connection.send(struct.pack('!L10s', server_time, server_salt))

				## Verify
				valid_proof = hashlib.sha224()
				valid_proof.update(struct.pack('!L', server_time) + struct.pack('!L', client_time) + server_salt + client_salt + __password)
				client_proof = self.receive(connection, len(valid_proof.digest()))
				if not client_proof == valid_proof.digest():
					break

				msgSize = struct.unpack('!I', self.receive(connection, struct.calcsize('!I')))[0]
				socket_msg = self.receive(connection, int(msgSize))
				self.parent.socket.socketQueue.addToQueue(socket_msg.decode('utf-8'))
				continue
			if not data:
				break
		connection.shutdown(socket.SHUT_WR)
		connection.close()
	def listen_loop(self):
		while self.runState:
			(clientsocket, address) = self.socketServer.accept()
			ct = threading.Thread(target=self.client_thread, args=(clientsocket,))
			ct.start()
		self.socketServer.shutdown(socket.SHUT_WR)
		self.socketServer.close()

def run(*args):
	weblog_manager(args[0], args[1], args[2], args[3])

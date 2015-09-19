import socket
import time
import os
import struct
import hashlib

class weblog_manager(object):
	def __init__(self, host, port):
		self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			self.conn.connect((host, port))
		except:
			pass #TODO: Return back statement saying laika is unavailable
	def receive(self, bytes_requested):
		data = b''
		while len(data) != bytes_requested:
			data += self.conn.recv(bytes_requested - len(data))
		return data
	def auth(self, password):
		self.conn.send(b"WOOF") # Initiate auth sequence
		client_time = int(time.time())
		client_salt = os.urandom(10)
		self.conn.send(struct.pack('!L10s', client_time, client_salt))

		server_time, server_salt = struct.unpack('!L10s', self.receive(struct.calcsize('!L10s')))
		proof = hashlib.sha224()
		proof.update(struct.pack('!L', server_time) + struct.pack('!L', client_time) + server_salt + client_salt + password)
		self.conn.send(proof.digest())
	def send_line(self, channel, nickname, message):
		socket_line = ("PRIVMSG %s :[%s] %s\r\n"%('#'+channel, nickname, message)).encode('utf-8')
		try:
			self.conn.send(struct.pack('!I', len(socket_line)))
			self.conn.send(socket_line)
		except Exception as e:
			print("Weblog Manager send error %d: %s"%(e.args[0], e.args[1]))
			return False
		return True

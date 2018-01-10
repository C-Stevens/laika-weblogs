import socket
import time
import os
import struct
import hashlib
import json
import datetime

class weblogError(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)
class timeMisMatchError(weblogError):
    def __init__(self, clientTime):
        Exception.__init__(self, "Server rejected client time (%d) [TIME_MISMATCH]" % clientTime)
class invalidProofError(weblogError):
    def __init__(self):
        Exception.__init__(self, "Server rejected the client proof [INVALID_PROOF]")

def datetimeSerialize(timestamp):
    if isinstance(timestamp, (datetime.datetime, datetime.date)):
        return timestamp.isoformat()
    else:
        raise TypeError("Expected type datetime but received type %s" % repr(type(repr(timestamp))))

class weblog_client(object):
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    def connect(self):
        self.socket.connect((self.host, self.port))
    def receive(self, bytes_requested):
        data = b''
        while len(data) != bytes_requested:
            data += self.socket.recv(bytes_requested - len(data))
        return data
    def auth(self, password):
        self.socket.send(b"WOOF") # Initiate auth sequence
        ## t0, s0
        client_time = int(time.time())
        client_salt = os.urandom(10)
        self.socket.send(struct.pack('!L10s', client_time, client_salt))
        
        ## r0
        response = self.receive(struct.calcsize('19s')).rstrip(b'\x00') # Strip NULL chars in case of return message < 19 chars
        if response != b"laika:OK":
            if response == b'laika:TIME_MISMATCH':
                raise timeMisMatchError(client_time)
        
        ## t1, s1 / t0+t1+s0+s1
        server_time, server_salt = struct.unpack('!L10s', self.receive(struct.calcsize('!L10s')))
        proof = hashlib.sha224()
        proof.update(struct.pack('!L', server_time) + struct.pack('!L', client_time) + server_salt + client_salt + bytes(password, 'utf8'))
        self.socket.send(proof.digest())
        
        ## r1
        response = self.receive(struct.calcsize('19s')).rstrip(b'\x00') # Strip NULL chars in case of return message < 19 chars
        if response != b'laika:OK':
            if response == b'laika:INVALID_PROOF':
                raise invalidProofError
    def send_line(self, data):
        serializedData = json.dumps(data, default=datetimeSerialize).encode('utf8')
        self.socket.send(struct.pack('!I', len(serializedData)))
        self.socket.send(serializedData)
        self.socket.close()

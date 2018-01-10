import datetime
import dateutil.parser
import MySQLdb
import threading
import socket
import socketserver
import struct
import time
import os
import sys
import hashlib
import json

class weblog_manager(object):
    def __init__(self, ircLogManager, botLog, botSocket, commandManager):
        self.ircLogManager = ircLogManager
        self.botSocket = botSocket

        self.config = {
            'bot'   : { 'debug'     : True,
                        'hostname'  : "",
                        'nickname'  : "",
                        'bouncerHostname' : "",
            },
            'db'    : { 'debug'     : True,
                        'dbHost'    : "",
                        'dbUser'    : "",
                        'dbPasswd'  : "",
                        'dbTable'   : "",
                        'dbName'    : '',
                        'dbCharset' : 'utf8',
                        'dbMaxReconnectAttempts'    : 10,
                        'dbReconnectInterval'   :   1.0,
            },
            'web'   : { 'debug'             : True,
                        'host'              : "",
                        'port'              : 0000,
                        'password'          : "",
                        'socketMsgFormat'   : "",
            }
        }
        self.dbPoster = db_poster(self.config['db'])
        self.logWatcher = log_watcher(self.config['bot'], self.ircLogManager, self.dbPoster)
        self.weblog_server = weblog_server(self.config['web'], self.logWatcher, self.botSocket)
    def start(self):
        '''Startup operations.'''
        self.weblog_server.startServer()
    def shutdown(self):
        '''Shutdown operations.'''
        self.weblog_server.stopServer()

class db_poster(object):
    def __init__(self, config):
        self.config = config
        self.db = None
        self.messageQueue = []
    def dbReconnect(self):
        '''Will attempt to create a connection to the database a specified number of times with specified time between attempts (in seconds).'''
        connectSuccess = False
        connectAttempts = 0
        while not connectSuccess and connectAttempts < self.config['dbMaxReconnectAttempts']:
            try:
                self.db = MySQLdb.connect(  host=self.config['dbHost'],
                                            user=self.config['dbUser'],
                                            passwd=self.config['dbPasswd'],
                                            db=self.config['dbName'],
                                            charset=self.config['dbCharset']  )
            except MySQLdb.OperationalError as e:
                if self.config.get('debug'):
                    print("Database connection error: %s", repr(e))
                    print("Attempting to reconnect in %d seconds (attempt %d/%d)" % (self.config.get('dbReconnectInterval'),connectAttempts+1,self.config.get('dbMaxReconnectAttempts')))
                time.sleep(self.config['dbReconnectInterval'])
                connectAttempts+=1
                continue
            connectSuccess = True
        if not connectSuccess: # We've maxed out our attempts, raise the exception again but this time let it be uncaught
            if self.config.get('debug'):
                print("Was not able to reconnect to the server after %d attempts. Giving up" % connectAttempts+1)
            raise
    def getDatabaseConnection(self):
        '''Pings the db connection to check status. If an error occurs, try to reconnect.'''
        try:
            self.db.ping()
        except (AttributeError, MySQLdb.OperationalError): # self.db isn't set, or the connection is lost. Either way, reconnect
            self.dbReconnect()
    def addToQueue(self, item):
        self.messageQueue.append(item)
    def dbCommit(self):
        '''Attempt to execute all pending lines.'''
        for item in self.messageQueue:
            self.getDatabaseConnection()
            c = self.db.cursor()
            try:
                c.execute("INSERT INTO "+self.config['dbTable']+" (message, nick, hostname, channel, timestamp, msgType) VALUES (%s, %s, %s, %s, %s, %s)", item)
            except Exception as e:
                if self.config.get('debug'):
                    print("Could not execute the current line (%s)\nException details: %s" % (item, e))
                continue # Leave it in the queue for future execution attempts
            self.messageQueue.remove(item)
            c.close()
        if not self.messageQueue: # An empty list means no errors occured, it is safe to try a commit
            self.db.commit()
    def logIrcLine(self, ircLine):
        '''Concert irc_log object into values for database insertion.'''
        self.addToQueue((ircLine.message, ircLine.nickname, ircLine.hostname, ircLine.channel, ircLine.timestamp, ircLine.messageType))
        self.dbCommit()
            
class log_watcher(object):
    ### Registers itself and necessary objects with Laika's logging system and prepares lines for logging into a weblog database.
    def __init__(self, config, ircLogManager, dbPoster):
        self.logConfig = config
        self.ircLogManager = ircLogManager
        self.ircLogManager.register(self)
        self.db = dbPoster
        self.channelsByNickname = {}
    def mapChannelToNickname(self, nickname, channel):
        '''Maintain a mapping of nicknames to all the channels that nickname has been discovered in (discovery is possible when they send a message)'''
        if not nickname in self.channelsByNickname:
            self.channelsByNickname[nickname] = []
            self.channelsByNickname[nickname].append(channel)
        else:
            if not channel in self.channelsByNickname[nickname]:
                self.channelsByNickname[nickname].append(channel)
    def logChannelData(self, *args):
        '''Receive channel logs to log what others have posted into channels.'''
        split_line = args[1]
        l = irc_line()
        l.parseLine(split_line)
        if l.hostname != self.logConfig.get('bouncerHostname'): # Avoid logging bouncer messages (if any)
            self.mapChannelToNickname(l.nickname, l.channel)
            self.db.logIrcLine(l)
        if self.logConfig.get('debug'):
            print("[Channel] %s" % l)
    def logSocketData(self, line):
        '''Receive socket logs to log what has gone out through the socket (i.e what the bot has said).'''
        l = irc_line()
        try:
            l.parseLine(line)
        except NotImplementedError: # This line wasn't an outbound message to a channel
            return
        l.hostname = self.logConfig.get('hostname')
        l.nickname = self.logConfig.get('nickname')
        if self.logConfig.get('debug'):
            print("[Socket] %s" % l)
        self.db.logIrcLine(l)
    def logServerData(self, line):
        '''Receive server logs for messages sent from the IRC server that aren't channel messages (e.g QUIT notices).'''
        l = irc_line()
        try:
            l.parseLine(line)
        except NotImplementedError:
            ## If it's not a message of a known type (QUIT, etc), disregard this line for logging.
            return
        if l.messageType == "QUIT" or l.messageType == "NICK": # Use the mapping of nicks to channels that nick was in to log lines for each channel they were in
            if l.nickname in self.channelsByNickname:
                for c in self.channelsByNickname[l.nickname]:
                    l.channel = c
                    self.db.logIrcLine(l)
                del self.channelsByNickname[l.nickname]
            return
        if l.channel == self.logConfig.get('nickname'): # Don't log PMs sent to the bot
            return
        if self.logConfig.get('debug'):
            print("[Server] %s" % l)
        self.db.logIrcLine(l)
    def logWebData(self, lineConfig):
        l = irc_line()
        l.loadFromConfig(lineConfig)
        # Set previous unknowns manually
        l.hostname = self.logConfig.get('hostname')
        l.messageType = "WMSG"
        if self.logConfig.get('debug'):
            print("[Web] %s" % l)
        self.db.logIrcLine(l)

class irc_line(object):
    def __init__(self):
        self.message = ""
        self.nickname = None
        self.hostname = None
        self.timestamp = datetime.datetime.now() # Automatically generate on instance spawn
        self.channel = None
        self.messageType = None
    def __repr__(self):
        '''More useful object representation, convenient for debugging.'''
        return "{ 'message' : \"%s\", 'nickname' : \"%s\", 'hostname' : \"%s\", 'timestamp' : \"%s\", 'channel' : \"%s\", 'messageType' : \"%s\" }" % (
            self.message,
            self.nickname,
            self.hostname,
            self.timestamp,
            self.channel,
            self.messageType
            )
    def determine_messageType(self, split_line):
        '''Classifies line into one of any known IRC line types.'''
        keyMappings = {
            'PRIVMSG'   :   "PMSG",
            'SOCKETMSG' :   "SMSG",
            'WEBMSG'    :   "WMSG",
            'NOTICE'    :   "NTCE",
            'ACTION'    :   "ACTN",
            'JOIN'      :   "JOIN",
            'PART'      :   "PART",
            'QUIT'      :   "QUIT",
            'NICK'      :   "NICK",
            'TOPIC'     :   "TPIC",
        }
        if len(split_line) > 3 and split_line[3] == ":\x01ACTION":
            return keyMappings['ACTION']
        if split_line[0] == "PRIVMSG": # Message came from the socket log (outbound to IRC server)
            return keyMappings["SOCKETMSG"]  
        try:
            return keyMappings[split_line[1]]
        except KeyError:
            raise NotImplementedError("Line is of unknown type")
    def extract_message(self, split_line):
        '''Sets or reconstructs message string based on messageType.'''
        if self.messageType == "JOIN":
            return '' # There is never a message supplied with JOIN
        if self.messageType == "PART": # Return part message if supplied
            return ' '.join(split_line[3:])[1:] if len(split_line) > 3 else ""
        elif self.messageType == "NICK":
            return (split_line[2])[1:]
        elif self.messageType == "QUIT": # Return quit message if supplied
            return ' '.join(split_line[2:])[1:] if len(split_line) > 2 else ""
        elif self.messageType == "SMSG":
            if split_line[2] == ":\x01ACTION": # If its a socket message, we need to check for an ACTION and update splitting indexes accordingly
                self.messageType = "ACTN"
                return ' '.join(split_line[3:]).replace("\x01","")
            return ' '.join(split_line[2:])[1:]
        elif self.messageType == "ACTN":
            return ' '.join(split_line[4:]).replace("\x01","")
        else:
            return ' '.join(split_line[3:])[1:]
    def extract_hostname(self, split_line):
        '''Extracts hostname from IRC line.'''
        if not self.messageType == "SMSG": # Socket messages have unknown hostnames, so it must be applied out of this scope
            return split_line[0][1:]
    def extract_nickname(self, split_line):
        '''Extracts nickname from IRC line.'''
        if not self.messageType == "SMSG": # Socket messages have unknown nicks at this scope, it must be applied elsewhere
            return self.hostname.split('!', 1)[0]
    def extract_channel(self, split_line):
        '''Extracts destination channel from IRC line.'''
        if self.messageType == "QUIT" or self.messageType == "NICK": # Server quits and nick changes do not specify channel, and it is unknown at this scope
            return None
        if self.messageType == "SMSG":
            return split_line[1].replace('#','') # Leading pound is assumed by outer scopes
        else:
            channel = split_line[2].replace('#','')
            return channel[1:] if channel.startswith(':') else channel # Some servers will format channel as :#channel instead of #channel
    def parseLine(self, line):
        '''Accepts an IRC line and parses it into relevant internal variables.'''
        if type(line) is list: # Someone has pre-split the line
            split_line = line
        elif type(line) is str:
            split_line = line.split(' ')
        else:
            raise NotImplementedError("Provided line is of invalid type (expected 'str' or 'list')")
        self.messageType = self.determine_messageType(split_line)
        self.channel = self.extract_channel(split_line)
        self.message = self.extract_message(split_line)
        self.hostname = self.extract_hostname(split_line)
        self.nickname = self.extract_nickname(split_line)
    def loadFromConfig(self, config):
        '''Instead of setting locals with message parsing, allow locals to be set directly with a configuration dictionary.'''
        self.message = config.get('message')
        self.nickname = config.get('nickname')
        self.hostname = config.get('hostname')
        self.timestamp = config.get('timestamp')
        self.channel = config.get('channel')
        self.messageType = config.get('messageType')

class serverHandler(socketserver.BaseRequestHandler):
    def sendToSocket(self, line):
        data = self.server.config.get('socketMsgFormat').format(**line)
        if self.server.config['debug']:
            print("%s sending this line to the bot's outbound socket: %s" % (threading.current_thread(), data))
        self.server.botSocket.socketQueue.addToQueue(data, reportToQueue=False)
    def receive(self, connection, bytes_requested):
        data = b''
        while len(data) != bytes_requested:
            data += connection.recv(bytes_requested - len(data))
        return data
    def handle(self):
        self.request.settimeout(30)
        currentThread = threading.current_thread()
        data = self.request.recv(4)
        if data == b'WOOF': # Connection initiated
            if self.server.config['debug']:
                print("%s Connection initiated"%currentThread)
                
            client_time, client_salt = struct.unpack('!L10s', self.receive(self.request, struct.calcsize('!L10s')))
            server_time = int(time.time()) # Cast as int to remove decimal inaccuracies in pack/unpacking
            if not abs(client_time - server_time) < 120: # System times too far apart (2min threshold)
                if self.server.config['debug']:
                    print("%s Failing connection due to time mismatch"%currentThread)
                self.request.sendall(struct.pack('19s', b"laika:TIME_MISMATCH"))
                return
            if self.server.config['debug']:
                print("%s Client salt received (%s) and client/server time difference is acceptable"%(currentThread, repr(client_salt)))
            self.request.sendall(struct.pack('19s', b"laika:OK"))

            server_salt = os.urandom(10)
            self.request.sendall(struct.pack('!L10s', server_time, server_salt))
            if self.server.config['debug']:
                print("%s Sent server salt (%s) to client"%(currentThread, repr(server_salt)))
            
            ## Verify
            valid_proof = hashlib.sha224()
            valid_proof.update(struct.pack('!L', server_time) + struct.pack('!L', client_time) + server_salt + client_salt + bytes(self.server.config['password'], 'utf8'))
            if self.server.config['debug']:
                print("%s Waiting for client to send proof"%currentThread)
                       
            client_proof = self.receive(self.request, len(valid_proof.digest()))
            if not client_proof == valid_proof.digest():
                if self.server.config['debug']:
                    print("%s Failing connection due to bad client proof"%currentThread)
                self.request.sendall(struct.pack('19s', b"laika:INVALID_PROOF"))
                return
            if self.server.config['debug']:
                print("%s Valid proof received from client"%currentThread)
            self.request.sendall(struct.pack('19s', b"laika:OK"))

            msgSize = struct.unpack('!I', self.receive(self.request, struct.calcsize('!I')))[0]
            data = self.receive(self.request, int(msgSize))
            if not len(data) is msgSize:
                return
            self.request.sendall(struct.pack('19s', b"laika:OK"))
            deserializedData = json.loads(data.decode('utf8'))
            deserializedData['timestamp'] = datetimeDeserialize(deserializedData.get('timestamp'))
            if self.server.config['debug']:
                print("%s Received %s bytes from server: %s" % (currentThread, repr(msgSize), repr(deserializedData)))

            # Send line to socket to be spoken
            self.sendToSocket(deserializedData)
            # Send line to the logger for database insertion
            self.server.logWatcher.logWebData(deserializedData)
            
            if self.server.config['debug']:
                print("%s Connection closing"%currentThread)

class threadedServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

class weblog_server(object):
    def __init__(self, config, logWatcher, botSocket):
        self.config = config
        self.logWatcher = logWatcher
        self.botSocket = botSocket
        self.server = None
        self.serverThread = None
    def spawnServer(self):
        self.server = threadedServer((self.config['host'], self.config['port']), serverHandler)
        self.server.config = self.config
        self.server.logWatcher = self.logWatcher
        self.server.botSocket = self.botSocket
        ip, port = self.server.server_address
        if self.config['debug']:
            print("Starting weblog listening server on %s port %s" % (repr(ip), repr(port)))
    def startServer(self):
        self.spawnServer()
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        if self.config['debug']:
            print("Weblog listening server started")
    def stopServer(self):
        self.server.shutdown()
        if self.config['debug']:
            print("Weblog listening server shut down")

def datetimeDeserialize(str):
    return dateutil.parser.parse(str)

def run(*args):
    global manager
    manager = weblog_manager(*args)
    manager.start()

def shutdown():
    global manager
    manager.shutdown()

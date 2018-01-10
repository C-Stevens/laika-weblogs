# laika-weblogs
Bringing live-updating and web-based IRC line posting functionality to [Laika](https://github.com/C-Stevens/Laika).

### The What
Laika weblogs provide Django-powered live updating weblog functionality to my [Laika IRC bot](https://github.com/C-Stevens/Laika). In total, this repository contains a [Laika module](https://github.com/C-Stevens/Laika#modules) for catching IRC data, a complete [Django](https://www.djangoproject.com) app backend for storing line data in a database, JavaScript and relevant HTML templates for web rendering and updating, as well as a method for posting to IRC channels through the bot by using a custom socket connection and authentication protocol.

A live demo can be found [here](http://irc.mog.dog/weblog/pwiki/), which keeps a log of #pwiki on [freenode](https://freenode.net).

### The How
#### Obtaining IRC Data
The weblogs are able to get IRC data (including channel logs, IRC server data, and data from the bot being sent out to the IRC server) by registering a series of custom logging objects with Laika's [log observer](https://github.com/C-Stevens/laika/blob/master/doc/log.py.md#irclogmanager-objects). From there, data is parsed and inserted into the backend database. Django does all the work of taking these inserted lines and providing functionality to them.

#### Providing an Auto-Updating IRC Log
The front-end drawing and manifestation of database data is done through a Django-powered API. An array of relevant lines to the URL request is sent to the [`main.js`](static/js/main.js) file where formatting and additional display drawing is applied. This JavaScript file provides auto-updating with a looping AJAX request to the backend.

#### Log Downloads
The application currently supports serializing requested database data in [`yaml`](http://yaml.org/) and [`JSON`](http://json.org/) formats through Django's built-in [serializers](https://docs.djangoproject.com/en/2.0/topics/serialization/#serialization-formats). `HTML` versions of logs are generated through a [Django template](templates/log/log_dl.html), and [`XML`](http://www.w3.org/XML/) versions of logs are generated through a custom [XML building method](log/webloglib.py).

#### Displaying Errors
The front-end is able to receive error data from the backend Django view in regards to log posting through the on-page form. The backend view is responsible for verifying the integrity of form fields, the status of the sent message, and the validity of the user via the socket service. The front-end merely uses this returned data to draw useful errors, it has no knowledge of how the backend has detected the error(s).

#### Log Posting Socket Authentication Stack Sequence
The Laika submodule handles both receiving log data from the bot, as well as running a socket server to serve requests from the Django backend. This service allows the backend (and thus the user) to send data through the bot's outbound socket, and thus speak in the IRC channel via a web interface.

To minimize spam and provide basic access control, there is an authentication sequence initiated by the backend upon receiving credentials and data from the web client. This authentication sequence is initiated by sending a `b'WOOF'` (equivalently: `\x57\x4f\x4f\x46`) [magic number](https://en.wikipedia.org/wiki/Magic_number_(programming)) to the service.

In general, the complete sequence including authentication and message transfer is as follows:
```
-client-> b'WOOF'
-client-> local time (t0)
-client-> client salt (s0)
<-server- b'LAIKA:ok' if client time and server times differ in acceptable thresholds, b'LAIKA:TIME_MISMATCH' otherwise
<-server- local time (t1)
<-server- server salt (s1)
-client-> authentication proof (t0 + t1 + s0 + s1 + password)
<-server- b'LAIKA:ok' if server computed and client provided proofs match, b'LAIKA:INVALID_PROOF' otherwise
-client-> byte size of message payload
-client-> message payload
<-server- b'LAIKA:ok' to terminate connection
```
Local system times (t0 & t1) are used both as additional obfuscation while hashing, as well as a rudimentary precaution against time-based attacks on the server. If the times differ between client and server by more than two minutes, the connection is dropped by the server. These times are cast and packaged as type `int` to avoid decimal precision loss while packing and unpacking large floating point values of the time(s).

Random salts (s0 & s1) are generated from `/dev/urandom` (via the python method [`os.urandom()`](https://docs.python.org/2/library/os.html#os.urandom)).

Authentication proof is the concatenation of both system times, both salts, and the password provided from the web form. This concatenation is then passed through a [SHA224](https://www.ietf.org/rfc/rfc3874.txt) hash and sent to the server. If the hashes from the client and the server's own computed hash do not match, the server will drop the connection.

#### Preventing Log Posting Spam
Since the log posting is fairly basic in design (notably, there being a master password and no nickname verification), all attempted posts from the web form have their IP compared against a database table of banned IP addresses. If there is a match the front-end will be notified, an error displayed, and the line will not be posted. There is no web-facing way to ban IP addresses; they must be manually inserted as rows into the banned IP table.

This ip-based detection is handled by the Django backend, and not by the socket service itself. That means if the connection of the socket service is known to anything other than the Django backend itself, it cannot provide this defense. Therefore it is strongly encouraged that the socket service listens on localhost only, to a port or socket known only to Django.

All attempts to use the web speaking feature are logged in a seperate table with the destination channel, nickname requested, and source ip address. The message content is only added to the general log database if the ip address is not recognized as prohibited by the Django backend, and the authentication sequence to the socket service does not end in failure. While no automated system for spam detection exists, it's possible to create one given monitoring of this table. To ban an ip address the address must be manually inserted into a database of prohibited ips. If given access to this table, a service able to exclude ip addresses more easily can be created.

### The Who
This repository and all relevant files were written by [Colin Stevens](https://colinjstevens.com).

I can be reached at [mail@colinjstevens.com](mailto:mail@colinjstevens.com)

### The Limitations
* The front-end includes methods to detect if the backend is not responding, but it cannot relaunch the bot or the weblog library itself. It should also be noted that no lines will be logged while the main Laika bot is not running, therefore it's recommended to place the bot behind an [IRC bouncer](https://en.wikipedia.org/wiki/BNC_(software)#IRC), so missed lines will be given to the bot when it reconnects.
* While the authentication sequence for web log posting is cryptographically sound, subsequent line messages (after the authentication proof) are sent unencrypted. As a result, a [MITM](https://en.wikipedia.org/wiki/Man-in-the-middle_attack) figure can wait for the sequence to complete, and then insert their own line packets to the server and have them posted. This can be reconciled by implementing a [MAC scheme](https://en.wikipedia.org/wiki/Message_authentication_code) using the computed hash.
  * At original time of writing, it was difficult to secure HTTPS certificates for subdomains. The state of HTTPS is changing and this is now made easier, which can ensure that the password is indeed encrypted on its way to the server. The rewritten socket service opens a new TCP connection per every request, but this can still be made even more secure by implementing a MAC scheme.

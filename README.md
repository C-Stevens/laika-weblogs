# laika-weblogs
Bringing live-updating and web-based IRC line posting functionality to [Laika](https://github.com/C-Stevens/Laika).

### The What
Laika weblogs provide Django-powered live updating weblog functionality to my [Laika IRC bot](https://github.com/C-Stevens/Laika). In total, this repository contains a [Laika module](https://github.com/C-Stevens/Laika#modules) for catching IRC data, a complete [Django](https://www.djangoproject.com) app backend for storing line data in a database, JavaScript and relevant HTML templates for web rendering and updating, as well as a method for posting to IRC channels through the bot by using a custom socket connection and authentication protocol.

A live demo can be found [here](http://irc.mog.dog/weblog/pwiki/), which keeps a log of #pwiki on [freenode](https://freenode.net).

### The How
#### Obtaining IRC Data
The weblogs are able to get IRC data (including channel logs, IRC server data, and data from the bot being sent out to the IRC server) are obtained by registering a series of custom logging objects with Laika's [log observer](https://github.com/C-Stevens/laika/blob/master/doc/log.py.md#irclogmanager-objects). From there, data is parsed and inserted into the backend database. Django does all the work of taking these inserted lines and providing functionality to them.

#### Providing an Auto-Updating IRC Log
The front-end drawing and manifestation of database data is done through Django. An array of relevant lines to the URL request is sent to the [`main.js`](static_raw/js/main.js) file where formatting and additional display drawing is applied. This JavaScript file also provides auto-updating with a looping AJAX request to the backend.

#### Log Downloads
The package currently supports serializing of relevant database data through Django's [`yaml`](http://yaml.org/) (through [`pyyaml`](http://pyyaml.org/), and [`JSON`](http://json.org/) [serializers](https://docs.djangoproject.com/en/1.8/topics/serialization/#serialization-formats). `HTML` logs are generated with a [Django template](templates/log/log_dl.html), and [`XML`](http://www.w3.org/XML/) logs are generated through a custom [XML building method](log/webloglib.py).

#### Displaying Errors
The JavaScript front-end is able to receive error data from the backend Django view in regards to log posting through the on-page form. The backend view is responsible for verifying the integrity of form fields, the status of the sent message, and the validity of the user. The front-end merely uses this returned data to draw useful errors, it has no knowledge of how the backend has detected the error(s).

#### Log Posting Socket Authentication Stack Sequence
The Laika submodule includes a [class](laika/modules/weblogs.py#L251-L307) that opens a socket connection for all local addresses (However, this could be [configured](laika/modules/weblogs.py#L262) for external addresses in addition, or in place of local addresses) that will initiate an authentication sequence if sent a `b'WOOF'` (equivalently: `\x57\x4f\x4f\x46`) [magic number](https://en.wikipedia.org/wiki/Magic_number_(programming)). This functionality is used to provide a method for posting messages into IRC channels through the bot from a webpage. This connection does not recover if packets are lost, and the server does not respond with notice that the client failed any or all parts of the sequence.

In general, the sequence looks as follows:
```
-client-> b'WOOF'
-client-> system time (t0)
-client-> 10 byte random salt (s0)
<-server- server time (t1)
<-server- 10 byte random salt (s1)
-client-> Authentication proof (t0 + t1 + s0 + s1 + password)

If connection isn't dropped by server (invalid proof):
-client-> Byte size of line
-client-> Line
```
Local system times (t0 & t1) are used both as additional obfuscation while hashing, as well as a rudimentary precaution against time-based brute force attacks on the server. If the times differ between client and server by more than two minutes, the connection is dropped without notice by the server. These times are cast and packaged as type `int` to avoid decimal precision loss while packing and unpacking large floating point values of the time(s).

Random salts (s0 & s1) are generated from `/dev/urandom` (via the python method [`os.urandom()`](https://docs.python.org/2/library/os.html#os.urandom)).

Authentication proof is the concatenation of both system times, both salts, and the password provided from the web form. This concatenation is then passed through a [SHA224](https://www.ietf.org/rfc/rfc3874.txt) hash and sent to the server. If the hashes from the client and the server's own computed hash do not match, the server will drop the connection without notice.

#### Preventing Log Posting Spam
Since the log posting is fairly basic in design (notably, there being a master password and no nickname verification), all attempted posts from the web form have their IP compared against a database table of banned IP addresses. If there is a match the front-end will be notified, an error displayed, and the line will not be posted. There is no web-facing way to ban IP addresses; they must be manually inserted as rows into the banned IP table.

Additionally for spam detection, there is no automated system or front-end, but all posts to the log from the web are logged in a seperate database table (in addition to the general line table used for drawing the on-page log). This table includes columns for not only the nickname and message supplied, but also the time it was posted at, and the IP address that the post came from. While no automated system for spam detection exists, it's certainly possible to create one, if given access to this table.

### The Who
This repository and all relevant files were written by [Colin Stevens](https://colinjstevens.com).

I can be reached at [mail@colinjstevens.com](mailto:mail@colinjstevens.com)

### The Limitations
* The front-end does not receive notice if the Laika module is not running or has crashed. The consequence of this (gaps in the logs) can be mitigated by placing the bot behind an [IRC bouncer](https://en.wikipedia.org/wiki/BNC_(software)#IRC), so missed lines will be given to the bot when it reconnects.
* While the authentication sequence for web log posting is cryptographically sound, subsequent line messages (after the authentication proof) are sent unencrypted. As a result, a [MITM](https://en.wikipedia.org/wiki/Man-in-the-middle_attack) figure can wait for the sequence to complete, and then insert their own line packets to the server and have them posted. This can be reconciled by implementing a [MAC scheme](https://en.wikipedia.org/wiki/Message_authentication_code) using the computed hash.
  * However, I haven't bothered implementing line encryption because, due to the awful state of [HTTPS](https://en.wikipedia.org/wiki/HTTPS) [CA](https://en.wikipedia.org/wiki/Certificate_authority)s, my log domain has no valid HTTPS certificate for its subdomain. As such, the password is sent to the server from the webform in plaintext anyway. As a result, a MITM entity can pick up the password from the wire and not have to bother inserting packets as described above anyway, making the effort to encrypt lines pointless.
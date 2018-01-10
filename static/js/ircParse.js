function get_id_from_nickname(nick) {
        return CryptoJS.SHA1(nick.toLowerCase()).toString().charAt(0);
};

function get_color_format(colorCode) {
        if(!colorCode) { // Don't bother with 'false', 'undefined', etc.
                return '';
        }
        var splitCode = colorCode.split(',');
        fontColor = splitCode[0].substring(1, splitCode[0].length); // Skip first '\x03' char
        if(splitCode[1]) {
                var bgColor = splitCode[1];
        } else {
                var bgColor = false;
        }
        colors = {
                '00': 'white',
                '01': 'black',
                '02': 'blue',
                '03': 'green',
                '04': 'red',
                '05': 'brown',
                '06': 'purple',
                '07': 'orange',
                '08': 'yellow',
                '09': 'light-green',
                '10': 'teal',
                '11': 'cyan',
                '12': 'light-blue',
                '13': 'pink',
                '14': 'grey',
                '15': 'light-grey'
        }
        returnString = "color: "+colors[fontColor]+";";
        if(bgColor) {
                returnString += "background-color: "+colors[bgColor]+";";
        }
        return returnString;
}

function get_format_span(msgState) {
        var styling = '';
        var styleMappings = {
                bold: "font-weight: bold;",
                italic: "font-style: italic;",
                underline: "text-decoration: underline;",
                color: get_color_format(msgState.color),
        };
        for(var key in msgState) {
                if(msgState[key] != 'undefined' && msgState[key] != false) {
                        styling += styleMappings[key];
                }
        }
        if(!styling) {
                return '</span>';
        } else {
                return('</span><span style=\"'+styling+'\">');
        }
}

function format(messageState, message) {
        function restyleMsg(toReplace) {
                message = message.replace(toReplace, get_format_span(messageState));
        }
        for(var i=0; i < message.length; i++) {
                switch(message[i]) {
                        case '\x02': // Bold
                                messageState.bold = !messageState.bold; // Flip state
                                restyleMsg(message[i]); // Recompile styling string
                                break;
                        case '\x1D' : // Italic
                                messageState.italic = !messageState.italic;
                                restyleMsg(message[i]);
                                break;
                        case '\x1F': // Underline
                                messageState.underline = !messageState.underline;
                                restyleMsg(message[i]);
                                break;
                        case '\x16': // Invert
                                /* HTML inversion requires the `filter: invert();` CSS property.
                                 * Since the style replacements here deal with HTML spans, this
                                 * isn't possible without applying some kind of class, which
                                 * requires special algo consideration. For now, '\x16' does
                                 * nothing. */
                                break;
                        case '\x03': // Color text
                                var re = /\x03(\d\d?)(?:,(\d\d?))?/g;
                                if ((matchArray = re.exec(message)) !== null) {
                                        if(messageState.color == matchArray[0]) { // Already present, time to end coloring
                                                messageState.color = false;
                                                restyleMsg(message[i]);
                                                break;
                                        } else { // Time for new coloring
                                                messageState.color = matchArray[0];
                                        }
                                        restyleMsg(matchArray[0]);
                                } else {
                                        messageState.color = false;
                                        restyleMsg(message[i]);
                                }
                                break;
                        case '\x0F': // Format reset
                                messageState.bold = false;
                                messageState.italic = false;
                                messageState.underline = false;
                                messageState.color = false;
                                restyleMsg(message[i])
                                break;
                }
        };
        return message;
};

function sanitize(input) {
        var output = input.replace(/<script[^>]*?>.*?<\/script>/gi, '').
        //replace(/<[\/\!]*?[^<>]*?>/gi, '').
        replace(/<style[^>]*?>.*?<\/style>/gi, '').
        replace(/<![\s\S]*?--[ \t\n\r]*>/gi, '').
        replace(/</gi, '&lt;').
        replace(/>/gi, '&gt;');
        return output;
};

function convert_links(input) {
        var replacedText, replacePattern1, replacePattern2;
        
        //URLs starting with http://, https://, or ftp://
        replacePattern1 = /(\b(https?|ftp):\/\/[-A-Z0-9+&@#\/%?=~_|!:,.;]*[-A-Z0-9+&@#\/%=~_|])/gim;
        replacedText = input.replace(replacePattern1, '<a href="$1" target="_blank">$1</a>');
        
        //URLs starting with "www." (without // before it, or it'd re-link the ones done above).
        replacePattern2 = /(^|[^\/])(www\.[\S]+(\b|$))/gim;
        replacedText = replacedText.replace(replacePattern2, '$1<a href="http://$2" target="_blank">$2</a>');
        
        return replacedText;
};

function prepare(messageState, message) {
	if(message) {
        	return format(messageState, convert_links(sanitize(message)));
	}
};

function compile_message_row(json_msg) {
        var message_row = document.createElement('tr');
        var message_cell = document.createElement('td');
        message_cell.setAttribute("id", json_msg['pk']);
        message_row.setAttribute("class", "message-row");
        message_row.appendChild(message_cell);
        
        var message_cell_children = [];
        var parsed_timestamp = document.createElement('a');
        var message_prefix = document.createElement('span');
        var parsed_nick = document.createElement('span');
        message_prefix.appendChild(parsed_nick);
        var parsed_message = document.createElement('span');
        message_cell_children.push(parsed_timestamp, message_prefix, parsed_message);
        message_cell_children.forEach(function (item) {
                message_cell.appendChild(item);
        });
        
        var id = json_msg['pk'];
        var msgType = json_msg['fields']['msgType'];
        var message = json_msg['fields']['message'];
        var nick = json_msg['fields']['nick'];
        var hostname = json_msg['fields']['hostname'];
        var timestamp = moment(json_msg['fields']['timestamp']);
        var renderAsHTML = json_msg['fields']['renderAsHTML'];
        var messageState = {
                bold : false,
                italic : false,
                underline : false,
                color: false,
        };
        
        parsed_timestamp.setAttribute("class", "timestamp");
        parsed_timestamp.setAttribute("title", timestamp.format('dddd, MMMM Do - h:mm:s A'));
        parsed_timestamp.setAttribute("href","#"+timestamp.format('HH-mm-ss'));
        parsed_timestamp.innerHTML = '['+timestamp.format('YYYY-MM-DD HH:mm:ss')+']';
        
        message_prefix.setAttribute("class", "message_prefix");
        parsed_nick.setAttribute("title", hostname);
        parsed_nick.setAttribute("class", "nick nick-"+get_id_from_nickname(nick));
        if(msgType == 'PMSG') {
                $(parsed_nick).text(' <'+nick+'>');
        } else if(msgType == 'WMSG') {
                $(parsed_nick).text(' <web:'+nick+'>');
        } else {
                message_cell.setAttribute("style", "font-style: italic");
                $(parsed_nick).text(' '+nick);
        }
        
        if(msgType == 'ACTN' || msgType == 'NICK' || msgType == 'TPIC' || msgType == 'NTCE') {
                $(message_prefix).prepend(' ***');
        switch(msgType) {
            case 'NICK':
                message = 'has changed their nickname to '+message
                break;
            case 'TPIC':
                message = 'has changed the topic to "'+message+'"'
                break;
            case 'NTCE':
                message = 'has issued a notice: '+message
                break; 
        }
        } else if(msgType == 'JOIN') {
                $(message_prefix).prepend(' -->');
        message = "has joined the channel"
        } else if(msgType == 'PART' || msgType == 'QUIT') {
            $(message_prefix).prepend(' <--');
            switch(msgType) {
                case 'PART':
                    message = "has left the channel" + (message ? ' ('+message+')':'')
                    break;
                case 'QUIT':
                    message = "has quit" + (message ? ' ('+message+')':'')
                    break;
            }
        }
        parsed_message.innerHTML = ' '+prepare(messageState, message);
        
        return message_row;
};

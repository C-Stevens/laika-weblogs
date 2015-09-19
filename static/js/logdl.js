$(document).ready(function() {
	$("#log_lines > tbody > tr").each(function() {
		msgState = {
			bold : false,
			italic : false,
			underline : false,
			color: false,
		}
		originalMsg = $(".message", this).html();
		$(".message", this).html(prepare(msgState, originalMsg));
	});
});

// Rip from main.js

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
	return format(messageState, convert_links(sanitize(message)));
};
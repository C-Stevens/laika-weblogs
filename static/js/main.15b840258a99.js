$(document).ready(function() {
	var latest_message_id = $("#log_lines tr:last td").attr('id');
	if (!latest_message_id) {
		latest_message_id = -1;
	}
 	update_logs(); // Initial message load
 	var loop = setInterval(update_logs, 3000); // Poll for updates every 3.0s
	function update_logs(){
		$.ajax({
			url: window.location.pathname,
			data: {latest_id: latest_message_id},
			success: function(json_response) {
				if (!$.isEmptyObject(json_response)) {
					$("#loader").show();
					latest_message_id = json_response[json_response.length-1]['pk'];
					for (var i = 0; i < json_response.length; i++) {
						$(compile_message_row(json_response[i])).hide().appendTo("#log_lines").fadeIn(270);
						$(document).scrollTop($(document).height());
					};
				}
				$("#loader").fadeOut(450);
			},
 			async: false
		});
	}

	$('#weblog_form').submit(function(e){
		function create_error_box() {
			$("#error_box").hide().fadeIn(200);
		}
		function hide_error_box() {
			$("#error_box").hide();
		}
		$.post($(this).attr('action'), $(this).serialize(), function(data){
			hide_error_box();
			var error_msg_mappings = {
				'user_can_post' : "Your IP is banned from posting messages.",
				'valid_password' : "Invalid password.",
				'valid_nickname': "No nickname supplied.",
				'valid_message':"No message supplied.",
			};
			console.log(data); // DEBUG
			$.each(data, function(key, value) {
				if(!value && value != null) {
					create_error_box();
					console.log("KEY: "+key); // DEBUG
					$("#error_box").children("#"+key).html(error_msg_mappings[key]);
				} else {
					$("#error_box").children("#"+key).html("");
				}
				
			});
			if(!($("#error_box").is(":visible"))) { // No current errors being displayed
				$("input[name=message]").val(''); // Save the user from having to backspace old message
				$(".id_password").hide(); // Give the user a larger message text box by removing password field
			}
		
		});
		e.preventDefault();
	});

	$("#download, #download_box_close").click(function() {
		$("#download_box").fadeToggle(200);
	});
	$('select[name="log_format"]').change(function() {
		if($(this).val() == "xml") {
			$("#xml_notice").text("Note: XML logs do not support IRC formatting control characters.");
		} else {
			$("#xml_notice").text('');
		}
	});
});

function get_id_from_nickname(nick) {
	function shadeColor2(color, percent) { // https://stackoverflow.com/questions/5560248/programmatically-lighten-or-darken-a-hex-color-or-rgb-and-blend-colors
				var f=parseInt(color.slice(1),16),t=percent<0?0:255,p=percent<0?percent*-1:percent,R=f>>16,G=f>>8&0x00FF,B=f&0x0000FF;
				return "#"+(0x1000000+(Math.round((t-R)*p)+R)*0x10000+(Math.round((t-G)*p)+G)*0x100+(Math.round((t-B)*p)+B)).toString(16).slice(1);
	}
	return shadeColor2(CryptoJS.SHA1(nick.toLowerCase()).toString().substring(0,6), -0.14);
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
	return format(messageState, convert_links(sanitize(message)));
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
	parsed_timestamp.setAttribute("title", timestamp.format('dddd, MMMM Mo - h:mm:s A'));
	parsed_timestamp.setAttribute("href","#"+timestamp.format('HH-mm-ss'));
	parsed_timestamp.innerHTML = '['+timestamp.format('YYYY-MM-DD HH:mm:ss')+']';

	message_prefix.setAttribute("class", "message_prefix");
	parsed_nick.setAttribute("class", "nick");
	parsed_nick.setAttribute("title", hostname);
	parsed_nick.setAttribute("style", "color: "+get_id_from_nickname(nick));
	if(msgType == 'PMSG') {
		$(parsed_nick).text(' <'+nick+'>');
	} else {
		message_cell.setAttribute("style", "font-style: italic");
		$(parsed_nick).text(' '+nick);
	}

	if(msgType == 'ACTN' || msgType == 'NICK' || msgType == 'TPIC' || msgType == 'NTCE') {
		$(message_prefix).prepend(' ***');
	} else if(msgType == 'JOIN') {
		$(message_prefix).prepend(' -->');
	} else if(msgType == 'PART') {
		$(message_prefix).prepend(' <--');
	}
	parsed_message.innerHTML = ' '+prepare(messageState, message);

	return message_row;
};

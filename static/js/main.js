$(document).ready(function() {
    console.log('doc ready'); //DEBUG
    var latest_message_id = $("#log_lines tr:last td").attr('id');
    if (!latest_message_id) {
        latest_message_id = 0;
    }
    update_logs(); // Initial message load
    var loop = setInterval(update_logs, 2000); // Poll for updates every 3.0s
    function update_logs(){
        $.ajax({
            type: "GET",
            url: "/api/"+window.location.pathname.split("/")[2]+"/"+latest_message_id,
            success: function(json_response) {
                if (!$.isEmptyObject(json_response)) {
                    $("#loader").show();
                    latest_message_id = json_response[json_response.length-1]['pk'];
                    $(json_response).each(function(i) {
                        if($("#log_lines tr:last td").attr('id') != json_response[i]['pk']) { // Avoid posting the same line multiple times due to network latency
                            $(compile_message_row(json_response[i])).hide().appendTo("#log_lines").fadeIn(270);
                            $(document).scrollTop($(document).height());
                        }
                    });
                }
                $("#loader").fadeOut(450);
            },
        });
    }
        
    $('#weblog_form').submit(function(e){
        e.preventDefault();
        var formData = $(this).serialize();
        $.ajax({
            type: "POST",
            url: window.location.pathname,
            dataType: "json",
            data: $(this).serialize(),
            success: function(response) {
                $("#error_box").hide();
                var message_mapping = {
                    'backend_alive'         : "Could not connect to server",
                    'message_not_default'   : "No message entered",
                    'nickname_not_default'  : "No nickname entered",
                    'send_success'          : "Failed to send line to server",
                    'user_not_banned'       : "You are banned from posting messages",
                    'valid_password'        : "Invalid password",
                }
                $("#errorMessage span").remove();
                $.each(response, function(key, value) {
                    if(!value && value != null) {
                        console.log("Going to add an error message for key "+key); //DEBUG
                        console.log("mapping: "+message_mapping[key]); //DEBUG
                        $("#errorMessage").append($('<span/>').html(message_mapping[key]));
                    }
                });
                if($("#errorMessage span").length > 0) {
                    $('#errorMessage span:not(:last-child)').each(function () {
                        $(this).append(', ');
                    });
                    $("#error_box").hide().fadeIn(200);
                } else { // No errors on submission, so remove the password field to make the message field larger and reset the message field to blank
                    $("input[name=message]").val('');
                    $(".id_password").hide();
                };
            },
        });
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

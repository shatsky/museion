// AJAX stuff
function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

var csrftoken = getCookie('csrftoken');

function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

$.ajaxSetup({
    crossDomain: false, // obviates need for sameOrigin test
    beforeSend: function(xhr, settings) {
        if (!csrfSafeMethod(settings.type)) {
            xhr.setRequestHeader('X-CSRFToken', csrftoken);
        }
    }
});

// Playback notifications for statistics
function ajax_notify(id)
{
    $.ajax({
        type: 'POST',
        url: '/journal/',
        data: {
            'id': id
        }
    })
}

//AJAX navigation with HTML5 History API
function ajax_navigate(url, nopush, data, method) {
        if(typeof(method)=='undefined') method='GET';
        $.ajax({
            data: data,
            dataType: 'json',
            type: method,
            url: url,
            cache: true, // doesn't work
            success: function(data, status, xhr){
                // TODO: Check if response contains valid JSON, display error message otherwise
                $('#content').html('');
                $('html').scrollTop(0);
                document.title=(data.title?data.title+' - ':'')+'{{ PROJECT_NAME }}';
                $('#content').html(data.content);
                // Update URL and push the history item
                // To make this happen immediately after the click, the following code must be moved to the beginning of ajax_navigate()
                // Problem: it won't work there because the new URL can't be set until we don't have the page title
                // Problem: we want to restore scroll position on history pop event, but to do this, we must set it for state object
                //of the page when we are leaving it, not when we've just loaded it
                if(!nopush)
                {
                    history.pushState({url: url}, data.title, url);
                    //restore #id of playing recording
                }
            },
        // Display error messages on the request failure
        error: function(jqXHR, textStatus, errorThrown){
            document.write(jqXHR.responseText);
        }
    });
}
$(window).bind('popstate', function(event){
    ajax_navigate(event.originalEvent.state.url, true);
});
function playfile(filename) {
    $('#jquery_jplayer_1').jPlayer('setMedia', {mp3: filename});
    $('#jquery_jplayer_1').jPlayer('play', 0);
    //notify server (for playback statistics)
}
// TODO: move messages to low right corner
function showmessage(text, mode) {
    if(mode!='error'&&mode!='success'&&mode!='info') mode='info';
    $('#messages').prepend('<div class="alert alert-'+mode+'"><a class="close" data-dismiss="alert">×</a>'+text+'</div>');
}
// Extra elements which show up on mouseover (e. g., edit icons) toggling
// 'show-extras' class element: shows 'extras' elements in 'hide-extras' block it resides in (can be itself)
// 'hide-extras' class element: hides 'extras' elements inside its own block
// e. g. ['hide-extras block' ['show-extras icon'] 'extras 1' 'extras 2' ... ]
$(document).on('mouseenter', '.show-extras', function(){
    $(this).closest('.hide-extras').find('.extras').css('display', '');
});
$(document).on('mouseleave', '.hide-extras', function(){
    $(this).find('.extras').css('display', 'none');
});
// Finally...
$(document).ready(function(){
    // Adapt body padding to navbar height
    // Shouldn't mix JS with CSS this way, must get values from stylesheet and add navbar height to the top one
    $('body').css('padding', ($('.navbar').height()+10)+'px 10px 10px');
    //
    $('body').click(function(event) {
        // Play button
        if($(event.target).hasClass('action-play')){
            playfile($(event.target).closest('a').attr('href'));
            ajax_notify($(event.target).closest('div.recording').data('id'));
            return false;
        }
        // Poetry view button
        else if($(event.target).hasClass('action-poetry-view')){
            $('#modal-poetry-viewer').find('.modal-text-title').html($(event.target).closest('div.piece').find('.title').html());
            $('#modal-poetry-viewer').find('.modal-body').html('');
            // Get text and insert it into the modal
            // TODO: figure out why does the background page change to main if /poetry/<id> is redirected to /
            $.get('/poetry/'+$(event.target).closest('div.poetry').data('id'), function(data) {
                $('#modal-poetry-viewer').find('.modal-body').html(data.replace(/\n/g,'<br>'));
            });
            // Show modal
            // TODO: somewhy the modal shows up before the text is received (confusingly displaying previously viewed text, if we don't clear it first)
            $('#modal-poetry-viewer').modal();
            return false;
        }
        // AJAX'ify links
        // http://docs.jquery.com/Tutorials:AJAX_and_Events
        // Also make foreign links open in a new tab
        // !!! Doesn't work for children inside <a>! Must check not target.is(<a>), but target.hasParent(<a>)
        else link=$(event.target).closest('a'); if(link.length && link.attr('href').charAt(0)=='/') {
            ajax_navigate(link.attr('href'));
            return false;
        }
        //AJAX'ify forms
        else if($(event.target).is('input') && $(event.target).attr('type')=='submit') {
            if(typeof($(event.target).parents('form:first').attr('action'))=='undefined')
                $(event.target).parents('form:first').attr('action', window.location.pathname);
            if($(event.target).parents('form:first').attr('action').charAt(0)=='/')
            {
                ajax_navigate($(event.target).parents('form:first').attr('action'), false, $(event.target).parents('form:first').serialize(), $(event.target).parents('form:first').attr('method'));
                return false;
            }
        }
    });
    //jPlayer stuff
    var	player = $('#jquery_jplayer_1'),
    player_progress=$('.player_progress'); //for performance
    player.jPlayer({
        ready: function () {
            //$('#jp_container .track-default').click();
        },
        //Initially controls are in disabled state, must enable them on canplay event
        loadstart:  function(event) {
            $('.player_play').removeClass('disabled');
            $('.player_bar').css('cursor', 'pointer');
        },
        //Progress bar: sync with current playback time
        timeupdate: function(event) {
            player_progress.css('width', event.jPlayer.status.currentPercentAbsolute+'%');
            //console.log(player_progress.attr('style'));
        },
        //Play/pause button toggling: hide player_play/show player_pause and vice versa
        play: function(event) {
            $('.player_play').css('display', 'none');
            $('.player_pause').css('display', '');
        },
        pause: function(event) {
            $('.player_pause').css('display', 'none');
            $('.player_play').css('display', '');
        },
        volume: 1,
        swfPath: STATIC_URL+'jplayer/Jplayer.swf'
    });
    //Play/pause click
    $('.player_pause').click(function(event){
        player.jPlayer('pause');
    });
    $('.player_play').click(function(event){
        player.jPlayer('play');
    });
    //Progress bar: click event handler to set time calculated from relative coordinates
    $('.player_bar').click(function(event){
        time=player.data('jPlayer').status.duration*(event.pageX-$(this).offset().left)/$(this).width()
        player.jPlayer('play', time);
    });
});

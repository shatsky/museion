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
                document.title=(data.title?data.title+' - ':'')+PROJECT_NAME;
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
        // Poetry view button
        if($(event.target).hasClass('action-poetry-view')){
            $('#modal-poetry-viewer').find('.modal-text-title').html($(event.target).closest('div.piece').find('.title').html());
            $('#modal-poetry-viewer').find('.modal-body').html('');
            // Get text and insert it into the modal
            // TODO: figure out why does the background page change to main if /poetry/<id> is redirected to /
            $.get('/poetry/text/'+$(event.target).closest('div.poetry').data('id'), function(data) {
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
});

function hashbang_get_vars(url) {
	url = url || window.location.href;
	var vars = {};
	var hashes = url.slice(url.indexOf('#') + 1).split('&');
    for(var i = 0; i < hashes.length; i++) {
        var hash = hashes[i].split('=');
        if(hash.length > 1) vars[hash[0]] = hash[1];
        else vars[hash[0]] = null;
    }
    return vars;
}

function hashbang_set_vars(vars){
    hash = '';
    for (var key in vars) {
        hash += key + '=' + vars[key] + '&';
    }
    if(hash.length>0) hash = hash.slice(0, -1);
    window.location.hash = hash;
}

function playfile(filename) {
    // if current src is the same, and player is on pause, we resume rather than play from the beginning
    if($('#jquery_jplayer_1').data('jPlayer').status.src==filename) $('#jquery_jplayer_1').jPlayer('play');
    // otherwise, we pause it before setting a new src to restore "play" icon in previous recording block
    else {
        $('#jquery_jplayer_1').jPlayer('pause');
        $('#jquery_jplayer_1').jPlayer('setMedia', {mp3: filename});
        $('#jquery_jplayer_1').jPlayer('play', 0);
    }
}

// Playback notifications for statistics
function ajax_notify(id)
{
    $.ajax({
        type: 'POST',
        url: '/journal/',
        data: {
            'id': id
        }
    });
}

function player_play(recording_id, recording_file) {
    // get file url
    if(recording_file===undefined) {
        recording_file = $('.recording[data-id="'+recording_id+'"]').find('a.action-play').attr('href');
    }
    // play file
    playfile(recording_file);
    // update hashbang
    hashbang_set_vars({'recording': recording_id});
    // send journal event
    ajax_notify(recording_id);
}

$(document).ready(function(){
    // jPlayer stuff
    var	player = $('#jquery_jplayer_1'),
    player_progress=$('.player_progress'); //for performance
    player.jPlayer({
        ready: function () {
            //$('#jp_container .track-default').click();
            // play recording from the hashbang argument
            hashbang_args=hashbang_get_vars();
            if(hashbang_args['recording']!==undefined) {
                player_play(hashbang_args['recording']);
                // scroll page to recording
                //$('.recording[data-id="'+hashbang_args['recording']+'"]').closest('.piece').scrollIntoView();
                $('html, body').animate({
                    scrollTop: $('.recording[data-id="'+hashbang_args['recording']+'"]').closest('.piece').offset().top -50
                }, 2000);
            }
        },
        // initially controls are in disabled state, must enable them on canplay event
        loadstart:  function(event) {
            $('.player_play').removeClass('disabled');
            $('.player_bar').css('cursor', 'pointer');
        },
        // progress bar: sync with current playback time
        timeupdate: function(event) {
            player_progress.css('width', event.jPlayer.status.currentPercentAbsolute+'%');
            //console.log(player_progress.attr('style'));
        },
        // play/pause button toggling: hide player_play/show player_pause and vice versa
        play: function(event) {
            $('.player_play').css('display', 'none');
            $('.player_pause').css('display', '');
            $('a.action-play[href="'+event.jPlayer.status.src+'"]').find('i').removeClass('icon-play');
            $('a.action-play[href="'+event.jPlayer.status.src+'"]').find('i').addClass('icon-pause');
        },
        pause: function(event) {
            $('.player_pause').css('display', 'none');
            $('.player_play').css('display', '');
            $('a.action-play[href="'+event.jPlayer.status.src+'"]').find('i').removeClass('icon-pause');
            $('a.action-play[href="'+event.jPlayer.status.src+'"]').find('i').addClass('icon-play');
        },
        ended: function(event) {
            $('.player_pause').css('display', 'none');
            $('.player_play').css('display', '');
            $('a.action-play[href="'+event.jPlayer.status.src+'"]').find('i').removeClass('icon-pause');
            $('a.action-play[href="'+event.jPlayer.status.src+'"]').find('i').addClass('icon-play');
        },
        volume: 1,
        swfPath: STATIC_URL+'jplayer/Jplayer.swf'
    });
    // play/pause click
    $('.player_pause').click(function(event){
        player.jPlayer('pause');
    });
    $('.player_play').click(function(event){
        player.jPlayer('play');
    });
    // progress bar: click event handler to set time calculated from relative coordinates
    $('.player_bar').click(function(event){
        time=player.data('jPlayer').status.duration*(event.pageX-$(this).offset().left)/$(this).width()
        player.jPlayer('play', time);
    });
    // Play button
    $('body').on('click', 'a.action-play', function() {
        //playfile($(event.target).closest('a').attr('href'));
        //ajax_notify($(event.target).closest('div.recording').data('id'));
        // if this recording is currently playing, we pause the player
        if($(this).find('i').hasClass('icon-pause')) $('.player_pause').click();
        // otherwise, we submit it to the player_play()
        else player_play($(this).closest('div.recording').data('id'), $(this).attr('href'));
        return false;
    });
});

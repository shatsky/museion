/*
This script handles title and related-piece inputs
It assumes that there is name=title input for title and class=related-piece input for related piece
If there is a piece id in related-piece output, it replaces title input with a piece info block
If "delete association" button is pressed in the piece info block, in clears related-piece input and restores title input
If a piece suggestion is picked up from a title input, it puts its id into related-piece input
*/

var piece_input;
// why cant't I access this from functions?
var form_model=$('#form-model').html();

function update_related_piece(data)
{
    //hide title input, replace it with piece info block
    $('input[name=title]').closest('.twitter-typeahead').css('display', 'none');
    $('input[name=title]').closest('.controls').append('<div class="title-piece" style="padding-top:5px">'+data+' <button class="btn btn-danger btn-mini delete-title-assoc">Удалить связь</button></div>');    
}

function process_related_piece_inputs(){
    $('input.related-piece').each(function() {
        // we assume that this related piece is a base piece for our object
        // get its description to display in title block
        // this means a request to server backend, right?
        // how can we get piece model?
        // we can send form model and field
        if(this.value != '') {
            $.get( '/util/piece_info?id='+this.value+'&model='+$('#form-model').html()+'&field='+$(this).attr('name'), function( data ) {
                update_related_piece(data);
                $('input[name=title]').typeahead('val', $('input[name=title]').closest('.controls').find('.title').html());
            });
            piece_input=this;
            return false;
        }
    });
}

// typeahead: suggestion template
function piece_suggestion_template() {
    return function f(context) {
        return '<p>'+context['title']+'<br><font size="1">'+context['description']+'</font></p>';
    }
}

// typeahead: suggestions array fetch function
function piece_suggestions_fetch(){
    return function findMatches(q, cb) {
        max_length=5;
        var suggestions=[];
        $.ajax({
            url: '/util/piece_suggestions?l='+max_length+'&q='+q+'&model='+$('#form-model').html()+'&field='+$('input.related-piece:first').attr('name'),
            type: 'get',
            dataType: 'json',
            async: false,
            success: function(data) {
                suggestions = data;
            }
        })
        // if the list is too long (>~10 suggestions), cut it and add "..." message indicating there are more matches in the database
        // don't cut if all items are 100% matches
        if(suggestions.length>max_length&&suggestions[suggestions.length-1]!=q) suggestions=suggestions.slice(0, max_length);
        // add as-is string suggestion
        suggestions.push({'title': q});
        cb(suggestions);
    }
}

$(document).ready(function(){
    // typeahead
    $('input[name=title]').typeahead({
        minLength: 3,
        highlight: true,
    }, {
        name: 'my-dataset',
        displayKey: 'title',
        source: piece_suggestions_fetch(),
        templates: {
            suggestion: piece_suggestion_template()
        }
    });
    $('input[name=title]').bind('typeahead:selected', function(event, suggestion, dataset){
        // clear piece inputs
        $('input.related-piece').each(function() {
            $(this).val('');
        });
        if(suggestion['id']!==undefined) {
            // update piece input
            piece_input=$('input[name='+suggestion['field']+']');
            $(piece_input).val(suggestion['id']);
            // update piece info
            //update_related_piece(suggestion['data']);
            // we don't want to fetch both suggestion- and title-templated pieces blocks in suggestions_fetch
            process_related_piece_inputs();
        }
    });
    // after typeahead initialization, because we need to set input value via typeahead method
    process_related_piece_inputs();
    // deleting association with related object
    $('body').on('click', '.delete-title-assoc', function(event) {
        // remove piece block
        $(this).closest('.title-piece').remove();
        // clean piece-related input
        $(piece_input).val('');
        // restore title input
        $('input[name=title]').closest('.twitter-typeahead').css('display', '');
        event.preventDefault();
    });
});

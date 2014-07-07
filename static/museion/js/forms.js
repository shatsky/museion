function is_integer(variable) {
    return typeof field[i] === 'number' && field[i] % 1 == 0
}

function list_append(list_container, element) {
    //element [{'id': pk}, {'name': name}, {'type': type}]
    list_container.append('<span class="list-item tag label" data-pk="'+element['id']+'"><span class="name">'+element['name']+'</span>'+' <i class="icon-remove action-delete-item"></i></span>');
}

function json_to_list(json_field, list_container) {
    field=JSON.parse(json_field.val())
    //request data for elements represented by pks
    pks=[];
    for(i=0; i<field.length; i++) {
        if(is_integer(field[i])) pks.push(field[i]);
    }
    pks=pks.join();
    if(pks!=''){
        var prepopulate="";
        $.ajax({
            url: '/util/tokeninput/prepopulate/person?q='+pks,
            type: 'get',
            dataType: 'json',
            async: false,
            success: function(data) {
                prepopulate = data;
            }
        });
    }
    //insert elements into list
    for(i=0; i<field.length; i++) {
        if(is_integer(field[i])) list_append(list_container, {'id': field[i], 'name': prepopulate[field[i]]['name'], 'type': prepopulate[field[i]]['type']});
        else list_append(list_container, {'id': undefined, 'name': field[i], 'type': 'unknown'});
    }
}

function list_to_json(list_container, json_field) {
    field=[]
    list_container.children().each(function() {
        if(this.dataset.pk=="undefined") field.push($(this).find('.name')[0].innerHTML);
        else field.push(parseInt(this.dataset.pk));
    });
    json_field.val(JSON.stringify(field));
}

// typeahead: suggestion template
function suggestion_template() {
    return function f(context) {
        if(context['type']!='unknown') return '<p>'+context['name']+'<br><font size="1" color="gray">id: '+context['id']+'</font></p>';
        else return '<p class="unknown">'+context['name']+'<br><font size="1" color="gray">Добавить неизвестное имя</font></p>';
    }
}

// typeahead: suggestions array fetch function
function autocomp_fetch(){
    return function findMatches(q, cb) {
        max_length=5;
        var suggestions=[];
        $.ajax({
            url: '/util/tokeninput/autocomplete/person?l='+max_length+'&q='+q,
            type: 'get',
            dataType: 'json',
            async: false,
            success: function(data) {
                suggestions = data;
            }
        })
        // if the list is too long (>~10 suggestions), cut it and add "..." message indicating there are more matches in the database
        if(suggestions.length>max_length) {
            suggestions=suggestions.slice(0, max_length);
            //suggestions.push();
        }
        // add as-is string suggestion, if no 100% match in the list
        if(suggestions.length==0||suggestions[0]['name']!=q) suggestions.push({'name': q, 'type': 'unknown'});
        cb(suggestions);
    }
}

$(document).ready(function(){
    // fill visible people list from JSON
    json_to_list($(m2mjson_field_sel), $(m2mjson_list_sel))
    // typeahead
    $('#typeahead').typeahead({
        minLength: 3,
        highlight: true,
    }, {
        name: 'my-dataset',
        displayKey: 'name',
        source: autocomp_fetch(),
        templates: {
            suggestion: suggestion_template()
        }
    });
    $('#typeahead').bind('typeahead:selected', function(event, suggestion, dataset){
        list_append($(m2mjson_list_sel), suggestion);
        // strangely, .val('') doesn't work: input gets cleared, but when it looses focus, selected value re-appears
        $(event.target).typeahead('val', '');
    });
    // click handler for item deletion icon
    $('body').on('click', '.action-delete-item', function() {
        $(this).closest('.list-item').remove();
    });
    // debug
    $(m2mjson_field_sel).click(function(event) {
        list_to_json($(m2mjson_list_sel), $(m2mjson_field_sel));
    });
});

function list_append(list_container, element) {
    //element [{'id': pk}, {'name': name}, {'type': type}]
    list_container.append('<span class="list-item tag label" data-pk="'+element['id']+'"><span class="name">'+element['name']+'</span>'+' <i class="icon-remove action-delete-item"></i></span>');
}

function json_to_list(json_field, list_container) {
    field=JSON.parse(json_field.val())
    //request data for elements represented by pks
    pks=[];
    for(i=0; i<field.length; i++) {
        if(Number.isInteger(field[i])) pks.push(field[i]);
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
        if(Number.isInteger(field[i])) {
            list_append(list_container, {'id': field[i], 'name': prepopulate[field[i]]['name'], 'type': prepopulate[field[i]]['type']});
        }
        else {
            list_append(list_container, {'id': undefined, 'name': field[i], 'type': 'unknown'});
        }
    }
}

function list_to_json(list_container, json_field) {
    field=[]
    list_container.children().each(function() {
        if(this.dataset.pk=="undefined"){
            field.push($(this).find('.name')[0].innerHTML);
        }
        else field.push(parseInt(this.dataset.pk));
    });
    json_field.val(JSON.stringify(field));
}

$(document).ready(function(){
    // fill visible people list from JSON
    json_to_list($(m2mjson_field_sel), $(m2mjson_list_sel))
    // typeahead
    function autocomp_fetch(){
        return function findMatches(q, cb) {
            var suggestions=[];
            $.ajax({
                url: '/util/tokeninput/autocomplete/person?q='+q,
                type: 'get',
                dataType: 'json',
                async: false,
                success: function(data) {
                    suggestions = data;
                }
            })
            // TODO: if the list is too long (>~10 suggestions), cut it and add "..." message indicating there are more matches in the database
            // add as-is string suggestion, if no 100% match in the list
            if(suggestions.length==0||suggestions[0]['name']!=q) {
                suggestions.push({'name': q});
            }
            cb(suggestions);
        }
    }
    $('#typeahead').typeahead({
        minLength: 3,
        highlight: true,
    }, {
        name: 'my-dataset',
        displayKey: 'name',
        source: autocomp_fetch()
    });
    $('#typeahead').bind('typeahead:selected', function(event, suggestion, dataset){
        list_append($(m2mjson_list_sel), suggestion);
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

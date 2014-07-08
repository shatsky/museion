// We currently expect that every m2m-json field is nested inside class="m2m-json" container, which contains:
// - one non-class="m2m-user-input" input for json string (hidden input which is actually submitted);
// - one class="m2m-list" container for displaying chosen items: its children are class="m2m-list-item" elements with class="m2m-action-remove-item" icons;
// - one class="m2m-user-input" input for typeahead plugin (nameless input for searching and selecting items from the database)

function is_integer(variable) {
    return typeof field[i] === 'number' && field[i] % 1 == 0
}

function list_append(list_container, element) {
    //element [{'id': pk}, {'name': name}, {'type': type}]
    list_container.append('<span class="m2m-list-item tag label'+((element['type']=='unknown')?' label-important':' label-success')+'" data-pk="'+element['id']+'"><span class="name">'+element['name']+'</span>'+' <i class="icon-remove icon-white m2m-action-remove-item"></i></span>');
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
    $('form').find('.m2m-json').each(function(){
        json_to_list($(this).find('input:not(.m2m-user-input)'), $(this).find('.m2m-list'));
    });
    // typeahead
    $('.m2m-user-input').typeahead({
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
    $('.m2m-user-input').bind('typeahead:selected', function(event, suggestion, dataset){
        list_append($(event.target).closest('.m2m-json').find('.m2m-list'), suggestion);
        // strangely, .val('') doesn't work: input gets cleared, but when it looses focus, selected value re-appears
        $(event.target).typeahead('val', '');
    });
    // click handler for item deletion icon
    $('body').on('click', '.m2m-action-remove-item', function() {
        $(this).closest('.m2m-list-item').remove();
    });
    // form submission
    $('form').submit(function(event) {
        //event.preventDefault();
        // in every m2m-json block, sync its hidden input with its items list
        $(event.target).find('.m2m-json').each(function() {
            list_to_json($(this).find('.m2m-list'), $(this).find('input:not(.m2m-user-input)'));
            console.log($(this).find('input:not(.m2m-user-input)').val());
        });
    });
});

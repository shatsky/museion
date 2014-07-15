def objects_tree(object, depth=0):
    related_array=[]
    # for each related model get all related objects
    for related in object.__class__._meta.get_all_related_objects():
        related_objects = related.model.objects.filter(**{related.field.name: object})
        for related_object in related_objects:
            # dirty hack:
            # if and object is Poetry object and related_object is a Recording object,
            # and if it references this Poetry object via music - ignore it
            if object.__class__.__name__=='Poetry' and related_object.__class__.__name__=='Recording' and related_object.music is not None and related_object.music.poetry==object: continue
            related_array+=[objects_tree(related_object, depth+1)]
    return {'object': object, 'related': related_array}

def related_forms(model):
    """Build a list of dicts for links to related objects creation forms"""
    return [{'url': related.model.get_create_url(), 'field': related.field.name, 'text': related.model._meta.verbose_name} for related in model._meta.get_all_related_objects() if 'get_create_url' in dir(related.model)]

def creation_form_context(form):
    return {
        'form': form,
        # form model name to be used in JS
        'model': form.instance.__class__.__name__,
        # show links to associated music pieces
        'objects_tree': objects_tree(form.instance)['related'],
        # show links to create related objects
        'related_forms': related_forms(form.instance.__class__),
    }

from django.db.models import Q
def compose_title_query(model, query, *args, **kwargs):
    """
    Search model objects by title, which can be inherited from other objects via fks or stored in self.title, if all suitable fks are null
    Title is looked up in the first object which is referenced by the non-null fk and has a title field; if there are none, self.title field is looked up
    Of course, this logic is recursive
    Priority is definded by the model field order
    """
    if 'suffix' not in kwargs.keys(): kwargs['suffix']=''
    if 'prefix' not in kwargs.keys(): kwargs['prefix']=''
    else: kwargs['prefix']+='__'
    result=[]
    for field in model._meta.fields:
        if field.__class__.__name__=='ForeignKey' and 'title' in field.related.parent_model._meta.get_all_field_names():
            # we should ensure that the further parts of the query will be added with &Q(**{field, None})
            # write the remainder to other variable and add is as |(Q(**{field, None})&remainder) in the end... somehow?
            # that's why we declared result as an array
            # on each step we append a dictionary of two items to it
            #  'query' is a query part which checks for title in a current fk-referenced object, if fk is not None
            #  'remainder' is a check that fk is None, to be &-added to remainder of the query which doesn't exist yet
            # after looping through fields, we will loop through the array in reversed direction, adding |(remainder[i]&query[i+1]) to query[i]
            # and result[0] will become the final result
            #result_array.append({'query': '~Q('+prefix+field.name+'=None)&('+search_query(field.related.parent_model, prefix+field.name, query)+')', 'remainder': 'Q('+prefix+field.name+'=None)'})
            result.append({'query':~Q(**{field.name: None})&compose_title_query(field.related.parent_model, query, *args, **dict(kwargs, prefix=kwargs['prefix']+field.name)), 'remainder': Q(**{kwargs['prefix']+field.name: None})})
        elif field.name=='title':
            #result_array.append({'query':'Q('+prefix+'title=\''+query+'\')'})
            result.append({'query':Q(**{kwargs['prefix']+'title'+kwargs['suffix']: query})})
    # turn result into a single query
    result=list(reversed(result))
    for i in xrange(len(result)-1):
        #result_array[i+1]['query']='('+result_array[i+1]['query']+')|(('+result_array[i+1]['remainder']+')&('+result_array[i]['query']+'))'
        result[i+1]['query']=result[i+1]['query']|(result[i+1]['remainder']&result[i]['query'])
    return result[len(result)-1]['query']

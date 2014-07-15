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
        # show links to associated music pieces
        'objects_tree': objects_tree(form.instance)['related'],
        # show links to create related objects
        'related_forms': related_forms(form.instance.__class__),
    }

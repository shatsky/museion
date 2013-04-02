# coding=UTF-8
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from djmuslib import models
from django.db.models import Q
from django import template
from django.template import loader
from django.shortcuts import render_to_response
# To pack AJAX replies
from django.utils import simplejson

# Processing initial request
def init(request):
    t=template.loader.get_template('init.htm')
    c=template.RequestContext(request, {
        'url':request.get_full_path,
    })
    return HttpResponse(t.render(c))

# List people
# in certain category
def people(request, category):
    if not request.is_ajax(): return init(request)
    if category=='poets': category='poetry'
    elif category=='composers': category='music'
    elif category=='performers': category='recording'
    people=models.person.objects.exclude(**{category:None}).order_by('name')
    # Template and responce    
    t=template.loader.get_template('people.htm')
    c=template.RequestContext(request, {
    'people': people,
    'category': category,
    })
    #for p in models.person.objects.exclude(**{category:None}).order_by('name'):
    #    output+="<a href='/people/"+str(p.id)+"'>"+p.name+"</a> ("+str(len(getattr(p, category+'_set').all()))+")<br>"
    return HttpResponse(simplejson.dumps({'title':'', 'content':t.render(c)}), mimetype='application/json')

# Show details about given person
# List all related recordings
def person(request, id):
    # /people/(id) addresses are bad, because id isn't guaranteed to remain persistent, messing clients bookmarks and history
    # /people/(name) should be used instead, name is persistent and unique in models.pesron
    # ! Should we really replace " " with "_"? What about non-breakable space?
    # Cache fragments are still identified by person id supplied through person.htm template
    try:
        int(id)
        return HttpResponseRedirect('/people/'+models.person.objects.get(id=id).name.replace(" ", "_"))
    except ValueError:
        if not request.is_ajax(): return init(request)
        p=models.person.objects.get(name=id.replace("_", " "))
    # Journaling
    models.journal.objects.create(address=request.META.get('REMOTE_ADDR'), agent=request.META.get('HTTP_USER_AGENT'), event='v', view_url=request.get_full_path())
    # problem! we can have no recording.poetry - in this case we must get title from recording.music
    # strange: somehow it used to work without 'poetry', 'music' in order_by()
    # giving all recordings with same (poetry_id, music_id) pair placed continiously in the result
    # but then it broke down, messing regroup by piece_id()
    r=models.recording.objects.filter(Q(performers=p)|Q(music__composers=p)|Q(poetry__poets=p)).distinct().order_by('poetry__title', 'poetry', 'music')
    # Template and responce
    t=template.loader.get_template('person.htm')
    c=template.RequestContext(request, {
    'title': p.name,
    'person': p,
    'recordings': r,
    })
    return HttpResponse(simplejson.dumps({'title':p.name, 'content':t.render(c)}), mimetype='application/json')

# Search results
def search(request):
    if not request.is_ajax(): return init(request)
    # Journaling
    models.journal.objects.create(address=request.META.get('REMOTE_ADDR'), agent=request.META.get('HTTP_USER_AGENT'), event='s', search_query=request.GET.get('q'), search_mode=request.GET.get('m'))
    # Output depends on the query mode
    # In title query mode we return list of recordings with relevant titles
    # In name query mode we return list of people and groups with relevant names
    # In poetry query mode we return list of recordings with matching lyrics (lyrics fragments embedded in list and highlighted)
    if request.GET.get('m')!='t': return HttpResponse(u'Пока реализован только поиск по названиям.')
    # Template and responce
    t=template.loader.get_template('search.htm')
    c=template.RequestContext(request, {
    'title': u'Поиск',
    'search': request.GET.get('q'),
    'recordings': models.recording.objects.filter(poetry__in=models.poetry.search.query(request.GET.get('q'))),
    })
    return HttpResponse(simplejson.dumps({'title':'', 'content':t.render(c)}), mimetype='application/json')

def login(request):
    if request.method=='POST':
        # log in user
        return HttpResponseRedirect('/')
    else:
        return render_to_response('login.htm', context_instance=template.RequestContext(request))

def logout(request):
    return HttpResponse('')

"""
<form method='post' action='/edit/person'>
<input name='name' value='{{ p.name }}'>
<input type='submit'>
</form>
"""

def edit_person(request, id=None):
    if request.method=='GET':
        # show form
        # if id is provided - fill it with actual values
        from django.forms.models import modelformset_factory
        PersonFormSet = modelformset_factory(models.person)
        formset=PersonFormSet(queryset=models.person.objects.filter(id=id))
        return HttpResponse('<table>'+str(formset)+'</table>')
        if id is not None:
            p=models.person.objects.get(id=id)
            c=template.RequestContext(request, {
            'p': p,
            })
        else:
            c=template.RequestContext(request, {})
        return render_to_response('form_person.htm', context_instance=c)
    else:
        # validate input
        # if id is provided - modify record with given id
        # otherwise - create a new one
        pass
    return HttpResponseRedirect('')

def edit_poetry(request, id):
    return HttpResponse('')

def edit_music(request, id):
    return HttpResponse('')

def edit_recording(request, id):
    return HttpResponse('')

# Journal representation
# Is it a nice solution to have three separate journals for three different types of events?
# It requires complicated join to represent all events in a single stream
# Another problem is page views representation
# We'd like to see page titles in journal, this requires duplicating title code from other view functions
# Events: view, listen, search, edit
def journal(request):
    if request.method=='POST': # AJAX notification about client-side events
        # Playback
        models.journal.objects.create(address=request.META.get('REMOTE_ADDR'), agent=request.META.get('HTTP_USER_AGENT'), event='p', playback_recording=models.recording.objects.get(id=request.POST.get('id')))
        return HttpResponse('')
    if not request.is_ajax(): return init(request)
    t=template.loader.get_template('journal.htm')
    c=template.RequestContext(request, {
        'events': models.journal.objects.all().order_by('-timestamp')[:10],
    })
    return HttpResponse(simplejson.dumps({'title':'', 'content':t.render(c)}), mimetype='application/json')

def ajax_test(request):
    if not request.is_ajax(): return init(request)
    # This is AJAX function, it must return JSON containing data and title
    return HttpResponse(simplejson.dumps({'title':'Title', 'content':'Content'}), mimetype='application/json')

def default(request):
    if not request.is_ajax(): return init(request)
    t=template.loader.get_template('main.htm')
    c=template.RequestContext(request, {
        'greeting': open('./djmuslib/FAQ.ru.md').read(),
    })
    return HttpResponse(simplejson.dumps({'title':'', 'content':t.render(c)}), mimetype='application/json')

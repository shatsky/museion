# coding=UTF-8
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from djmuslib import models
from django.db.models import Q
from django import template
from django.template import loader
from django.shortcuts import render_to_response

# List people
# in certain category
def people(request, category):
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
    return HttpResponse(t.render(c))

# Show details about given person
# including all related recordings
def person(request, id):
    # problem! we can have no recording.poetry - in this case we must get title from recording.music
    p=models.person.objects.get(id=id)
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
    return HttpResponse(t.render(c))

# Search results
def search(request):
    if request.GET.get('what')!='title': return HttpResponse(u'Пока реализован только поиск по названиям.')
    title=request.GET.get('title')
    r=models.recording.objects.filter(poetry__in=models.poetry.search.query(title))
    # Template and responce
    t=template.loader.get_template('search.htm')
    c=template.RequestContext(request, {
    'title': u'Поиск',
    'search': title,
    'recordings': r,
    })
    return HttpResponse(t.render(c))

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

def default(request):
    return render_to_response('layout.htm', context_instance=template.RequestContext(request))

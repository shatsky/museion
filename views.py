# coding=UTF-8
from django.http import HttpResponse
from djmuslib import models
from django.db.models import Q
from django import template
from django.template import loader

def people(request, category):
    if category=='poets': category='poetry'
    elif category=='composers': category='music'
    elif category=='performers': category='recording'
    people=models.person.objects.exclude(**{category:None}).order_by('name')
    t=template.loader.get_template('people.htm')
    c=template.RequestContext(request, {
    'people': people,
    'category': category,
    })
    #for p in models.person.objects.exclude(**{category:None}).order_by('name'):
    #    output+="<a href='/people/"+str(p.id)+"'>"+p.name+"</a> ("+str(len(getattr(p, category+'_set').all()))+")<br>"
    return HttpResponse(t.render(c))

def person(request, id):
    # problem! we can have no recording.poetry - in this case we must get title from recording.music
    t=template.loader.get_template('person.htm')
    p=models.person.objects.get(id=id)
    r=models.recording.objects.filter(Q(performers=p)|Q(music__composers=p)|Q(poetry__poets=p)).distinct().order_by('poetry__title')
    c=template.RequestContext(request, {
    'title': p.name,
    'person': p,
    'recordings': r,
    })
    return HttpResponse(t.render(c))

def search(request):
    if request.GET.get('what')!='title': return HttpResponse(u'Пока реализован только поиск по названиям.')
    title=request.GET.get('title')
    r=models.recording.objects.filter(poetry__in=models.poetry.search.query(title))
    t=template.loader.get_template('search.htm')
    c=template.RequestContext(request, {
    'title': u'Поиск',
    'search': title,
    'recordings': r,
    })
    return HttpResponse(t.render(c))

def default(request):
    t=template.loader.get_template('layout.htm')
    c=template.RequestContext(request, {})
    return HttpResponse(t.render(c))

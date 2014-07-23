# coding=UTF-8
import django
from django.http import HttpResponse
from museion import models
import utils
from django.db.models import Q
from django.db.models import Count
from django.template.loader import get_template
from django.template import RequestContext
# To pack AJAX replies
from django.utils import simplejson
# Gettext
from django.utils.translation import ugettext as _
# Event journaling
from visitors_journal.utils import journal_event

# non-PEP8-compliant name to mimic HttpResponse constructor calls in view functions
# maybe, this should be rewritten as an object inheriting from HttpResponse with a modified constructor?
def XHttpResponse(request, data):
    """
    eXtended HttpResponse wrapper which detects the right way to serve response data, depending on request details:
    embedded in layout template (for initial request) or in json (for subsequent AJAX requests);
    then returns it via HttpResponse
    """
    if not request.is_ajax():
        # update context dictionary with some global variables
        # TODO: move their values to the settings, and (if possible) their insertion into context to an external template context processor
        data.update({'PROJECT_NAME':'Непопулярная музыка'})
        return HttpResponse(get_template('layout.htm').render(RequestContext(request, data)))
    else:
        return HttpResponse(simplejson.dumps(data), mimetype='application/json')

def person(request, name):
    """Shows details about given person with a list of all related pieces and recordings"""
    journal_event(models.Journal, request, {'event':'v', 'view_url':request.get_full_path()})
    # id-based addresses are bad, because id isn't guaranteed to remain persistent, messing clients bookmarks and history
    # name-based should be used instead, name is persistent and unique in models.pesron
    # Cache fragments are still identified by person id supplied through person.htm template
    # Would be nice to use try...except here to provide error message in DoesNotExist case with similar existing names
    person = models.Person.objects.get(name=name.replace("_", " "))
    recordings = models.Recording.objects.select_related('poetry', 'music').prefetch_related('performers', 'poetry__poets', 'music__composers', 'production_set').filter(Q(performers=person)|Q(music__composers=person)|Q(poetry__poets=person)).distinct().order_by('title', 'poetry', 'music')
    context = RequestContext(request, {
        'person': person,
        'recordings': recordings,
    })
    return XHttpResponse(request, {'title':person.name, 'content':get_template('person.htm').render(context)})

def people(request, category):
    """Lists all people which belong to a certain category"""
    related={'poets':'poetry', 'composers':'music', 'performers':'recording'}
    # Any person who have anything associated matching the selected category
    # =All people, excluding those who have nothing associated mathing the selected category
    # e. g., exclude(recording=None) will give us performers
    people = models.Person.objects.exclude(type='unknown').exclude(**{related[category]:None}).filter(**request.GET.dict()).annotate(related__count=Count(related[category])).order_by('name')
    context = RequestContext(request, {
        'people': people,
        'category': category,
    })
    return XHttpResponse(request, {'title':'', 'content':get_template('people_alphabetical.htm').render(context)})

def search_query(arg, vals):
    """Returns a query built from AND-joined Q objects"""
    query = Q(**{arg:vals[0]})
    if len(vals) > 1:
        for val in vals[1:]:
            query.add(Q(**{arg:val}), Q.AND)
    return query

def search_words(query_string):
    """Splits a query string into words and returns a list of regexps matching these words"""
    # word boundaries are expressed differenly in different database engines
    word_start = word_end = r'\y'
    import re
    return [word_start+'('+word+')'+word_end for word in re.sub('\s+', ' ', query_string).split(' ')]

def search_title(request, title):
    """Searches recordings by title"""
    journal_event(models.Journal, request, {'event':'s', 'search_query':title, 'search_mode':'t'})
    # Multiple search methods: sphinx (if available) and simple substring^W db regex (as a fallback)
    try:
        # TODO this query duplicates Recording.title_piece_object logic, as well as the query in the 'except:' branch
        # implementing an abstraction for title inheritance will be a very complex task
        recordings = models.Recording.objects.select_related('poetry', 'music').prefetch_related('performers', 'poetry__poets', 'music__composers', 'production_set').filter((~Q(poetry=None)&Q(poetry__in=models.Poetry.search.query(title)))|(Q(poetry=None)&~Q(music=None)&~Q(music__poetry=None)&Q(music__poetry__in=models.Poetry.search.query(title)))|(Q(poetry=None)&~Q(music=None)&Q(music__poetry=None)&Q(music__in=models.Music.search.query(title)))).order_by('title', 'poetry', 'music')
    except:
        words = search_words(title)
        recordings = models.Recording.objects.select_related('poetry', 'music').prefetch_related('performers', 'poetry__poets', 'music__composers', 'production_set').filter((Q(poetry=None)&((Q(music__poetry=None)&search_query('music__title__iregex', words))|search_query('music__poetry__title__iregex', words)))|search_query('poetry__title__iregex', words)).order_by('title', 'poetry', 'music')
    context = RequestContext(request, {
        'search': title,
        'recordings': recordings,
    })
    return XHttpResponse(request, {'title':u'Поиск', 'content':get_template('search.htm').render(context)})

# In text search mode we want to show matching fragment above any piece block
def search_text(request, text):
    """Searches recordings by poetry text fragment"""
    journal_event(models.Journal, request, {'event':'s', 'search_query':text, 'search_mode':'p'})
    words = search_words(text)
    recordings = models.Recording.objects.select_related('poetry', 'music').prefetch_related('performers', 'poetry__poets', 'music__composers', 'production_set').filter(poetry__in=models.Poetry.objects.filter(search_query('text__iregex', words))).order_by('title', 'poetry', 'music')
    context = RequestContext(request, {
        'search': text,
        'recordings': recordings,
    })
    return XHttpResponse(request, {'title':u'Поиск', 'content':get_template('search.htm').render(context)})

def search_name(request, name):
    """Searches people by name"""
    journal_event(models.Journal, request, {'event':'s', 'search_query':name, 'search_mode':'n'})
    words = search_words(name)
    people = models.Person.objects.filter(search_query('name__iregex', words))
    context = RequestContext(request, {
        'search': name,
        'people': people,
    })
    return XHttpResponse(request, {'title':u'Поиск', 'content':get_template('people.htm').render(context)})

def poetry_text(request, id):
    """Returns poetry text by id (for poetry view modal window)"""
    return HttpResponse(models.Poetry.objects.get(id=id).text)

# Session management
import django.contrib.auth.views

def login(request, **kwargs):
    #return django.contrib.auth.views.login(request, {'template_name': 'login.htm'})
    #settings.LOGIN_REDIRECT_URL = '/'
    # 'next' GET var in the template points to the refresh page to update the navbar
    # TODO: move its assignment here (unfortunately, login() function, unlike logout(), doesn't accept next_page parameter)
    response = django.contrib.auth.views.login(request, template_name='login.htm')
    try: return XHttpResponse(request, {'title':'', 'content':response.render().content})
    except: return response

def logout(request):
    return django.contrib.auth.views.logout(request, next_page='/refresh')

def refresh(request):
    """
    Returns a page which causes a full refresh, updating session block in the navbar
    Its template has a simple JS redirecting to the main page via window.location
    """
    # TODO: redirect to pre-login/logout page
    return HttpResponse(simplejson.dumps({'content':get_template('refresh.htm').render(RequestContext(request, {}))}), mimetype='application/json')
def user_profile(request):
    return
def registration(request):
    return

# Content editing
# These methods must have a protection from unauthorized access

from museion import forms

# Tokeninput backend functions
def prepopulate_person(request):
    autocomp = {}
    for p in models.Person.objects.filter(id__in=request.GET.get('q').split(',')):
        autocomp[p.id]={'name':p.name, 'type':p.type, 'url': p.get_absolute_url()}
    return HttpResponse(simplejson.dumps(autocomp))

def autocomplete_person(request):
    q=request.GET.get('q')
    length=int(request.GET.get('l'))
    from itertools import chain
    initial_queryset=models.Person.objects.exclude(type='unknown')
    # we want exact match first (if one exists), then matches which start with query string, then other matches
    queryset=initial_queryset.filter(name__iexact=q)
    # we expect that queryset.len()<=1
    queryset=list(chain(queryset, initial_queryset.filter(name__istartswith=q).exclude(name__iexact=q)[:length-len(queryset)]))
    if len(queryset)<length:
        # no need to exclude iexact, because iexact result will be in istartswidth
        queryset=list(chain(queryset, initial_queryset.filter(name__icontains=q).exclude(name__istartswith=q)[:length-len(queryset)]))
    autocomp = []
    for p in queryset:
        autocomp.append({'id':p.id, 'name': p.name, 'type': p.type, 'url': p.get_absolute_url()})
    return HttpResponse(simplejson.dumps(autocomp))

# A single edit_person for individuals, groups and unknown names: form class is chosen dynamically based on instance.type
def edit_person(request, id=None):
    """Shows a form for editing person objects"""
    # form class depends on instance type
    instance = (models.Person.objects.get(id=id) if id is not None else None)
    submitted_type = (request.GET.get('type') if request.method == 'GET' else (request.POST.get('type') if request.method == 'POST' else ''))
    if   submitted_type == 'individual' or (instance is not None and instance.type == 'individual'): form = forms.Individual
    elif submitted_type == 'group'      or (instance is not None and instance.type == 'group'):      form = forms.Group
    form = form(getattr(request, request.method), **{'instance': instance} if instance is not None else {})
    #if request.method == 'POST': form.save()
    context = RequestContext(request, {
        'form': form,
    })
    return XHttpResponse(request, {'content':get_template('form.htm').render(context)})

def piece_info(request):
    """Information about linked piece"""
    piece=getattr(getattr(models, request.GET.get('model')), request.GET.get('field')).field.related.parent_model.objects.get(id=request.GET.get('id'))
    return HttpResponse('<div class="title">'+piece.get_title+'</div> '+get_template('object_info.htm').render(RequestContext(request, {'object': piece})))

def piece_suggestions(request):
    """Suggestions for title/piece input"""
    q=request.GET.get('q')
    length=int(request.GET.get('l'))
    field=request.GET.get('field')
    model=getattr(getattr(models, request.GET.get('model')), field).field.related.parent_model
    suggestions=[]
    for item in model.objects.filter(utils.compose_title_query(model, q, suffix='__icontains')):
        suggestions.append({'field': field, 'id': item.id, 'title': item.get_title, 'data': 'test'})
    return HttpResponse(simplejson.dumps(suggestions))

def edit_poetry(request, id=None):
    """Shows a form for editing poetry objects"""
    instance=(models.Poetry.objects.get(id=id) if id is not None else None)
    # this limits choices to already listed people
    #forms.Poetry.base_fields['poets'] = forms.ModelM2MJSONField(queryset=(instance.poets if instance is not None else models.Person.objects.none()))
    form = (forms.Poetry(getattr(request, request.method)) if instance is None else forms.Poetry((request.POST if request.method == 'POST' else None), instance=instance))
    if request.method == 'POST':
        try: form.save(commit=False)
        except:
            import sys
            print sys.exc_info()
    context = RequestContext(request, dict(utils.creation_form_context(form), **{
        'title': u'Изменение информации о тексте',
    }))
    return XHttpResponse(request, {'title':context['title'], 'content':get_template('form.htm').render(context)})

def edit_music(request, id=None):
    """Shows a form for editing music objects"""
    #form = forms.Music((request.POST if request.method == 'POST' else None), instance=(models.Music.objects.get(id=id) if id is not None else None))
    form = (forms.Music(getattr(request, request.method)) if id is None else forms.Music((request.POST if request.method == 'POST' else None), instance=models.Music.objects.get(id=id)))
    #if request.method == 'POST': form.save()
    context = RequestContext(request, dict(utils.creation_form_context(form), **{
        'title': u'Изменение информации о музыкальном произведении',
    }))
    return XHttpResponse(request, {'title':context['title'], 'content':get_template('form.htm').render(context)})

def edit_recording(request, id=None):
    """Shows a form for editing recording objects"""
    form = (forms.Recording(getattr(request, request.method)) if id is None else forms.Recording((request.POST if request.method == 'POST' else None), instance=models.Recording.objects.get(id=id)))
    context = RequestContext(request, dict(utils.creation_form_context(form), **{
        'title': u'Изменение информации об аудиозаписи',
    }))
    return XHttpResponse(request, {'title':context['title'], 'content':get_template('form.htm').render(context)})


# Journal and statistics
# Is it a nice solution to have three separate journals for three different types of events?
# It requires complicated join to represent all events in a single stream
# Another problem is page views representation
# We'd like to see page titles in journal, this requires duplicating title code from other view functions
# Events: view, listen, search, edit
def journal(request):
    """Events journaling: POST event to log or GET journal webpage"""
    if request.method == 'POST': # AJAX notification about client-side events
        # Playback
        journal_event(models.Journal, request, {'event':'p', 'playback_recording':models.Recording.objects.get(id=request.POST.get('id'))})
        return HttpResponse('')
    context = RequestContext(request, {
        'events': models.Journal.objects.all().order_by('-timestamp')[:10],
    })
    return XHttpResponse(request, {'title':'', 'content':get_template('journal.htm').render(context)})

def top_recordings(request):
    """Show most listened recordings"""
    recordings = models.Recording.objects.annotate(Count('journal')).order_by('-journal__count')[:20]
    context = RequestContext(request, {
        'recordings': recordings,
    })
    return XHttpResponse(request, {'title':u'Самые популярные', 'content':get_template('recordings.htm').render(context)})

def main(request):
    import os
    context = RequestContext(request, {
        'greeting': open(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'FAQ.ru.md')).read(),
    })
    return XHttpResponse(request, {'content':get_template('main.htm').render(context)})


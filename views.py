# coding=UTF-8
import django
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from djmuslib import models
from django.db.models import Q
from django import template
from django.template import loader
from django.shortcuts import render_to_response
# To pack AJAX replies
from django.utils import simplejson
# Gettext
from django.utils.translation import ugettext as _

# Processing initial request
# In every other view the part intented to respond GET requests with some viewable content begins with
#if not request.is_ajax(): return init(request)
# This way client will get base layout with JS warning and a small script to load content from given URL via AJAX
# TODO: extend to enable POST requests
def init(request):
    t=template.loader.get_template('init.htm')
    c=template.RequestContext(request, {
        'url':request.get_full_path,
    })
    return HttpResponse(t.render(c))

# Show details about given person
# List all related recordings
def person(request, name):
    if not request.is_ajax(): return init(request)
    # Journaling
    models.journal.objects.create(address=(request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR')), agent=request.META.get('HTTP_USER_AGENT'), event='v', view_url=request.get_full_path())
    # id-based addresses are bad, because id isn't guaranteed to remain persistent, messing clients bookmarks and history
    # name-based should be used instead, name is persistent and unique in models.pesron
    # ! Should we really replace " " with "_"? What about non-breakable space?
    # Cache fragments are still identified by person id supplied through person.htm template
    # Would be nice to use try...except here to provide error message in DoesNotExist case with similar existing names
    p=models.person.objects.get(name=name.replace("_", " "))
    # TODO sorting by poetry__title is bad because pieces without poetry fall out of order
    #  extra recording.title field? phytonic sort?
    r=models.recording.objects.select_related('poetry', 'music').prefetch_related('performers', 'poetry__poets', 'music__composers').filter(Q(performers=p)|Q(music__composers=p)|Q(poetry__poets=p)).distinct().order_by('poetry__title', 'poetry', 'music')
    t=template.loader.get_template('person.htm')
    # Template and responce
    c=template.RequestContext(request, {
        'title': p.name,
        'person': p,
        'recordings': r,
    })
    return HttpResponse(simplejson.dumps({'title':p.name, 'content':t.render(c)}), mimetype='application/json')

# List people
# in certain category
def people(request, category):
    if not request.is_ajax(): return init(request)
    if category=='poets': category='poetry'
    elif category=='composers': category='music'
    elif category=='performers': category='recording'
    # Any person who have anything associated matching the selected category
    #=All people, excluding those who have nothing associated mathing the selected category
    # e. g., exclude(recording=None)
    people=models.person.objects.exclude(type='unknown').exclude(**{category:None}).order_by('name')
    # Template and responce    
    t=template.loader.get_template('people.htm')
    c=template.RequestContext(request, {
        'people': people,
        'category': category,
    })
    #for p in models.person.objects.exclude(**{category:None}).order_by('name'):
    #    output+="<a href='/people/"+str(p.id)+"'>"+p.name+"</a> ("+str(len(getattr(p, category+'_set').all()))+")<br>"
    return HttpResponse(simplejson.dumps({'title':'', 'content':t.render(c)}), mimetype='application/json')

# Search results
def search_title(request):
    if not request.is_ajax(): return init(request)
    # Journaling
    models.journal.objects.create(address=(request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR')), agent=request.META.get('HTTP_USER_AGENT'), event='s', search_query=request.GET.get('q'), search_mode=request.GET.get('m'))
    # Output depends on the query mode
    # In title query mode we return list of recordings with relevant titles
    # In name query mode we return list of people and groups with relevant names
    # In poetry query mode we return list of recordings with matching lyrics (lyrics fragments embedded in list and highlighted)
    if request.GET.get('m')!='t': return HttpResponse(u'Пока реализован только поиск по названиям.')
    # Template and responce
    t=template.loader.get_template('search.htm')
    # Multiple search methods: sphinx (if available) and simple substring (as a fallback)
    try: r=models.recording.objects.filter(poetry__in=models.poetry.search.query(request.GET.get('q')))
    except: r=models.recording.objects.filter(poetry__in=models.poetry.objects.filter(title__contains=request.GET.get('q')))
    c=template.RequestContext(request, {
        'title': u'Поиск',
        'search': request.GET.get('q'),
        'recordings': r,
    })
    return HttpResponse(simplejson.dumps({'title':'', 'content':t.render(c)}), mimetype='application/json')

# In text search mode we want to show matching fragment above any piece block
def search_text(request):
    return

def search_name(request):
    return

# Poetry text by id (for poetry view modal window)
def poetry_text(request, id):
    return HttpResponse(models.poetry.objects.get(id=id).text)

# Session management
import django.contrib.auth.views

def login(request, **kwargs):
    if not request.is_ajax(): return init(request)
    #return django.contrib.auth.views.login(request, {'template_name': 'login.htm'})
    #settings.LOGIN_REDIRECT_URL='/'
    # 'next' GET var in the template points to the refresh page to update the navbar
    # TODO: move its assignment here (unfortunately, login() function, unlike logout(), doesn't accept next_page parameter)
    response=django.contrib.auth.views.login(request, template_name='login.htm')
    try: return HttpResponse(simplejson.dumps({'title':'', 'content':response.render().content}), mimetype='application/json')
    except: return response

def logout(request):
    return django.contrib.auth.views.logout(request, next_page='/refresh')

# Refresh: returns a page which causes a full refresh, updating session block in the navbar
# Its template has a simple JS redirecting to the main page via window.location
# TODO: redirect to pre-login/logout page
def refresh(request):
    #if not request.is_ajax(): return init(request)
    return HttpResponse(simplejson.dumps({'content':template.loader.get_template('refresh.htm').render(template.RequestContext(request, {}))}), mimetype='application/json')
def user_profile(request):
    return
def registration(request):
    return

# Content editing
# These methods must have a protection from unauthorized access

# Poetry/music/recording forms
# By default, M2M authors/performers fields are represented with multiselect (which submits multiple instances of the variable)
# We want a text input instead (jquery tokeninput, which submits a string of comma-separated ids in one variable)
# We also need a validator to check several things: i. e. group cannot be an author

# By default, M2M is represented with ModelMultipleChoiceField, widget=SelectMultiple
# Simply replacing widget with TextInput causes validation error, even if SelectMultiple behaviour is simulated from the client side
# This class has been copypasted from stackoverflow discussion, and it does, suprisingly, make things work
# TODO: figure out how does it actually work, find a more elegant solution if possible
# http://stackoverflow.com/questions/4707192/django-how-to-build-a-custom-form-widget
# I thought the problem is that "input value to python structure" logic was somwhere in the widget, not in the field, which
# expects TextInput to return python array instead of the string; but the link above suggests it's actually in the field
class ModelCommaSeparatedChoiceField(django.forms.ModelMultipleChoiceField):
    widget = django.forms.TextInput
    def clean(self, value):
        if value is not None:
            value = [item.strip() for item in value.split(",")]  # remove padding
        return super(ModelCommaSeparatedChoiceField, self).clean(value)

# Individuals and groups are stored in a single table
# There are properties specific to only one of these types, e. g. gender for individual
# We need it to be represented with select input, only visible for individuals
class form_person(django.forms.ModelForm):
    class Meta:
        model=models.person
        fields=['name', 'subtype']

class form_poetry(django.forms.ModelForm):
    poets=ModelCommaSeparatedChoiceField(queryset=models.person.objects.filter())
    class Meta:
        model=models.poetry
        fields=['title', 'poets', 'text']
        #widgets={
        #    'poets':django.forms.widgets.TextInput(),
        #}
        # TODO: make labels work
        labels={
            'title':_(u'Название'),
            'poets':_(u'Поэты'),
            'text':_(u'Текст'),
        }

# Music can either inherit title from poetry (via poetry key, while title field is empty)
# or have ins own (in title field, with poetry key set to NULL)
# This logic is not fully controlled from the model, so we must have a pair of radiobuttuns to switch between two related inputs
# and a custom validator
class form_music(django.forms.ModelForm):
    class Meta:
        model=models.music
        fields=['poetry', 'title', 'composers']
        widgets={
            'poetry':django.forms.widgets.TextInput(),
            'composers':django.forms.widgets.TextInput(),
        }

class form_recording(django.forms.ModelForm):
    class Meta:
        model=models.recording
        fields=['poetry', 'music', 'performers', 'href']
        widgets={
            'poetry':django.forms.widgets.TextInput(),
            'music':django.forms.widgets.TextInput(),
            'performers':django.forms.widgets.TextInput(),
        }

# Tokeninput backend functions
def prepopulate_person(request):
    autocomp=[]
    for p in models.person.objects.filter(id__in=request.GET.get('q').split(',')):
        autocomp.append({'id':p.id, 'name': p.name})
    return HttpResponse(simplejson.dumps(autocomp))

def autocomplete_person(request):
    autocomp=[]
    for p in models.person.objects.filter(name__contains=request.GET.get('q')):
        autocomp.append({'id':p.id, 'name': p.name})
    return HttpResponse(simplejson.dumps(autocomp))

# Access control
# TODO: can we specify permissions at model level instead of using decorators at every dangerous function
# so that form.save() simply fails if the request.user has no permissions to edit related model?
from django.contrib.auth.decorators import user_passes_test
# TODO: define an 'editors' group and give its users permissions to edit content
# TODO: make an interface for superusers to control other users and their permissions
def check_editor(user):
    return user.is_superuser

# A single edit_person for groups and individuals?
# URL must be informative of which record type is being edited. e.g. /edit/person or /edit/group
# If URL is mismatching object type of a given id, we redirect to a correct one
@user_passes_test(check_editor)
def edit_person(request, id=None):
    if not request.is_ajax(): return init(request)
    form=form_person((request.POST if request.method=='POST' else None), instance=(models.person.objects.get(id=id) if id is not None else None))
    #if request.method=='POST': form.save()
    t=template.loader.get_template('form_person.htm')
    c=template.RequestContext(request, {
        'form': form.as_p(),
    })
    return HttpResponse(simplejson.dumps({'content':t.render(c)}), mimetype='application/json')
@user_passes_test(check_editor)
def edit_group(request, id=None):
    return HttpResponse('')

@user_passes_test(check_editor)
def edit_poetry(request, id=None):
    if not request.is_ajax(): return init(request)
    form=form_poetry((request.POST if request.method=='POST' else None), instance=(models.poetry.objects.get(id=id) if id is not None else None))
    #if request.method=='POST': form.save()
    t=template.loader.get_template('form_poetry.htm')
    c=template.RequestContext(request, {
        'form': form,
        # Show links to associated music pieces
        'music': (models.music.objects.filter(poetry=models.poetry.objects.get(id=id)) if id is not None else None),
    })
    return HttpResponse(simplejson.dumps({'content':t.render(c)}), mimetype='application/json')

# Music can either inherit title from poetry it war written for, or have its own one
@user_passes_test(check_editor)
def edit_music(request, id=None):
    if not request.is_ajax(): return init(request)
    form=form_music((request.POST if request.method=='POST' else None), instance=(models.music.objects.get(id=id) if id is not None else None))
    #if request.method=='POST': form.save()
    t=template.loader.get_template('form_music.htm')
    c=template.RequestContext(request, {
        'form': form,
    })
    return HttpResponse(simplejson.dumps({'content':t.render(c)}), mimetype='application/json')

@user_passes_test(check_editor)
def edit_recording(request, id=None):
    return HttpResponse('')

# Journal and statistics
# Is it a nice solution to have three separate journals for three different types of events?
# It requires complicated join to represent all events in a single stream
# Another problem is page views representation
# We'd like to see page titles in journal, this requires duplicating title code from other view functions
# Events: view, listen, search, edit
def journal(request):
    if request.method=='POST': # AJAX notification about client-side events
        # Playback
        models.journal.objects.create(address=(request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR')), agent=request.META.get('HTTP_USER_AGENT'), event='p', playback_recording=models.recording.objects.get(id=request.POST.get('id')))
        return HttpResponse('')
    if not request.is_ajax(): return init(request)
    t=template.loader.get_template('journal.htm')
    c=template.RequestContext(request, {
        'events': models.journal.objects.all().order_by('-timestamp')[:10],
    })
    return HttpResponse(simplejson.dumps({'title':'', 'content':t.render(c)}), mimetype='application/json')

def top_recordings(request):
    t=template.loader.get_template('recordings.htm')
    # Select most listened recordings
    # Looks like the only way to do this is to have counter field calculated from journal
    r=models.recording.objects.all()[:10]
    c=template.RequestContext(request, {
        'title': u'Самые популярные',
        'search': request.GET.get('q'),
        'recordings': r,
    })
    return HttpResponse(simplejson.dumps({'title':'', 'content':t.render(c)}), mimetype='application/json')

# TODO: get rid of 'if not request.is_ajax...' at the beginning for every normal view function
def ajax_test(request):
    if not request.is_ajax(): return init(request)
    # This is AJAX function, it must return JSON containing data and title
    return HttpResponse(simplejson.dumps({'title':'Title', 'content':'Content'}), mimetype='application/json')

def main(request):
    if not request.is_ajax(): return init(request)
    t=template.loader.get_template('main.htm')
    c=template.RequestContext(request, {
        'greeting': open('./djmuslib/FAQ.ru.md').read(),
    })
    return HttpResponse(simplejson.dumps({'title':'', 'content':t.render(c)}), mimetype='application/json')

# Unknown URLs redirect to the main page
def default(request):
    request.path='/'
    request.META['QUERY_STRING']=''
    # TODO: We must return redirect block in json, not in layout.htm
    return init(request)

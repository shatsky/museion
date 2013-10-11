# coding=UTF-8
import django
from django.http import HttpResponse
from djmuslib import models
from django.db.models import Q
from django.db.models import Count
from django.template.loader import get_template
from django.template import RequestContext
# To pack AJAX replies
from django.utils import simplejson
# Gettext
from django.utils.translation import ugettext as _

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
    # Journaling
    models.Journal.objects.create(address=(request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR')), agent=request.META.get('HTTP_USER_AGENT'), event='v', view_url=request.get_full_path())
    # id-based addresses are bad, because id isn't guaranteed to remain persistent, messing clients bookmarks and history
    # name-based should be used instead, name is persistent and unique in models.pesron
    # ! Should we really replace " " with "_"? What about non-breakable space?
    # Cache fragments are still identified by person id supplied through person.htm template
    # Would be nice to use try...except here to provide error message in DoesNotExist case with similar existing names
    person = models.Person.objects.get(name=name.replace("_", " "))
    # TODO sorting by poetry__title is bad because pieces without poetry fall out of order
    #  extra recording.title field? phytonic sort?
    recordings = models.Recording.objects.select_related('poetry', 'music').prefetch_related('performers', 'poetry__poets', 'music__composers').filter(Q(performers=person)|Q(music__composers=person)|Q(poetry__poets=person)).distinct().order_by('title', 'poetry', 'music')
    context = RequestContext(request, {
        'person': person,
        'recordings': recordings,
    })
    return XHttpResponse(request, {'title':person.name, 'content':get_template('person.htm').render(context)})

def people(request, category):
    """Lists all people which belong to a certain category"""
    if category == 'poets': category = 'poetry'
    elif category == 'composers': category = 'music'
    elif category == 'performers': category = 'recording'
    # Any person who have anything associated matching the selected category
    #=All people, excluding those who have nothing associated mathing the selected category
    # e. g., exclude(recording=None)
    people = models.Person.objects.exclude(type='unknown').exclude(**{category:None}).annotate(related__count=Count(category)).order_by('name')
    context = RequestContext(request, {
        'people': people,
        'category': category,
    })
    return XHttpResponse(request, {'title':'', 'content':get_template('people.htm').render(context)})

def search_query(arg, vals):
    """Returns a query built from AND-joined Q objects"""
    query = Q(**{arg:vals[0]})
    if len(vals) > 1:
        for val in vals[1:]:
            query.add(Q(**{arg:val}), Q.AND)
    return query

def search_title(request):
    """Shows search results"""
    # Journaling
    models.Journal.objects.create(address=(request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR')), agent=request.META.get('HTTP_USER_AGENT'), event='s', search_query=request.GET.get('q'), search_mode=request.GET.get('m'))
    # Output depends on the query mode
    # In title query mode we return list of recordings with relevant titles
    # In name query mode we return list of people and groups with relevant names
    # In poetry query mode we return list of recordings with matching lyrics (lyrics fragments embedded in list and highlighted)
    if request.GET.get('m') != 't': return HttpResponse(u'Пока реализован только поиск по названиям.')
    # Multiple search methods: sphinx (if available) and simple substring^W db regex (as a fallback)
    try:
        # TODO this query duplicates Recording.title_piece_object logic, as well as the query in the 'except:' branch
        # implementing an abstraction for title inheritance will be a very complex task
        recordings = models.Recording.objects.select_related('poetry', 'music').prefetch_related('performers', 'poetry__poets', 'music__composers').filter((~Q(poetry=None)&Q(poetry__in=models.Poetry.search.query(request.GET.get('q'))))|(Q(poetry=None)&~Q(music=None)&~Q(music__poetry=None)&Q(music__poetry__in=models.Poetry.search.query(request.GET.get('q'))))|(Q(poetry=None)&~Q(music=None)&Q(music__poetry=None)&Q(music__in=models.Music.search.query(request.GET.get('q'))))).order_by('title', 'poetry', 'music')
    except:
        # split query string into words to construct AND-joined iregex-matching queries from them
        # word boundaries are expressed differenly in different database engines
        word_start = word_end = r'\y'
        import re
        words=[word_start+'('+word+')'+word_end for word in re.sub('\s+', ' ', request.GET.get('q')).split(' ')]
        recordings = models.Recording.objects.select_related('poetry', 'music').prefetch_related('performers', 'poetry__poets', 'music__composers').filter((Q(poetry=None)&((Q(music__poetry=None)&search_query('music__title__iregex', words))|search_query('music__poetry__title__iregex', words)))|search_query('poetry__title__iregex', words)).order_by('title', 'poetry', 'music')
    context = RequestContext(request, {
        'search': request.GET.get('q'),
        'recordings': recordings,
    })
    return XHttpResponse(request, {'title':u'Поиск', 'content':get_template('search.htm').render(context)})

# In text search mode we want to show matching fragment above any piece block
def search_text(request):
    return

def search_name(request):
    return

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
        model = models.Person
        fields = ['name', 'subtype']

class form_poetry(django.forms.ModelForm):
    poets = ModelCommaSeparatedChoiceField(queryset=models.Person.objects.filter())
    class Meta:
        model = models.Poetry
        fields = ['title', 'poets', 'text']
        #widgets = {
        #    'poets':django.forms.widgets.TextInput(),
        #}
        # TODO: make labels work
        labels = {
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
        model = models.Music
        fields = ['poetry', 'title', 'composers']
        widgets = {
            'poetry':django.forms.widgets.TextInput(),
            'composers':django.forms.widgets.TextInput(),
        }

class form_recording(django.forms.ModelForm):
    class Meta:
        model = models.Recording
        fields = ['poetry', 'music', 'performers', 'href']
        widgets = {
            'poetry':django.forms.widgets.TextInput(),
            'music':django.forms.widgets.TextInput(),
            'performers':django.forms.widgets.TextInput(),
        }

# Tokeninput backend functions
def prepopulate_person(request):
    autocomp = []
    for p in models.Person.objects.filter(id__in=request.GET.get('q').split(',')):
        autocomp.append({'id':p.id, 'name': p.name})
    return HttpResponse(simplejson.dumps(autocomp))

def autocomplete_person(request):
    autocomp = []
    for p in models.Person.objects.filter(name__contains=request.GET.get('q')):
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
    form=form_person((request.POST if request.method == 'POST' else None), instance=(models.Person.objects.get(id=id) if id is not None else None))
    #if request.method == 'POST': form.save()
    context = RequestContext(request, {
        'form': form.as_p(),
    })
    return XHttpResponse(request, {'content':get_template('form_person.htm').render(context)})
@user_passes_test(check_editor)
def edit_group(request, id=None):
    return HttpResponse('')

@user_passes_test(check_editor)
def edit_poetry(request, id=None):
    form = form_poetry((request.POST if request.method == 'POST' else None), instance=(models.Poetry.objects.get(id=id) if id is not None else None))
    #if request.method == 'POST': form.save()
    context = RequestContext(request, {
        'form': form,
        # Show links to associated music pieces
        'music': (models.Music.objects.filter(poetry=models.Poetry.objects.get(id=id)) if id is not None else None),
    })
    return XHttpResponse(request, {'content':get_template('form_poetry.htm').render(context)})

# Music can either inherit title from poetry it war written for, or have its own one
@user_passes_test(check_editor)
def edit_music(request, id=None):
    form = form_music((request.POST if request.method == 'POST' else None), instance=(models.Music.objects.get(id=id) if id is not None else None))
    #if request.method == 'POST': form.save()
    context = RequestContext(request, {
        'form': form,
    })
    return XHttpResponse(request, {'content':get_template('form_music.htm').render(context)})

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
    """Events journaling: POST event to log or GET journal webpage"""
    if request.method == 'POST': # AJAX notification about client-side events
        # Playback
        models.Journal.objects.create(address=(request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR')), agent=request.META.get('HTTP_USER_AGENT'), event='p', playback_recording=models.Recording.objects.get(id=request.POST.get('id')))
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


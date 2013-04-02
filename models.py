from django.db import models
from djangosphinx import SphinxSearch

import logging
logger = logging.getLogger(__name__)

import re

class ext_person_link(models.Model):
    href=models.URLField(unique=True)
    FORMAT_CHOICES=(('kkre', 'kkre "title (composers - poets) performers" format'),)
    format=models.CharField(max_length=255, choices=FORMAT_CHOICES, blank=True)
    def __unicode__(self):
        return '[%s] %s' % (self.format, self.href)

class kkre_person_category(models.Model):
    category=models.CharField(max_length=255, unique=True)
    def __unicode__(self):
        return self.category

# Person
# We have multiple name forms which are derived from full one
# Problem: if we store them as fields, we can't be shure they are in sync with full form
# if we have functions to get them on the fly, we can't use them in sort operations
# We store both individuals and groups here
# Problem:
# Problem: groups can be only performers, but not authors; we don't have such a constraint
# Problem: individuals can take part in groups 
class person(models.Model):
    # Must write a validator to forbid "category", "_", number-only names (enough?) here
    name=models.CharField(max_length=255, unique=True)
    name_e=models.CharField(max_length=255)
    name_short=models.CharField(max_length=255)
    #name_abbrv=models.CharField(max_length=255)
    type=models.CharField(max_length=255)
    category=models.ManyToManyField(kkre_person_category)
    # we can explicitly define manytomany table for this
    # to store start...end page offsets for each person
    # (kkre has many multi-person pages)
    links=models.ManyToManyField(ext_person_link)
    def __unicode__(self):
        return self.name
    # first letter to regroup in people directory
    def first_letter(self):
        try: return self.name[0]
        except: return ''
    def name_abbrv(self):
        if self.type=='male' or self.type=='female':
            name_abbrv=''
            name_part=re.sub('\s\([^)]*\)', '', self.name).split(' ') # throw out parts in brackets, split by whitespaces
            if len(name_part)>=1:
                name_abbrv=name_part[0]
                if len(name_part)>=2: name_abbrv=name_part[1][0]+'. '+name_abbrv # 'N. Surname'
            return name_abbrv
        else: return self.name

class poetry(models.Model):
    title=models.CharField(max_length=255)
    poets=models.ManyToManyField(person)
    def __unicode__(self):
        return self.title
    search = SphinxSearch(
        index='title'
    )
    def save(self):
        print('called poetry save()')
        old=poetry.objects.get(pk=self.pk)
        print('old:')
        print(old.title)
        super(poetry, self).save()
        print('new:')
        print(self.title)

class music(models.Model):
    title=models.CharField(max_length=255)
    poetry=models.ForeignKey(poetry)
    composers=models.ManyToManyField(person)

class recording(models.Model):
    poetry=models.ForeignKey(poetry, blank=True, null=True, on_delete=models.SET_NULL)
    music=models.ForeignKey(music, blank=True, null=True, on_delete=models.SET_NULL)
    performers=models.ManyToManyField(person)
    href=models.URLField(unique=True)
    def __unicode__(self):
        return self.href
    def piece_title(self):
        if self.poetry: return self.poetry.title
        elif self.music: return self.music.title
    def piece_id(self):
        poetry_id=''
        music_id=''
        if self.poetry: poetry_id=self.poetry.id
        if self.music: music_id=self.music.id
        return '%s %s' %(str(poetry_id), str(music_id))

class kkre_recording_link(models.Model):
    recording=models.ForeignKey(recording)
    href=models.ForeignKey(ext_person_link)
    title=models.CharField(max_length=255)
    description=models.CharField(max_length=255)
    class Meta:
        unique_together=("recording", "href")

# Journaling
# -----------------
from django.contrib.auth.models import User

# Unified journal
class journal(models.Model):
    timestamp=models.DateTimeField(auto_now_add=True)
    address=models.IPAddressField()
    agent=models.CharField(max_length=255)
    user=models.ForeignKey(User, blank=True, null=True, on_delete=models.SET_NULL)
    EVENT_CHOICES=(
        ('v', 'page view'),
        ('s', 'search query'),
        ('p', 'recording playback'),
    )
    event=models.CharField(max_length=1, choices=EVENT_CHOICES)
    # Page view fields
    view_url=models.CharField(max_length=255)
    # Search query fields
    search_query=models.CharField(max_length=255)
    MODE_CHOICES=(
        ('n', 'in names'),
        ('t', 'in titles'),
        ('p', 'in poetry'),
    )
    search_mode=models.CharField(max_length=1, choices=MODE_CHOICES)
    # Recording playback fields
    playback_recording=models.ForeignKey(recording, blank=True, null=True)

# Event-driven cache invalidation
# -------------------------------

from django.db.models import signals
from django.core.cache import cache
from django.utils.http import urlquote
import hashlib

# Cache key for template fragment
# This should be in Django API
def template_cache_key(fragment_name='', *args):
    return 'template.cache.%s.%s' % (fragment_name, hashlib.md5(u':'.join([urlquote(arg) for arg in args])).hexdigest())

# On M2M change (list of people related to certain object has been modified)
# Poetry/music/recording: invalidate all recording lists it appears in
#   all people which are in both old and new M2M lists;
#   invalidate people lists which depend on count
def poets_changed(sender, **kwargs):
    if kwargs['action']=='pre_add' or kwargs['action']=='pre_remove':
        print('caught '+kwargs['action']+' from ')
        print(sender)
        old=poetry.objects.get(pk=kwargs['instance'].pk)
        print('old:')
        print(old.poets.all())
        print('new:')
        print(kwargs['instance'].poets.all())
        for pk in kwargs['pk_set']:
            cache.delete(template_cache_key('recordings_person', pk))

# On object change
# Poetry/music/recording: invalidate all recording lists it appears in
#   pages of all related people
# Person: invalidate person's page and all the other pages on which this person appears
#   problem: get list of all people related to given one
#   person.objects.filter(Q())
def poetry_changed(sender, instance, signal, *args, **kwargs):
    old=poetry.objects.get(pk=instance.pk)
    print('pre_save caught!')
    print('old:')
    print(old.poets.all())
    print(old.title)
    print('new:')
    print(instance.poets.all())
    print(instance.title)

# Create: not needed, because anything appears on pages only by M2M relation, which is set after creation
# Delete: not needed, if M2M is unset before deletion (?)

signals.m2m_changed.connect(poets_changed, sender=poetry.poets.through)
signals.pre_save.connect(poetry_changed, sender=poetry)

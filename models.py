# coding=UTF-8

from django.db import models
from djangosphinx import SphinxSearch

import logging
logger = logging.getLogger(__name__)

import re

# Person: all individuals and groups are stored here
# Again, we don't use explicit distinction for categories like "poets", etc.
# Every person can be referenced from poetry.poets/music.composers/recording.performers
# Problem: groups can be only performers, but not authors; we don't have a constraint to ensure this
# Problem: individuals and groups can have different properties, e. g., nationality is only for individuals
# Problem: individuals can take part in groups 
# We have multiple name forms which are derived from full one
# Problem: if we store them as fields, we can't be shure they are in sync with full form,
#and if we have functions to get them on the fly, we can't use them in sort operations
class person(models.Model):
    # Must write a validator to forbid "category", "_", number-only names (enough?) here
    name=models.CharField(max_length=255, unique=True)
    name_short=models.CharField(max_length=255)
    # individual or group
    type=models.CharField(max_length=255)
    # gender for individual, maybe format for group
    subtype=models.CharField(max_length=255)
    search = SphinxSearch(index='name')
    def __unicode__(self):
        return self.name
    # first letter to regroup in people directory
    def first_letter(self):
        try: return self.name[0]
        except: return ''
    # Name form to use in descriptions
    def name_clean(self):
        # Throw out parts in brackets
        name=re.sub('\s\([^)]*\)', '', self.name)
        return name
    def name_short(self):
        name=self.name_clean()
        if self.type=='individual': # Name Surname
            name_parts=name.split(', ')
            # Unshortable name part
            name=name_parts[0]
            # First word of the shortable part
            if len(name_parts)>1:
                name=name_parts[1].split(' ')[0]+' '+name # 'Name Surname'
            return name
        elif self.type=='group' and self.subtype=='ussrvia':
            return name.replace(u'Вокально-инструментальный ансамбль', u'ВИА')
        else: return name
    def name_abbrv(self):
        name=self.name_clean()
        if self.type=='individual': # N. Surname
            name_parts=name.split(', ') #split by comma
            # Unshortable name part
            name=name_parts[0]
            # First letter of the first word of the shortable part
            if len(name_parts)>1 and len(name_parts[1])>0:
                name=name_parts[1][0]+'. '+name # 'N. Surname'
            return name
        else: return self.name_short()
    # Name form to use in URLs
    def name_url(self):
        return self.name.replace(" ", "_")

class poetry(models.Model):
    title=models.CharField(max_length=255)
    poets=models.ManyToManyField(person)
    text=models.TextField(blank=True)
    year=models.DateField(null=True)
    def __unicode__(self):
        return self.title
    search = SphinxSearch(index='title')
    search_text = SphinxSearch(index='text')
    # Debugging cache invalidation
    #def save(self):
    #    print('called poetry save()')
    #    old=poetry.objects.get(pk=self.pk)
    #    print('old:')
    #    print(old.title)
    #    super(poetry, self).save()
    #    print('new:')
    #    print(self.title)

# "Music" here stands for musical piece itself, not a recording of its performers
# Sheet music goes here
class music(models.Model):
    title=models.CharField(max_length=255)
    # If music has been written for the specific poetry, we can leave music.title empty, but set music.poetry pointer
    #to reference this poetry and inherit title from it
    poetry=models.ForeignKey(poetry, null=True)
    composers=models.ManyToManyField(person)
    def __unicode__(self):
        if self.poetry is not None:
            return self.poetry.title
        else:
            return self.title

class recording(models.Model):
    # We don't have a "piece" object with pointers to music and lyrics forming one piece together
    # Instead, we have there pointers in recording
    # on_delete=models.SET_NULL essential to avoid losing recordings if we wipe music or poetry records
    poetry=models.ForeignKey(poetry, blank=True, null=True, on_delete=models.SET_NULL)
    music=models.ForeignKey(music, blank=True, null=True, on_delete=models.SET_NULL)
    # Performers list
    performers=models.ManyToManyField(person)
    # Audiofile address
    href=models.URLField(unique=True)
    # To disable/hide recordings we can't play because of copyright
    legal_status=models.CharField(max_length=255)
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

# For import from external websites
# ---------------------------------

# Links to people pages from external websites
# Can be also used to import content
# For this task we need to know the format of the external page
#to be able to parse things like recording lists on it
class ext_person_link(models.Model):
    people=models.ManyToManyField(person)
    # we can explicitly define manytomany table for this
    # to store start...end page offsets for each person
    # (kkre has many multi-person pages)
    href=models.URLField(unique=True)
    # recordings M2M via ext_recording_link
    # funny thing is that while I described ext_recording_link connecting these tables times ago,
    # the idea of putting M2M here came to me only after I've faced a need to select recordings by referencing ext_person_link
    recordings=models.ManyToManyField(recording, through='ext_recording_link')
    # Known formats
    FORMAT_CHOICES=(('kkre', 'kkre "title (composers - poets) performers" format'),)
    format=models.CharField(max_length=255, choices=FORMAT_CHOICES, blank=True)
    def __unicode__(self):
        return '[%s] %s' % (self.format, self.href)

# Categories like "poet", "composer", "performer"
# Although we categorise people using actual information, e. g,
#if the person has any poetry associated via poetry.poets, it will be shown in "poets" category,
#we may need to supply categories explicitly for new people who have no related content yet
#to import information from external website, e. g, if there is an external website page about some person
#with a recordings list on it, and there is a recording in the list that has "performer" information omitted,
#and from this table we know that this person is known as a performer,
#then we can make a safe assumption that this person is a performer for this recording
class ext_person_category(models.Model):
    people=models.ManyToManyField(person)
    category=models.CharField(max_length=255, unique=True)
    def __unicode__(self):
        return self.category

# Name forms
# For fast person lookups when parsing external webpages
# Also can be used for mapping some widespread mistaken names to correct ones
class ext_person_name(models.Model):
    person=models.ForeignKey(person)
    #name_e, name_short, name_abbrv
    form=models.CharField(max_length=255)
    name=models.CharField(max_length=255)
    class Meta:
        unique_together=('person', 'name')

# Description of an audiofile from a webpage to be parsed
# For various websites like KKRE, knowing standard format of the test describing a link,
#we can parse and compare descriptions of a recording, extracting information needed to import it
#into our database (like title, poets, composers, performers, ...)
class ext_recording_link(models.Model):
    # Recording the link is pointing at
    recording=models.ForeignKey(recording)
    # Address of a webpage the link was found at
    href=models.ForeignKey(ext_person_link)
    # Link text (usually a piece title)
    title=models.CharField(max_length=255)
    # Some text around the link which seems to be its description
    description=models.CharField(max_length=255)
    # Assuming that there can be only one link to the same recording on a webpage
    class Meta:
        unique_together=('recording', 'href')

# Names that failed to be recognized while parsing webpages
class ext_unknown_name(models.Model):
    name=models.CharField(max_length=255, unique=True)
    # Number of occurences
    #count=models.IntegerField()
    # instead of occurences counter, we will have relations to poetry/music/recordings objects
    # we will be able to calculate the number of occurences from them, show unknown names like names for existing person objects,
    # and even to show lists of pieces with same unknown name (of course, without any guarantee that it means the same person everywhere)
    poetry=models.ManyToManyField(poetry)
    music=models.ManyToManyField(music)
    recordings=models.ManyToManyField(recording)

# Extra titles for pieces which are seen under more than one title
# we don't need them, we can always get all titles as all ext_recording_link.title values of all recordings that our piece is related to
#class ext_poetry_title(models.Model):
#    title=models.CharField(max_length=255)
#    poetry=models.ForeignKey(poetry)
#    count=models.IntegerField()
#class ext_music_title(models.Model):
#    title=models.CharField(max_length=255)
#    music=models.ForeignKey(music)
#    count=models.IntegerField()

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
    pass
#    if kwargs['action']=='pre_add' or kwargs['action']=='pre_remove':
#        print('caught '+kwargs['action']+' from ')
#        print(sender)
#        old=poetry.objects.get(pk=kwargs['instance'].pk)
#        print('old:')
#        print(old.poets.all())
#        print('new:')
#        print(kwargs['instance'].poets.all())
#        for pk in kwargs['pk_set']:
#            cache.delete(template_cache_key('recordings_person', pk))

# On object change
# Poetry/music/recording: invalidate all recording lists it appears in
#   pages of all related people
# Person: invalidate person's page and all the other pages on which this person appears
#   problem: get list of all people related to given one
#   person.objects.filter(Q())

def poetry_changed(sender, instance, signal, *args, **kwargs):
    pass
#    old=poetry.objects.get(pk=instance.pk)
#    print('pre_save caught!')
#    print('old:')
#    print(old.poets.all())
#    print(old.title)
#    print('new:')
#    print(instance.poets.all())
#    print(instance.title)

# Create: not needed, because anything appears on pages only by M2M relation, which is set after creation
# Delete: not needed, if M2M is unset before deletion (?)

signals.m2m_changed.connect(poets_changed, sender=poetry.poets.through)
signals.pre_save.connect(poetry_changed, sender=poetry)

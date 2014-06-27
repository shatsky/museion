# coding=UTF-8

from django.db import models
from djangosphinx import SphinxSearch

# TODO: replace this with a custom field capable of storing year-only values as well as full dates
# https://github.com/dracos/django-date-extensions may fit
# is it database- or, at least, dumpdata/loaddata-compatible?
ApproximateDateField = models.DateField

def delete_bracketed_fragments(string):
    """Returns string stripped of bracketed fragments (used in models to return clean names/titles)"""
    import re
    return re.sub('\s\([^)]*\)', '', string)

class Person(models.Model):
    """
    Person model objects describe people, groups and unknown names
    They don't have explicit categories like 'poet' or 'composer';
    categories are determined dynamically based on references from other models like 'poetry' or 'music'
    """
    # Must write a validator to forbid "category", "_", number-only names (enough?) here
    name = models.CharField(max_length=255, unique=True)
    text = models.TextField(blank=True)
    image = models.FileField(upload_to='people', null=True)
    # individual, group or unknown
    # unknown is a special type, it means we don't have any data about this person, are unshure if all references to it mean same person
    #  or different people with same name, or even not a person at all, but just some string accidentally treated as s person name
    #  by some import script
    #  we just shouldn't forget that if we want to query for verified people we should use exclude(type='unknown')
    type = models.CharField(max_length=255)
    # gender for individual, maybe format for group
    subtype = models.CharField(max_length=255)
    # how should we use these for groups?
    birth_date = ApproximateDateField(null=True, blank=True)
    death_date = ApproximateDateField(null=True, blank=True)
    def __unicode__(self):
        return self.name
    @property
    def first_letter(self):
        """Returns the first letter (used in people catalog templates to regroup lists)"""
        return self.name[0]
    # Different name forms to use in pieces descriptions, etc.
    @property
    def name_clean(self):
        """Returns a clean name (without bracketed fragments)"""
        if self.type != 'unknown':
            return delete_bracketed_fragments(self.name)
        else:
            return self.name
    @property
    def name_short(self):
        """Returns a short name ('Name Surname')"""
        name = self.name_clean
        if self.type == 'individual': # Name Surname
            name_parts = name.split(', ')
            # Unshortable name part
            name = name_parts[0]
            # First word of the shortable part
            if len(name_parts)>1:
                name = name_parts[1].split(' ')[0] + ' ' + name # 'Name Surname'
            return name
        elif self.type == 'group' and self.subtype == 'ussrvia':
            return name.replace(u'Вокально-инструментальный ансамбль', u'ВИА')
        else: return name
    @property
    def name_abbrv(self):
        """Returns an abberviated name ('N. Surname')"""
        name = self.name_clean
        if self.type == 'individual': # N. Surname
            name_parts = name.split(', ') #split by comma
            # Unshortable name part
            name = name_parts[0]
            # First letter of the first word of the shortable part
            if len(name_parts)>1 and len(name_parts[1])>0:
                name = name_parts[1][0] + '. ' + name # 'N. Surname'
            return name
        else: return self.name_short
    @property
    def name_url(self):
        """Returns the name form to use in URLs (whitespaces replaced with underscores)"""
        return self.name.replace(" ", "_")
    def get_absolute_url(self):
        from django.core.urlresolvers import reverse
        from django.utils.http import urlquote
        return reverse('museion.views.person', args=[urlquote(self.name_url, safe='/,')])
    search = SphinxSearch(index='name')

class Poetry(models.Model):
    """
    Poetry pieces
    """
    title = models.CharField(max_length=255)
    poets = models.ManyToManyField(Person)
    text = models.TextField(blank=True)
    year = ApproximateDateField(null=True, blank=True)
    def __unicode__(self):
        return self.title
    search = SphinxSearch(index='title')
    search_text = SphinxSearch(index='text')
    # Debugging cache invalidation
    #def save(self):
    #    print('called poetry save()')
    #    old = poetry.objects.get(pk=self.pk)
    #    print('old:')
    #    print(old.title)
    #    super(poetry, self).save()
    #    print('new:')
    #    print(self.title)

class Music(models.Model):
    """
    Musical pieces (just pieces, not recordings!)
    """
    title = models.CharField(max_length=255)
    # If music has been written for the specific poetry, we can leave music.title empty, but set music.poetry pointer
    #to reference this poetry and inherit title from it
    poetry = models.ForeignKey(Poetry, null=True)
    composers = models.ManyToManyField(Person)
    year = ApproximateDateField(null=True, blank=True)
    def __unicode__(self):
        if self.poetry is not None:
            return self.poetry.title
        else:
            return self.title

class Recording(models.Model):
    """
    Recordings of pieces, performed by certain performes and (usually) associated with audiofiles
    """
    # We don't have a "piece" object with pointers to music and lyrics forming one piece together
    # Instead, we have separate poetry/music pointers in recording
    # on_delete=models.SET_NULL essential to avoid losing recordings if we wipe music or poetry records
    poetry = models.ForeignKey(Poetry, blank=True, null=True, on_delete=models.SET_NULL)
    music = models.ForeignKey(Music, blank=True, null=True, on_delete=models.SET_NULL)
    # However, we still have a title field
    # For recordings with poetry and/or music, it stores duplicated inherited title - for ordering in queries
    # There can also be pieceless recordings - namely, speeches
    # Plus, this solves the problem of storing titles for imported recordings which don't have related pieces
    #  because the import analyser failed to get poets and composers
    title = models.CharField(max_length=255, blank=True)
    performers = models.ManyToManyField(Person)
    year = ApproximateDateField(null=True, blank=True)
    # Audiofile address
    href = models.URLField(unique=True)
    # To disable/hide recordings we can't play because of copyright
    legal_status = models.CharField(max_length=255)
    def __unicode__(self):
        return self.href
    @property
    def title_piece_object(self):
        """
        Returns a piece object from which this recording derives its title
        Can be used to get its title (obviously) or id (to anchorize the title in the description of this recording, pointing it to a page
        which displays all pieces derived from this title piece with their recordings; e. g. some poetry with multiple different
        music pieces set to it, written by different composers)
        """
        if self.poetry: return self.poetry
        elif self.music:
            if self.music.poetry: return self.music.poetry
            else: return self.music
        else: return self
    @property
    def piece_id(self):
        """
        Returns a pseudo-id string, combining ids of objects that make together a piece of this recording (usually, poetry and music)
        Used in templates to regroup recordings list into pieces lists, each one containing recordings of a single piece
        """
        poetry_id = ''
        music_id = ''
        if self.poetry: poetry_id = self.poetry.id
        if self.music: music_id = self.music.id
        return '%s %s' % (str(poetry_id), str(music_id))
    def save(self, *args, **kwargs):
        # TODO: this should be re-run automatically each time related objects are modified to keep fields in sync
        self.title = self.title_piece_object.title
        super(Recording, self).save(*args, **kwargs)

class Production(models.Model):
    """
    Movies, radio plays, TV programmes and other productions
    """
    title = models.CharField(max_length=255, unique=True)
    # type: movie, radio play, TV programme, ...
    type = models.CharField(max_length=255)
    # synopsis/annotation
    text = models.TextField(blank=True)
    people = models.ManyToManyField(Person)
    year = ApproximateDateField(null=True, blank=True)
    # although we refer to Recording model here, not Music model, which is for music pieces,
    # we find Production.recordings field name too confusing, thus it's called Production.music
    music = models.ManyToManyField(Recording)
    @property
    def title_clean(self):
        """Clean title (without bracketed fragments)"""
        return delete_bracketed_fragments(self.title)

# For import from external websites
# ---------------------------------

class ExtPersonLink(models.Model):
    """
    Links to people pages from external websites
    Can be used to import content from these pages
    (functions capable of extracting content from their mirrored copies should be available in
    management/commands/_import_<website_format_string>.py for this, see management/commands/museion_import.py)
    """
    people = models.ManyToManyField(Person)
    # we can explicitly define manytomany table for this
    # to store start...end page offsets for each person
    # (kkre has many multi-person pages)
    href = models.URLField(unique=True)
    # recordings M2M via ext_recording_link
    # funny thing is that while I described ext_recording_link connecting these tables times ago,
    # the idea of putting M2M here came to me only after I've faced a need to select recordings by referencing ext_person_link
    recordings = models.ManyToManyField(Recording, through='ExtRecordingLink')
    # Known formats
    FORMAT_CHOICES = (('kkre', 'kkre "title (composers - poets) performers" format'),)
    format = models.CharField(max_length=255, choices=FORMAT_CHOICES, blank=True)
    def __unicode__(self):
        return '[%s] %s' % (self.format, self.href)

class ExtPersonCategory(models.Model):
    """
    Categories like "poet", "composer", "performer"
    Although we categorise people using actual information, e. g,
    if the person has any poetry associated via poetry.poets, it will be shown in "poets" category,
    we may need to supply categories explicitly for new people who have no related content yet
    to import information from external website, e. g, if there is an external website page about some person
    with a recordings list on it, and there is a recording in the list that has "performer" information omitted,
    and from this table we know that this person is known as a performer,
    then we can make a safe assumption that this person is a performer for this recording
    """
    people = models.ManyToManyField(Person)
    category = models.CharField(max_length=255, unique=True)
    def __unicode__(self):
        return self.category

class ExtPersonName(models.Model):
    """
    Basic name forms given by models.person functions (name_short, name_abbrv) for fast person lookups when parsing external webpages
    Also for name forms that are used in indexes of websites we that have import modules for (kkre, sssrviapesni)
    """
    person = models.ForeignKey(Person)
    #name_e, name_short, name_abbrv
    form = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    
    class Meta:
        unique_together = ('person', 'form')

class ExtRecordingLink(models.Model):
    """
    Description of an audiofile from a webpage to be parsed
    For various websites like KKRE, knowing standard format of the test describing a link,
    we can parse and compare descriptions of a recording, extracting information needed to import it
    into our database (like title, poets, composers, performers, ...)
    """
    # Recording the link is pointing at
    recording = models.ForeignKey(Recording)
    # Address of a webpage the link was found at
    href = models.ForeignKey(ExtPersonLink)
    # Link text (usually a piece title)
    title = models.CharField(max_length=255)
    # Some text around the link which seems to be its description
    description = models.CharField(max_length=255)
    # Assuming that there can be only one link to the same recording on a webpage
    class Meta:
        unique_together = ('recording', 'href')

# Journaling
# -----------------
import visitors_journal.models
class Journal(visitors_journal.models.Journal):
    """Unified journal"""
    EVENT_CHOICES = (
        ('v', 'page view'),
        ('s', 'search query'),
        ('p', 'recording playback'),
    )
    event = models.CharField(max_length=1, choices=EVENT_CHOICES)
    # Page view fields
    view_url = models.CharField(max_length=255)
    # Search query fields
    search_query = models.CharField(max_length=255)
    MODE_CHOICES = (
        ('n', 'in names'),
        ('t', 'in titles'),
        ('p', 'in poetry'),
    )
    search_mode = models.CharField(max_length=1, choices=MODE_CHOICES)
    # Recording playback fields
    playback_recording = models.ForeignKey(Recording, blank=True, null=True)

# Event-driven cache invalidation
# -------------------------------

from django.db.models import signals
from django.core.cache import cache
from django.utils.http import urlquote
import hashlib

# This should be in Django API
def template_cache_key(fragment_name='', *args):
    """Cache key for template fragment"""
    return 'template.cache.%s.%s' % (fragment_name, hashlib.md5(u':'.join([urlquote(arg) for arg in args])).hexdigest())

# On M2M change (list of people related to certain object has been modified)
# Poetry/music/recording: invalidate all recording lists it appears in
#   all people which are in both old and new M2M lists;
#   invalidate people lists which depend on count

def poets_changed(sender, **kwargs):
    pass
#    if kwargs['action'] == 'pre_add' or kwargs['action'] == 'pre_remove':
#        print('caught ' + kwargs['action'] + ' from ')
#        print(sender)
#        old = Poetry.objects.get(pk=kwargs['instance'].pk)
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
#   Person.objects.filter(Q())

def poetry_changed(sender, instance, signal, *args, **kwargs):
    pass
#    old = Poetry.objects.get(pk=instance.pk)
#    print('pre_save caught!')
#    print('old:')
#    print(old.poets.all())
#    print(old.title)
#    print('new:')
#    print(instance.poets.all())
#    print(instance.title)

# Create: not needed, because anything appears on pages only by M2M relation, which is set after creation
# Delete: not needed, if M2M is unset before deletion (?)

signals.m2m_changed.connect(poets_changed, sender=Poetry.poets.through)
signals.pre_save.connect(poetry_changed, sender=Poetry)

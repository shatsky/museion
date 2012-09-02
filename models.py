from django.db import models
from djangosphinx import SphinxSearch

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

class person(models.Model):
    name=models.CharField(max_length=255, unique=True)
    name_e=models.CharField(max_length=255)
    name_short=models.CharField(max_length=255)
    name_abbrv=models.CharField(max_length=255)
    type=models.CharField(max_length=255)
    category=models.ManyToManyField(kkre_person_category)
    # we can explicitly define manytomany table for this
    # to store start...end page offsets for each person
    # (kkre has many multi-person pages)
    links=models.ManyToManyField(ext_person_link)
    def __unicode__(self):
        return self.name
    def first_letter(self):
        try: return self.name[0]
        except: return ''
    #def name_abbrv(self):
    #    ?

class poetry(models.Model):
    title=models.CharField(max_length=255)
    poets=models.ManyToManyField(person)
    def __unicode__(self):
        return self.title
    search = SphinxSearch(
        index='title'
    )

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

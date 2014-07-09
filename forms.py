# coding=UTF-8

from django import forms
from museion import models
from django.utils import simplejson
from django.utils.html import mark_safe

# Poetry/music/recording forms
# By default, M2M authors/performers fields are represented with multiselect (which submits multiple instances of the variable)
# We want a text input instead (jquery tokeninput, which submits a string of comma-separated ids in one variable)
# We also need a validator to check several things: i. e. group cannot be an author

class M2MJSONInput(forms.HiddenInput):
    def render(self, *args, **kwargs):
        return mark_safe('<div class="m2m-json">'+super(M2MJSONInput, self).render(*args, **kwargs)+"""
<p class="m2m-list"></p>
<input type="text" class="m2m-user-input">
        """+'</div>')

# By default, M2M is represented with ModelMultipleChoiceField, widget=SelectMultiple
# Simply replacing widget with TextInput causes validation error, even if SelectMultiple behaviour is simulated from the client side
# This class has been copypasted from stackoverflow discussion, and it does, suprisingly, make things work
# TODO: figure out how does it actually work, find a more elegant solution if possible
# http://stackoverflow.com/questions/4707192/django-how-to-build-a-custom-form-widget
# I thought the problem is that "input value to python structure" logic was somwhere in the widget, not in the field, which
# expects TextInput to return python array instead of the string; but the link above suggests it's actually in the field
class ModelM2MJSONField(forms.ModelMultipleChoiceField):
    widget = M2MJSONInput
    # clean() is responsible for conversion of the given input into a list of values
    # we parse the string as JSON array, expecting it to be a list of pks
    def clean(self, value):
        if value is not None:
            value = simplejson.loads(value)
        return super(ModelM2MJSONField, self).clean(value)

# Customised form class with save() method which creates new objects for string vars from ModelM2MJSONField transparently
# model field is currently hardcoded as 'name' (strings are treated as values for 'name' fields of M2M-related model objects)
class MuseionForm(forms.ModelForm):
    def save(self, *args, **kwargs):
        # form saving should be an atomic operation:
        # we shouldn't create people objects for the string names, if is_valid() fails
        # we shouldn't save() if we can't create some people objects (and we must show informative error message)
        # first, we have to make data writable
        self.data=self.data.copy()
        # now we can parse M2MJSONFields, create objects for strings and replace strings with objects pks
        m2mjson_fields={}
        # list affected fields
        for field_name in self.Meta.fields:
            if self.base_fields[field_name].__class__.__name__ == 'ModelM2MJSONField':
                m2mjson_fields[field_name]={'objects':[]}
                m2mjson_fields[field_name]['data']=simplejson.loads(self.data[field_name])
                for idx in range(len(m2mjson_fields[field_name]['data'])):
                    # delete string names from the list, simltaneosely instantiating unknown people objects for them
                    if isinstance(m2mjson_fields[field_name]['data'][idx], unicode):
                        name=m2mjson_fields[field_name]['data'].pop(idx)
                        try: m2mjson_fields[field_name]['objects'].append(getattr(self.Meta.model, field_name).field.related.parent_model.objects.get(name=name))
                        except models.Person.DoesNotExist: m2mjson_fields[field_name]['objects'].append(getattr(self.Meta.model, field_name).field.related.parent_model(name=name, type='unknown'))
                    # we do not check for other types, it's up to form.is_valid() to ensure that everything else is valid pks
                # replace field data with filtered array wich contains only pks
                self.data[field_name] = simplejson.dumps(m2mjson_fields[field_name]['data'])
        # if everything went OK, validate form
        # we cannot save yet, because we have to add ids of newly created objects
        # we have to run is_valid() on a temporary form copy, because it's results, including cleaned_data, cannot be updated after further data changes (why?)
        if not self.__class__(self.data, instance=self.instance).is_valid(): raise NameError('FormIsNotValid')
        # if everything is still OK, save instantiated objects and add their pks to field
        for field_name in m2mjson_fields:
            for m2m_object in m2mjson_fields[field_name]['objects']:
                if m2m_object.id is None:
                    if 'commit' not in kwargs.keys() or kwargs['commit'] is True: m2m_object.save()
                    # if object creation failed, insert name back into field array (this will prevent form.save())
                    if m2m_object.id is None: m2mjson_fields[field_name]['data'].append(m2m_object.name)
                else: m2mjson_fields[field_name]['data'].append(m2m_object.id)
            self.data[field_name] = simplejson.dumps(m2mjson_fields[field_name]['data'])
        # finally
        return super(MuseionForm, self).save(*args, **kwargs)

# Individuals and groups are stored in a single table
# There are properties specific to only one of these types, e. g. gender for individual
# We need it to be represented with select input, only visible for individuals
class Person(MuseionForm):
    class Meta:
        model = models.Person
        fields = ['name', 'subtype', 'birth_date', 'death_date', 'image', 'text']

class Poetry(MuseionForm):
    poets = ModelM2MJSONField(queryset=models.Person.objects.all(), label=u'Авторы')
    class Meta:
        model = models.Poetry
        fields = ['title', 'poets', 'year', 'text']
        help_texts = {
            'poets':u'Используйте текстовое поле для поиска людей',
        }

# Music can either inherit title from poetry (via poetry key, while title field is empty)
# or have ins own (in title field, with poetry key set to NULL)
# This logic is not fully controlled from the model, so we must have a pair of radiobuttuns to switch between two related inputs
# and a custom validator
class Music(MuseionForm):
    composers = ModelM2MJSONField(queryset=models.Person.objects.all(), label='Композиторы')
    class Meta:
        model = models.Music
        fields = ['poetry', 'title', 'composers', 'year']
        widgets = {
            'poetry':forms.widgets.TextInput(),
        }

class Recording(MuseionForm):
    performers = ModelM2MJSONField(queryset=models.Person.objects.all(), label='Исполнители')
    class Meta:
        model = models.Recording
        fields = ['music', 'poetry', 'performers', 'year', 'href']
        widgets = {
            'poetry':forms.widgets.TextInput(),
            'music':forms.widgets.TextInput(),
        }

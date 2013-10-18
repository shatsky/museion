# coding=UTF-8

from django import forms
from museion import models

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
class ModelCommaSeparatedChoiceField(forms.ModelMultipleChoiceField):
    widget = forms.TextInput
    def clean(self, value):
        if value is not None:
            value = [item.strip() for item in value.split(",")]  # remove padding
        return super(ModelCommaSeparatedChoiceField, self).clean(value)

# Individuals and groups are stored in a single table
# There are properties specific to only one of these types, e. g. gender for individual
# We need it to be represented with select input, only visible for individuals
class Person(forms.ModelForm):
    class Meta:
        model = models.Person
        fields = ['name', 'subtype', 'birth_date', 'death_date', 'image', 'text']

class Poetry(forms.ModelForm):
    poets = ModelCommaSeparatedChoiceField(queryset=models.Person.objects.filter())
    class Meta:
        model = models.Poetry
        fields = ['title', 'poets', 'year', 'text']
        #widgets = {
        #    'poets':forms.widgets.TextInput(),
        #}
        # TODO: make labels work
        labels = {
            'title':u'Название',
            'poets':u'Поэты',
            'text':u'Текст',
        }

# Music can either inherit title from poetry (via poetry key, while title field is empty)
# or have ins own (in title field, with poetry key set to NULL)
# This logic is not fully controlled from the model, so we must have a pair of radiobuttuns to switch between two related inputs
# and a custom validator
class Music(forms.ModelForm):
    class Meta:
        model = models.Music
        fields = ['poetry', 'title', 'composers', 'year']
        widgets = {
            'poetry':forms.widgets.TextInput(),
            'composers':forms.widgets.TextInput(),
        }

class Recording(forms.ModelForm):
    class Meta:
        model = models.Recording
        fields = ['music', 'poetry', 'performers', 'year', 'href']
        widgets = {
            'poetry':forms.widgets.TextInput(),
            'music':forms.widgets.TextInput(),
            'performers':forms.widgets.TextInput(),
        }

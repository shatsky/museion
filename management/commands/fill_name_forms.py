#!/usr/bin/python
# coding=UTF-8

from museion import models
from _common import *

def people_fill_name_forms(people=None):
    for person in (models.person.objects.all() if people is None else people):
        print(person.name)
        for form in ['short', 'abbrv']:
            name = str_insens(getattr(person, 'name_'+form)())
            print(form + ': ' + name)
            name_form, created = models.ext_person_name.objects.get_or_create(person=person, form=form, defaults={'name':name})
            if not created and name_form.name != name:
                name_form.name = name
                name_form.save()

from django.core.management.base import BaseCommand
class Command(BaseCommand):
    def handle(self, *args, **options):
        if len(args) > 0:
            print(args[0])
            people_fill_name_forms(models.person.objects.filter(name=args[0]))
        else:
            people_fill_name_forms()


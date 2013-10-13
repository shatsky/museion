#!/usr/bin/python
# coding=UTF-8

from museion import models

from django.core.management.base import BaseCommand
class Command(BaseCommand):
    def handle(self, *args, **options):
        for category in ['poet', 'composer', 'performer']:
            models.ext_person_category.objects.get_or_create(category=category)

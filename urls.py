from django.conf.urls.defaults import patterns, include, url

from views import *

urlpatterns = patterns('djmuslib.views',
    (r'^people/category/(.+)$', 'people'),
    (r'^people/name/(.+)$', 'person'),
    (r'^poetry/(.+)$', 'poetry_text'),
    (r'^search/$', 'search_title'),
    (r'^accounts/login$', 'login'),
    (r'^accounts/logout$', 'logout'),
    (r'^refresh$', 'refresh'),
    (r'^util/tokeninput/prepopulate/person$', 'prepopulate_person'),
    (r'^util/tokeninput/autocomplete/person$', 'autocomplete_person'),
    (r'^edit/person/(?P<id>\d+)$', 'edit_person'),
    (r'^edit/poetry/(?P<id>\d+)$', 'edit_poetry'),
    (r'^edit/music/(?P<id>\d+)$', 'edit_music'),
    (r'^edit/recording/(?P<id>\d+)$', 'edit_recording'),
    (r'^journal.*$', 'journal'),
    (r'^ajax_test.*$', 'ajax_test'),
    (r'^$', 'main'),
    (r'', 'default'),
)

from django.conf.urls.defaults import patterns, include, url

from views import *

urlpatterns = patterns('djmuslib.views',
    (r'^people/categories/(.+)$', 'people'),
    (r'^people/(.+)$', 'person'),
    (r'^search/$', 'search'),
    (r'^user/login$', 'login'),
    (r'^user/logout$', 'logout'),
    (r'^edit/person/(?P<id>\d+)/$', 'edit_person'),
    (r'^journal.*$', 'journal'),
    (r'^ajax_test.*$', 'ajax_test'),
    (r'', 'default'),
)

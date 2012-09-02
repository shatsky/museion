from django.conf.urls.defaults import patterns, include, url

from views import *

urlpatterns = patterns('djmuslib.views',
    ('^people/(\d+)$', 'person'),
    ('^people/(.+)$', 'people'),
    ('^search/$', 'search'),
)

from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

from views import *

urlpatterns = patterns('music.views',
    ('^people/(\d+)$', 'person'),
    ('^people/(.+)$', 'people'),
    ('^search/$', 'search'),
)

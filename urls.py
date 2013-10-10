from django.conf.urls.defaults import patterns
from django.conf.urls.defaults import url
from django.conf import settings

urlpatterns = patterns('djmuslib.views',
    url(r'^people/category/(.+)$', 'people'),
    url(r'^people/name/(.+)$', 'person'),
    url(r'^poetry/(.+)$', 'poetry_text'),
    url(r'^search/$', 'search_title'),
    url(r'^'+settings.LOGIN_URL[1:]+'$', 'login'),
    url(r'^'+settings.LOGOUT_URL[1:]+'$', 'logout'),
    url(r'^refresh$', 'refresh'),
    url(r'^util/tokeninput/prepopulate/person$', 'prepopulate_person'),
    url(r'^util/tokeninput/autocomplete/person$', 'autocomplete_person'),
    
    url(r'^edit/person/$', 'edit_person'),
    url(r'^edit/person/(?P<id>\d+)$', 'edit_person'),
    url(r'^edit/poetry/$', 'edit_poetry'),
    url(r'^edit/poetry/(?P<id>\d+)$', 'edit_poetry'),
    url(r'^edit/music/$', 'edit_music'),
    url(r'^edit/music/(?P<id>\d+)$', 'edit_music'),
    url(r'^edit/recording/$', 'edit_recording'),
    url(r'^edit/recording/(?P<id>\d+)$', 'edit_recording'),
    
    url(r'^journal.*$', 'journal'),
    url(r'^top.*$', 'top_recordings'),
    url(r'^$', 'main'),
    #(r'', 'default'),
)

if settings.DEBUG:
    from django.conf.urls.static import static
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

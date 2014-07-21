from django.conf.urls import patterns, url
from django.conf import settings

urlpatterns = patterns('museion.views',
    url(r'^people/category/(.+)$', 'people'),
    url(r'^people/name/(.*)$', 'person'),
    url(r'^poetry/text/(.+)$', 'poetry_text'),
    url(r'^search/title/(.+)$', 'search_title'),
    url(r'^search/text/(.+)$', 'search_text'),
    url(r'^search/name/(.+)$', 'search_name'),
    url(r'^'+settings.LOGIN_URL[1:]+'$', 'login'),
    url(r'^'+settings.LOGOUT_URL[1:]+'$', 'logout'),
    url(r'^refresh$', 'refresh'),
    url(r'^util/people_prepopulate$', 'prepopulate_person'),
    url(r'^util/people_suggestions$', 'autocomplete_person'),
    url(r'^util/piece_info$', 'piece_info'),
    url(r'^util/piece_suggestions$', 'piece_suggestions'),
    
    url(r'^people/edit/$', 'edit_person'),
    url(r'^people/edit/(?P<id>\d+)$', 'edit_person'),
    url(r'^poetry/edit/$', 'edit_poetry'),
    url(r'^poetry/edit/(?P<id>\d+)$', 'edit_poetry'),
    url(r'^music/edit/$', 'edit_music'),
    url(r'^music/edit/(?P<id>\d+)$', 'edit_music'),
    url(r'^recording/edit/$', 'edit_recording'),
    url(r'^recording/edit/(?P<id>\d+)$', 'edit_recording'),
    
    url(r'^journal.*$', 'journal'),
    url(r'^top.*$', 'top_recordings'),
    url(r'^$', 'main'),
    #(r'', 'default'),
)

if settings.DEBUG:
    from django.conf.urls.static import static
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

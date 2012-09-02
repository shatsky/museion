#!/usr/bin/python
# coding=UTF-8

# current problems
# name fixes and case handling

from lxml.html import parse
from pprint import pprint
from music.models import *

# strange
#pprint(u'\u043f\u0435\u0432\u0438\u0446\u044b \u043d\u0430 "');
#pprint(u'певцы на "');

# function downloads or updates file from remote address
# and returns local path (which is just the address without the protocol handler)
# it does not write a file if server returns an error
# it returns false if there is no file
import pycurl
import os
basedir='./mirror/'
work_offline=True
def fetch(addr):
    print('fetching '+addr)
    if addr.endswith('/'): addr+='index.htm'
    path=basedir+addr.replace('http://', '')
    if work_offline==True:
        if os.path.exists(path):
            #print('offline')
            return path
        else:
            return False
    else:
        download=False
        curl=pycurl.Curl()
        curl.setopt(pycurl.URL, addr.encode('ascii'))
        curl.setopt(pycurl.HEADER, True)
        curl.setopt(pycurl.NOBODY, True)
        curl.setopt(pycurl.OPT_FILETIME, True)
        curl.perform()
        remote_timestamp=curl.getinfo(pycurl.INFO_FILETIME)
        curl.reset()
        if os.path.exists(path): # if local file exists - compare mtime with remote
            if os.stat(path).st_mtime<remote_timestamp: # file needs to be updated
                download=True
            else: # file is up to date
                return path
        else: # file needs to be downloaded anyway
            download=True
        if download==True:
            curl.setopt(pycurl.URL, addr.encode('ascii'))
            if not os.path.exists(os.path.dirname(path)): os.makedirs(os.path.dirname(path))
            file = open(path, "wb")
            curl.setopt(pycurl.WRITEDATA, file)
            curl.perform()
            curl.close()
            file.close()
            if False: # handle download errors
                if(os.path.exists(path)): # if download failed - still check if there is a local file, if yes - return path
                    return path # this is WRONG because we there always IS a local file after fopen() call
                else: # otherwise, return false
                    return False
            else: # if download succeeded - preserve timestamp
                print('applying timestamp')
                pprint(remote_timestamp)
                pprint(path)
                os.utime(path, tuple([remote_timestamp, remote_timestamp]))
            return path

# function to get inner text of a DOM node
def dom_node_text(node):
    text=''
    if node.hasChildNodes():
        # get all children
        node=node.firstChild
        while node!=None:
            text+=dom_node_text(node)
            node=node.nextSibling
    else:
        if node.nodeType==node.TEXT_NODE:
            # return text
            text=node.nodeValue
    return text

# function to get inner text of a DOM nodes chain following a given one until one of terminating tags occurs
class _dom_node_text_term_result:
    text=''
    abort=False

def dom_node_text_term(node):
    result=_dom_node_text_term_result
    result.text=''
    result.abort=False
    try: _dom_node_text_term(node.nextSibling, result)
    except: pass
    return result.text

def _dom_node_text_term(node, result):
    # if we have already met a terminating tag
    if result.abort!=True:
        while result.abort!=True and node!=None:
            # if we meet a terminating tag here
            if node.nodeType!=node.TEXT_NODE and node.nodeName!='b' and node.nodeName!='i':
                result.abort=True
                return
            elif node.hasChildNodes():
                _dom_node_text_term(node.firstChild, result)
            elif node.nodeType==node.TEXT_NODE:
                result.text+=node.nodeValue
            node=node.nextSibling
    return

import re

#########
#STAGE 1#
#########
# read people lists, fill person and kkre_person_link tables

#person.objects.all().delete() doesn't work well with SQLite (number of variables in the request is limited)
#from django.db import connection
#cursor = connection.cursor()
#cursor.execute('DELETE FROM "{0}"'.format(kkre_person_link._meta.db_table))
#cursor.execute('DELETE FROM "{0}"'.format(person._meta.db_table))

# create categories
for category in ['poet', 'composer', 'performer']:
    kkre_person_category.objects.get_or_create(category=category)

lists={
'composers':'http://kkre-1.narod.ru/komp.htm',
'poets':'http://kkre-1.narod.ru/poet.htm',
'singers_female':'http://kkre-1.narod.ru/pevi.htm',
'singers_male':'http://kkre-1.narod.ru/pevc.htm',
'groups':'http://krapp-sa.narod.ru/',
}
lists={}
for list, address in lists.iteritems():
    doc=parse(fetch(address)).getroot()
    for link in doc.cssselect('a'):
        if link.get('href')=='http://kkre-1.narod.ru/': continue
        name=link.text_content()
        name=re.sub('\s+', ' ', name) # multiple whitespaces
        name=name.strip() # trim
        
        if len(name)==1:
            if list=='singers_female': name=u'\u043f\u0435\u0432\u0438\u0446\u044b \u043d\u0430 "'+name+'"'
            elif list=='singers_male': name=u'\u043f\u0435\u0432\u0446\u044b \u043d\u0430 "'+name+'"'
            #if list=='singers_female': name=u'певицы на "'+name+'"'
            #elif list=='singers_male': name=u'певцы на "'+name+'"'
        
        # strange - without encode('utf8') django_shell<this_script works, but django_shell<this_script>output_file fails
        print '%s: %s' % (name.encode('utf8'), link.get('href'))
        
        # extra details 
        # category
        if list=='poets':
            category='poet'
        elif list=='composers':
            category='composer'
        elif list in ['singers_male', 'singers_female', 'groups']:
            category='performer'
        
        # type (gender)
        # third name endings: 'вич', 'мич', 'ьич', 'оглы' - male, 'вна', 'чна' - female
        if category=='singers_male' or name[-3:] in [u'\u0432\u0438\u0447', u'\u043c\u0438\u0447', u'\u044c\u0438\u0447'] or name[-4:]==u'\u043e\u0433\u043b\u044b':
            type='male'
        elif category=='singers_female' or name[-3:] in [u'\u0432\u043d\u0430', u'\u0447\u043d\u0430']:
            type='female'
        elif category=='groups':
            type='group'
        
        # name forms
        name_e=name.replace(u'\u0451', u'\u0435') # for 'ё'/'е' insensetive comparison
        name_e=re.sub('\s\([^)]*\)', '', name_e) # throw out parts in brackets
        # this only has sense for individuals
        name_short=name_abbrv=''
        if not list=='groups':
            name_part=name_e.split(' ')
            if len(name_part)>=1:
                name_short=name_abbrv=name_part[0]
                if len(name_part)>=2:
                    name_short=name_part[1]+' '+name_short # 'Name Surname'
                    name_abbrv=name_part[1][0]+'. '+name_abbrv # 'N. Surname'
        p,created=person.objects.get_or_create(name=name, defaults={'name_e':name_e, 'name_short':name_short, 'name_abbrv':name_abbrv, 'type':type})
        # if a new category - add and save
        p.category.add(kkre_person_category.objects.filter(category=category)[0].id)
        #except: pass # already set
        #else: p.save()
        try: kkre_person_link.objects.create(href=link.get('href'), person=p)
        except: pass
        


# some fixes
# here is a problem: if we re-run stage 1 after fixes are applied, wrong records will be added again, as unique constraint will not work after name/link change
# solved via delete() on exception

for l in ext_person_link.objects.filter(href='http://kkre-2.narod.ru/gladkov.htm/'):
    l.href='http://kkre-2.narod.ru/gladkov.htm'
    try: l.save()
    except: l.delete()

for l in ext_person_link.objects.filter(href='http://kkre-48.narod.ru/chuev.htm/'):
    l.href='http://kkre-48.narod.ru/chuev.htm'
    try: l.save()
    except: l.delete()

for p in person.objects.filter(name=u'\u0411\u044e\u043b\u044c-\u0431\u044e\u043b\u044c \u043e\u0433\u043b\u044b \u041f\u043e\u043b\u0430\u0434'): # Полад Бюль-Бюль Оглы
    p.name=u'\u0411\u044e\u043b\u044c-\u0411\u044e\u043b\u044c\u00a0\u041e\u0433\u043b\u044b \u041f\u043e\u043b\u0430\u0434' # non-breaking space
    p.name_e=p.name
    p.name_short=u'\u041f\u043e\u043b\u0430\u0434 \u0411\u044e\u043b\u044c-\u0431\u044e\u043b\u044c \u043e\u0433\u043b\u044b'
    p.name_abbrv=u'\u041f. \u0411\u044e\u043b\u044c-\u0411\u044e\u043b\u044c \u041e\u0433\u043b\u044b'
    try: p.save()
    except: p.delete()

for p in person.objects.filter(name=u'\u041b\u0430\u0437\u0430\u0440\u0435\u0432-\u041c\u0438\u043b\u044c\u0434\u043e\u043d \u0412\u043b\u0430\u0434\u0438\u043c\u0438\u0440 \u042f\u043a\u043e\u0432\u043b\u0435\u0432\u0438\u0447'): # Лазарев-Мильдон Владимир Яковлевич
    p.name=u'\u041b\u0430\u0437\u0430\u0440\u0435\u0432 (\u041b\u0430\u0437\u0430\u0440\u0435\u0432-\u041c\u0438\u043b\u044c\u0434\u043e\u043d) \u0412\u043b\u0430\u0434\u0438\u043c\u0438\u0440 \u042f\u043a\u043e\u0432\u043b\u0435\u0432\u0438\u0447'
    p.name_e=u'\u041b\u0430\u0437\u0430\u0440\u0435\u0432 \u0412\u043b\u0430\u0434\u0438\u043c\u0438\u0440 \u042f\u043a\u043e\u0432\u043b\u0435\u0432\u0438\u0447'
    p.name_short=u'\u0412\u043b\u0430\u0434\u0438\u043c\u0438\u0440 \u041b\u0430\u0437\u0430\u0440\u0435\u0432'
    p.name_abbrv=u'\u0412. \u041b\u0430\u0437\u0430\u0440\u0435\u0432'
    try: p.save()
    except: p.delete()


#########
#STAGE 2#
#########
# search for audio recordings on people pages, export links descriptions to kkre_recording_link table
from xml.dom.pulldom import SAX2DOM
import lxml.sax
for l in []:
#for l in ext_person_link.objects.filter(format='kkre'):
    print(l.href)
    # I want to use JS-like DOM API, but I also need a good parser to handle messy HTML
    # lxml parser and xml.dom? Seems to work...
    doc=SAX2DOM()
    #lxml.sax.saxify(parse(fetch(l.href)).getroot(), doc)
    lxml.sax.saxify(lxml.etree.parse(fetch(l.href), lxml.etree.HTMLParser(encoding='CP1251')).getroot(), doc)
    doc=doc.document
    for link in doc.getElementsByTagName('a'):
        href=link.getAttribute('href')
        # filter audiofiles
        # if not href[-4:] in ['.mp3', '.ogg', '.wma', '.wav', '.vqf']
        if not link.getAttribute('href').endswith('.mp3'):
            continue
        title=dom_node_text(link).strip()
        description=dom_node_text_term(link).strip()
        print '%s: "%s" %s' % (href, title.encode('utf8'), description.encode('utf8'))
        r,created=recording.objects.get_or_create(href=href)
        try: kkre_recording_link.objects.create(recording=r, href=l, title=title, description=description)
        except: pass
    

#########
#STAGE 3#
#########
# analyse collected descriptions of every recording, try to guess its authors/performers/title, verify, export to poetry/music tables

# load translation tables for name mistakes correction and case transformation
names_unknown={}
for line in open('./kkre_names_unknown').read().splitlines():
    line=unicode(line, 'utf8')
    name=line.split(':')
    if len(name)==2:
        names_unknown[name[1]]=name[0]

names_ins={}
for line in open('./kkre_names_cases').read().splitlines():
    line=unicode(line, 'utf8')
    name=line.split(';')
    if len(name)==2:
        names_ins[name[1]]=name[0]

from django.db.models import Q
for r in recording.objects.filter(music=None, poetry=None):
    print(r.href.encode('utf8'))
    flags={}
    flags['no_failed_names']=True
    results=[]
    for l in kkre_recording_link.objects.filter(recording=r):
        # we need associated people, their categories and names (for debug output)
        result_tmp={'self':[], 'poet':[], 'composer':[], 'performer':[]}
        self=person.objects.filter(links=l.href)
        message=''
        # because we can have multiple people per reference page, this is a bit complicated
        # we will introduce two logical arrays
        self_any={'poet':False, 'composer':False, 'performer':False} # True, if any of assoc people are in category
        self_all={'poet':True, 'composer':True, 'performer':True} # True, if all assoc people are in category
        for p in self:
            result_tmp['self'].append(p)
            for category in ['poet', 'composer', 'performer']:
                if not p.category.filter(category=category):
                    self_all[category]=False
                else:
                    self_any[category]=True
            message+='['+p.name+']'
        message+=' '+l.title+' '+l.description
        # split description into authors/performers substrings
        # what about newlines in descriptions? looks like database drops them
        # this code is UGLY
        performers=authors=''
        bracketed=re.finditer('\([^)]*\)', l.description)
        try: authors=bracketed.next()
        except: # 0 matches
            # whole string is performers
            performers=l.description
            pass
        else: # >=1 match
            # cut match from description
            if authors.start()>0: performers+=l.description[:authors.start()-1]
            if authors.end()<len(l.description): performers+=l.description[authors.end():]
            authors=authors.group(0)[1:-1]
        try: bracketed.next()
        except: # 1 match
            # OK
            pass
        else: # >1 matches
            # parse error
            print(message.encode('utf8')+' => parse error')
            continue
        # check both strings for '('/')', if any - parse error
        # split authors into composers/poets
        composers=poets=''
        authors=authors.split(' - ')
        if len(authors)==2: # "<composers> - <poets>"
            composers=authors[0]
            poets=authors[1]
            authors=''
        elif len(authors)==1: # "<composers>" or "<poets>" ?
            # if self is a poet, but not a composer - composers
            if self_any['poet']==True and self_any['composer']==False:
                composers=authors[0]
                authors=''
                for p in self:
                    if p.category.filter(category='poet'):
                        result_tmp['poet'].append(p)
            # if self is a composer, but not a poet - poets
            elif self_any['composer']==True and self_any['poet']==False:
                poets=authors[0]
                authors=''
                for p in self:
                    if p.category.filter(category='composer'):
                        result_tmp['composer'].append(p)
            else: # ?
                print(message.encode('utf8')+' => parse error')
                continue
        else: # parse error
            print(message.encode('utf8')+' => parse error')
            continue
        # if empty performers list and self is a performer
        if performers.strip()=='':
            for p in self:
                if p.category.filter(category='performer'):
                    result_tmp['performer'].append(p)
        # iterate lists
        lists={
        'poet':poets,
        'composer':composers,
        'performer':performers,
        }
        for category, list in lists.iteritems():
            list=list.strip()
            # replace different dividers by ';'
            # there are some exceptions
            # ',' inside "": 'ВИА "Лейся, песня"', ...
            # '/' in 'к/ф', 'п/у', 'п/п', ...
            # ' и ' in 'ТВ и Р', ...
            list=list.replace(',', ';')
            list=list.replace('/', ';')
            list=list.replace(u' \u0438 ', ';')
            # 'with ...'
            # if list begins with these words, self is omitted and others are in instrumental case
            ins_case=False
            for prefix in [u'\u0441 ', u'c ', u'\u0441\u043e ', u'\u0432 \u0434\u0443\u044d\u0442\u0435 \u0441']:
                if list.startswith(prefix):
                    ins_case=True
                    for p in self:
                        if p.category.filter(category=category):
                            result_tmp[category].append(p)
                    list=list[len(prefix):]
                    break
            # split list by dividers into names, iterate names
            list=list.split(';')
            for name in list:
                name=name.strip()
                # empty list will produce one empty name, but empty name from non-empty list means something is wrong with format
                if name=='': continue
                # 'сол. '
                #if name.startswith(u'\u0441\u043e\u043b. '): pass
                # instrumental case
                if ins_case:
                    try: name=names_ins[name]
                    except: pass
                name=re.sub('\.\s*', '. ', name)
                name=name.replace(u'\u0451', u'\u0435') # ё/е insensetive
                # is name comparison case-insensetive?
                # look up the name in people table
                p=person.objects.filter(Q(name__iexact=name)|Q(name_e__iexact=name)|Q(name_short__iexact=name)|Q(name_abbrv__iexact=name))
                if len(p)==1: # one match
                    result_tmp[category].append(p[0])
                elif len(p)>1: # multiple matches
                    # if only one of matching people is in current category - take him, otherwise - ambigious name
                    p=p.filter(category__in=[kkre_person_category.objects.get(category=category)])
                    if len(p)==1:
                        result_tmp[category].append(p[0])
                    else:
                        flags['no_failed_names']=False
                        print('ambigious name: '+name.encode('utf8'))
                else: # no matches
                    # look in the corrections array
                    try: name=names_unknown[name]
                    except: pass
                    p=person.objects.filter(Q(name__iexact=name)|Q(name_e__iexact=name)|Q(name_short__iexact=name)|Q(name_abbrv__iexact=name))
                    if len(p)==1:
                        result_tmp[category].append(p[0])
                    else:
                        print('unknown name: '+name.encode('utf8'))
                        flags['no_failed_names']=False
            # this is WEIRD solution
            result_num=[]
            for p in result_tmp[category]:
                result_num.append(p.id)
            result_num.sort()
            result_tmp[category]=[]
            for p in result_num:
                result_tmp[category].append(person.objects.get(id=p))
        # debug output
        message+=' => ( '
        for p in result_tmp['composer']: message+=str(p.id)+' '
        message+='- '
        for p in result_tmp['poet']: message+=str(p.id)+' '
        message+=') '
        for p in result_tmp['performer']: message+=str(p.id)+' '
        print(message.encode('utf8'))
        result_tmp['title']=l.title
        results.append(result_tmp)
    # verify and create poetry/music records
    #pprint(result)
    # results match
    # we must probably deduplicate and sort lists
    # only has sense if we have multiple results
    flags['results_match']=False
    flags['title_match']=False
    if len(results)>1:
        flags['results_match']=True
        flags['title_match']=True
        for result in results:
            for category in ['poet', 'composer', 'performer']:
                if result[category]!=results[0][category]:
                    flags['results_match']=False
                    break
            if result['title']!=results[0]['title']:
                flags['title_match']=False
    # cross-verification
    # enshure that each person in 'poet', 'composers', 'performer' lists is present in any 'self' list
    flags['cross_verified']=False
    # only has sense if results match or just one result
    if flags['results_match'] or len(results)==1:
        flags['cross_verified']=True
        for category in ['poet', 'composer', 'performer']:
            for p in results[0][category]: # each person in each category
                flag_p=False
                for result in results:
                    for s in result['self']:
                        if s==p: # current person p found in one of the self lists as s
                            flag_p=True
                            break
                # if any person p hasn't been found
                if flag_p==False:
                    flags['cross_verified']=False
                    # break 2 loops
                    break
            if flags['cross_verified']==False:
                break
    # enshure that each person in 'self' lists is present in 'poet', 'composers' or 'performer' list
    if flags['results_match']: print('same results!')
    if flags['title_match']: print ('title match!')
    if flags['cross_verified']==True:
        print('cross verification success!')
    else:
        print('cross verification failed')
    # if everyting verified - write results
    success=False
    if len(results)>1 and flags['no_failed_names'] and flags['results_match'] and flags['title_match'] and flags['cross_verified']: success=True
    if success:
        result=results[0]
        title=result['title']
        # assign performers
        for p in result['performer']:
            r.performers.add(p)
        # if we have poets - create poetry record
        # one poet cannot have multiple pieces with same title
        if len(result['poet'])>0:
            # here we filter poetry objects that have given title and any of given poets
            t=poetry.objects.filter(title=title, poets__in=result['poet']).distinct()
            if not t: # if no results - create, add poets and use
                t=poetry.objects.create(title=title)
                for p in result['poet']:
                    t.poets.add(p)
                t.save()
                print('poetry: "'+t.title.encode('utf8')+'" created')
            elif len(t)==1: # if one - add missing poets (if any) and use
                t=t[0]
                for p in result['poet']:
                    t.poets.add(p)
                t.save()
                print('poetry: "'+t.title.encode('utf8')+'" already exists')
            elif len(t)>1: # if multiple - join, add missing poets (if any) and use
                #for t_i in t[1:]:
                #    #
                print('poetry: multiple "'+t[0].title.encode('utf8')+'" have to be joined')
                continue
            # careful! recordings.poetry and recordings.music must have on_delete=models.SET_NULL
            # otherwise, we will lose recordings if we clean music or poetry tables
            r.poetry=t    
        if len(result['composer'])>0:
            # it is possible that we have no poets -> no poetry -> this is a standalone musical piece
            # in this case, t is not available
            m=music.objects.filter(poetry=t, composers__in=result['composer']).distinct()
            if not m:
                m=music.objects.create(poetry=t)
                for p in result['composer']:
                    m.composers.add(p)
                m.save()
                print('music: "'+m.poetry.title.encode('utf8')+'" created')
            elif len(m)==1:
                m=m[0]
                for p in result['composer']:
                    m.composers.add(p)
                m.save()
                print('music: "'+m.poetry.title.encode('utf8')+'" already exists')
            elif len(m)>1:
                print('music: multiple "'+m[0].poetry.title.encode('utf8')+'" have to be joined')
                continue
            r.music=m
        r.save()
    # next recording...


print('bye')
exit()

person.objects.exclude(recording=None)
len(p.recordings_set.all())
recording.objects.filter(Q(performers=p)|Q(music__composers=p)|Q(poetry__poets=p))



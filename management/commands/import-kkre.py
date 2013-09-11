#!/usr/bin/python
# coding=UTF-8

from _common import *

########
#STAGE 1
########
# read people lists, fill person and kkre_person_link tables

#person.objects.all().delete() doesn't work well with SQLite (number of variables in the request is limited)
#from django.db import connection
#cursor = connection.cursor()
#cursor.execute('DELETE FROM "{0}"'.format(kkre_person_link._meta.db_table))
#cursor.execute('DELETE FROM "{0}"'.format(person._meta.db_table))

# create categories
for category in ['poet', 'composer', 'performer']:
    ext_person_category.objects.get_or_create(category=category)

def people():
    lists=[
        ('http://kkre-1.narod.ru/komp.htm','composer','individual'),
        ('http://kkre-1.narod.ru/poet.htm','poet','individual'),
        ('http://kkre-1.narod.ru/pevi.htm','performer','individual female'),
        ('http://kkre-1.narod.ru/pevc.htm','performer','individual male'),
        ('http://krapp-sa.narod.ru/','performer','group'),
    ]
    for address,category,comtype in lists:
        print('fetching '+address+' (category: '+category+', type: '+comtype+')')
        # Type and subtype from combined type
        type=comtype.split(' ')[0]
        # Fetch and parse index page
        content=UnicodeDammit(open(fetch(address)).read(), is_html=True).unicode_markup
        doc=lxml.html.fromstring(content)
        for link in doc.cssselect('a'):
            if link.get('href')=='http://kkre-1.narod.ru/': continue
            
            # Collect information and create a person record
            name=link.text_content()
            # Ensure that name is unique before going further
            if len(name)==1: # Special case for 'first-letter' multi-person pages
                if address=='http://kkre-1.narod.ru/pevi.htm': name=u'певицы на "'+name+'"'
                elif address=='http://kkre-1.narod.ru/pevc.htm': name=u'певцы на "'+name+'"'
            # Check if name is already in database
            # If already present - take that person and add new categories and links if any, if not - create
            try:
                p=ext_person_name.objects.get(form='kkre', name=name).person
            except ext_person_name.DoesNotExist:
                # Will have to create new person record
                # back up original name
                name_kkre=name
                # Вокальный квартет "Гая" -> вокально-инструментальный ансамбль "Гая"
                # Ансамбль "Дружба" -> вокально-инструментальный ансамбль "Дружба"
                # normalize name
                name=re.sub('\s+', ' ', name) # multiple whitespaces
                name=name.strip() # trim
                # For individuals: put comma after non-shortable name part
                # It's usually a first word, but if the part in brackets follows, it's included
                if type=='individual':
                    name_head=name.split(' ')[0]
                    name_tail=''
                    flag_brackets=False
                    flag_head=True
                    for name_part in name.split(' ')[1:]:
                        # If we meet '('-beginning part - append everything till we find ')'-ending one
                        if name_part.startswith('('): flag_brackets=True
                        # If head still set and
                        if not (flag_brackets or name_part.lower()==u'оглы'): flag_head=False
                        # ')'
                        if flag_brackets and name_part.endswith(')'): flag_brackets=False
                        # It's a part of non-shortable name part
                        if flag_head: name_head=name_head+' '+name_part
                        # End of non-shortable name part, place comma here
                        else: name_tail=name_tail+' '+name_part
                    name=name_head+','+name_tail
                    # Restore current list subtype
                    # This code shouldn't be here
                    if len(comtype.split(' '))<2: subtype=''
                    else: subtype=comtype.split(' ')[1]
                    if subtype=='': sybtype=gender_from_name(name)
                # person still can already exist,
                #if it wasn't created with this script and has no ext_person_name kkre alias
                p,created=person.objects.get_or_create(name=name, type=type, subtype=subtype)
                # create kkre original name alias
                # this way we enshure that if we change person.name and re-run this script,
                #duplicate with original kkre name won't be created
                ext_person_name.objects.create(form='kkre', name=name_kkre, person=p)
            
            print '%s: %s' % (name, link.get('href'))
            
            # Name forms
            try: ext_person_name.objects.create(person=p, form='short', name=insens(p.name_short()))
            except: pass
            try: ext_person_name.objects.create(person=p, form='abbrv', name=insens(p.name_abbrv()))
            except: pass
            
            # Explicit categories
            ext_person_category.objects.get(category=category).people.add(p)
            
            # Page address
            href=link.get('href')
            if href=='http://kkre-2.narod.ru/gladkov.htm/': href='http://kkre-2.narod.ru/gladkov.htm'
            elif href=='http://kkre-48.narod.ru/chuev.htm/': href='http://kkre-48.narod.ru/chuev.htm'
            l,created=ext_person_link.objects.get_or_create(href=href, format='kkre')
            l.people.add(p)
    
    # some fixes
    # here is a problem: if we re-run stage 1 after fixes are applied,
    #wrong records will be added again, as unique constraint will not work after name/link change
    # solved via delete() on exception
    
    for p in person.objects.filter(name=u'Бюль-бюль оглы Полад'):
        p.name=u'Бюль-Бюль Оглы Полад' # non-breaking space
        p.name_e=p.name
        p.name_short=u'Полад Бюль-бюль оглы'
        p.name_abbrv=u'П. Бюль-бюль оглы'
        try: p.save()
        except: p.delete()
    
    for p in person.objects.filter(name=u'Лазарев-Мильдон Владимир Яковлевич'):
        p.name=u'Лазарев (Лазарев-Мильдон) Владимир Яковлевич'
        p.name_e=u'Лазарев Владимир Яковлевич'
        p.name_short=u'Владимир Лазарев'
        p.name_abbrv=u'В. Лазарев'
        try: p.save()
        except: p.delete()
    
########
#STAGE 2
########
# search for audio recordings on people pages, export links descriptions to kkre_recording_link table

def recordings():
    for l in ext_person_link.objects.filter(format='kkre'):
        print(l.href)
        # I want to use JS-like DOM API, but I also need a good parser to handle messy HTML
        # lxml parser and xml.dom? Seems to work...
        doc=SAX2DOM()
        #lxml.sax.saxify(parse(fetch(l.href)).getroot(), doc)
        lxml.sax.saxify(lxml.etree.parse(fetch(l.href), lxml.etree.HTMLParser(encoding='CP1251')).getroot(), doc)
        doc=doc.document
        for link in doc.getElementsByTagName('a'):
            href=link.getAttribute('href')
            title=dom_node_text(link).strip()
            legal_status=''
            # Filter recording links
            # Audiofiles
            if not href[-4:] in ['.mp3', '.ogg', '.wma', '.wav', '.vqf']:
                # melody.su links: let's assume there can be only one title on a one disk
                # Problem: there are multi-line links for multiple recordings on a same disk
                if 'melody.su' in href and href.split('melody.su')[1] not in ['', '/']:
                    href=href+'#'+title
                    legal_status='deleted'
                    # We might also want to set some flag indicating that recording is deleted by copyright holder
                else: continue
            description=dom_node_text_term(link).strip()
            print '%s: "%s" %s' % (href, title, description)
            r,created=recording.objects.get_or_create(href=href, legal_status=legal_status)
            try: ext_recording_link.objects.create(recording=r, href=l, title=title, description=description)
            except: pass

########
#STAGE 3
########
# analyse collected descriptions of every recording, try to guess its authors/performers/title, verify, export to poetry/music tables

def relations(recording_str=None):
    # load translation tables for name mistakes correction and case transformation
    #names_unknown={}
    #for line in open('./kkre_names_unknown').read().splitlines():
    #    line=unicode(line, 'utf8')
    #    name=line.split(':')
    #    if len(name)==2:
    #        names_unknown[name[1]]=name[0]
    
    names_ins={}
    try:
        for key,val in json.loads(open(basedir+'/kkre_names_cases.json').read()).iteritems(): names_ins[val]=insens(key)
    except: print('Error: failed to load names cases from an external file')
    
    # Getting the set of the recordings to build relations for
    # recording_str can be a recording file URL or http://kkre-29.narod.ru/kalinchenko/apn.mp3 a person webpage URL
    # If not provided - select all the recordings that are not bound by any relations yet
    if recording is not None:
        recordings=recording.objects.filter(href=recording_str)
        # if empty - try searching recording_str as a recordings list webpage url
        if len(recordings) == 0:
            #recordings=ext_recording_link.objects.filter(href=ext_person_link.objects.get(href=recording_str))
            # if still nothing - give up
            if len(recordings) == 0:
                print('Error: no such recording or webpage')
    else:
        recordings=recording.objects.filter(music=None, poetry=None)
    # Statistics
    total=recordings.count()
    counter=1
    # For each recording...
    for r in recordings:
        print(str(counter)+'/'+str(total)+': '+r.href)
        counter=counter+1
        #...we get all previously collected links pointing to it from different pages... 
        links=ext_recording_link.objects.filter(recording=r)
        # Results for current recording
        results=[]
        # Flags for verification
        flags={
            'no_failed_names':True
        }
        #...and analyse their descriptions to build relationships
        for l in links:
            # we need associated people, their categories and names (for debug output)
            result_tmp={'self':[], 'poet':[], 'composer':[], 'performer':[]}
            self=l.href.people.all()
            message=''
            # because we can have multiple people per reference page, this is a bit complicated
            # we will introduce two logical arrays
            self_any={'poet':False, 'composer':False, 'performer':False} # True, if any of assoc people are in category
            self_all={'poet':True, 'composer':True, 'performer':True} # True, if all assoc people are in category
            for p in self:
                result_tmp['self'].append(p)
                for category in ['poet', 'composer', 'performer']:
                    if p in ext_person_category.objects.get(category=category).people.all():
                        self_any[category]=True
                    else:
                        self_all[category]=False
                message+='['+p.name+']'
            message+=' "'+l.title+'" '+l.description
            
            # Split description into authors/performers substrings
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
                        if p in ext_person_category.objects.get(category='poet').people.all():
                            result_tmp['poet'].append(p)
                # if self is a composer, but not a poet - poets
                elif self_any['composer']==True and self_any['poet']==False:
                    poets=authors[0]
                    authors=''
                    for p in self:
                        if p in ext_person_category.objects.get(category='composer').people.all():
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
                    if p in ext_person_category.objects.get(category='performer').people.all():
                        result_tmp['performer'].append(p)
            
            # Iterate lists
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
                list=list.replace(u' и ', ';')
                # 'with ...'
                # if list begins with these words, self is omitted and others are in instrumental case
                ins_case=False
                for prefix in [u'с ', u'c ', u'со ', u'в дуэте с ', u'дуэт с ']:
                    if list.startswith(prefix):
                        ins_case=True
                        for p in self:
                            if p in ext_person_category.objects.get(category=category).people.all():
                                result_tmp[category].append(p)
                        list=list[len(prefix):]
                        break
                # split list by dividers into names
                list=list.split(';')
                
                # Now, iterate names
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
                    name=insens(name)
                    # is name comparison case-insensetive?
                    # look up the name in people table
                    while True:
                        p=person.objects.filter(ext_person_name__in=ext_person_name.objects.filter((Q(form='insens')&Q(name__iexact=name))|(Q(form='short')&Q(name__iexact=name))|(Q(form='abbrv')&Q(name__iexact=name))))
                        # single match
                        if len(p)==1:
                            result_tmp[category].append(p[0])
                            break
                        # multiple matches
                        elif len(p)>1:
                            # if only one of matching people is in current category - take him, otherwise - ambigious name
                            p=p.filter(ext_person_category__in=[ext_person_category.objects.get(category=category)])
                            if len(p)==1:
                                result_tmp[category].append(p[0])
                                break
                            else:
                                flags['no_failed_names']=False
                                print('ambigious name: '+name.encode('utf8'))
                                break
                        # no matches
                        else:
                            try:
                                # look in the corrections array
                                name=names_unknown[name]
                                # if present - take it and retry
                                # we can rely upon previous except: break to ensure that it won't retry infinitely
                                continue
                            except:
                                # if nothing - failed name
                                flags['no_failed_names']=False
                                break
                
                # Push resolved names into local result
                # this is WEIRD solution
                result_num=[]
                for p in result_tmp[category]:
                    result_num.append(p.id)
                result_num.sort()
                result_tmp[category]=[]
                for p in result_num:
                    result_tmp[category].append(person.objects.get(id=p))
            
            # Push local result into global result
            result_tmp['title']=l.title
            results.append(result_tmp)
            # debug output for local result
            message+=' => ( '
            for p in result_tmp['composer']: message+=str(p.id)+' '
            message+='- '
            for p in result_tmp['poet']: message+=str(p.id)+' '
            message+=') '
            for p in result_tmp['performer']: message+=str(p.id)+' '
            print(message.encode('utf8'))
        
        # Merge results
        # Find results with split composers/poets
        #for result in results:
        #    if result['authors']==[] and (result['poets']!=[] or result['composers']!=[]):
        # If none and same authors list everywhere - instrumental picece or poetry without music
        # If present - use them as basis to move authors to composers/poets in other results
        # Decide if authors list more alike composers or poets
        # decision factors: sets intersection sizes, categories of recognized people
        
        # Compare and verify results
        if not flags['no_failed_names']: print('[!] Failed names!')
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
                    if result[category]!=results[0][category] and flags['results_match']==True:
                        flags['results_match']=False
                        print('[!] Results do not match!')
                        break
                if result['title']!=results[0]['title']:
                    flags['title_match']=False
                    print('[!] Title does not match!')
        else: print('[!] Single result!')
        # cross-verification
        # enshure that each person in 'poets', 'composers', 'performers' lists is present in any 'self' list
        flags['cross_verified']=False
        flags['person_category_match']=False
        # only has sense if results match or just one result
        if flags['results_match'] or len(results)==1:
            flags['cross_verified']=True
            flags['person_category_match']=True
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
                        print('[!] Cross verification failed!')
                        # if this person has same category in ext_person_category - it's still quite safe to consider results being correct
                        # however, if not - it's dangerous
                        if ext_person_category.objects.get(category=category) not in p.ext_person_category_set.all(): flags['person_category_match']=False
                        # break 2 loops
                        # We shouldn't break, because not only we want to check if all people from parsed lists is in self list,
                        #but also for any person failing this check we want to check if category matches, which means we must continue till the end
                        #break
                #if flags['cross_verified']==False: break
            # We don't have to enshure that each person in 'self' lists is present in 'poet', 'composers' or 'performer' list,
            #because it should be done during the description analysis, when the algorithm tries to place at least one person from the 'self' list
            #into the local result
        
        # If everyting verified - write results to database
        if len(results)>1 and flags['no_failed_names'] and flags['results_match'] and flags['title_match'] and ((flags['cross_verified_right'] and flags['cross_verified_left']) or flags['person_category_match']):
            print('[*] Passed!')
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
                    for p in result['poet']: t.poets.add(p)
                    print('poetry: "'+t.title.encode('utf8')+'" created')
                elif len(t)==1: # if one - add missing poets (if any) and use
                    t=t[0]
                    for p in result['poet']: t.poets.add(p)
                    print('poetry: "'+t.title.encode('utf8')+'" already exists')
                elif len(t)>1: # if multiple - join, add missing poets (if any) and use
                    #for t_i in t[1:]:
                    #    #
                    print('poetry: multiple "'+t[0].title.encode('utf8')+'" have to be joined')
                    continue
                r.poetry=t
            if len(result['composer'])>0:
                # it is possible that we have no poets -> no poetry -> this is a standalone musical piece
                # in this case, t is not available
                m=music.objects.filter(poetry=t, composers__in=result['composer']).distinct()
                if not m:
                    m=music.objects.create(poetry=t)
                    for p in result['composer']: m.composers.add(p)
                    print('music: "'+m.poetry.title.encode('utf8')+'" created')
                elif len(m)==1:
                    m=m[0]
                    for p in result['composer']: m.composers.add(p)
                    print('music: "'+m.poetry.title.encode('utf8')+'" already exists')
                elif len(m)>1:
                    print('music: multiple "'+m[0].poetry.title.encode('utf8')+'" have to be joined')
                    continue
                r.music=m
            # Must save recording after we've set poetry and music
            r.save()
        # next recording...

#def __main__():
#    print('hello')
#    #people()
#    #recordings()
#    #relations()

from django.core.management.base import BaseCommand
class Command(BaseCommand):
    def handle(self, *args, **options):
        if len(args)>0:
            if args[0]=='relations':
                if len(args)>1:
                    relations(args[1])
                else:
                    relations()
            else:
                print('unknown function')
        else:
            print('all')

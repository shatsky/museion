#!/usr/bin/python
# coding=UTF-8

import re

# parse broken html from file using lxml.html parser and chardect encoding autodetection
def lxmlparse(filepath):
    import lxml.html
    import chardet
    document=open(filepath).read()
    print('Info: detecting document encoding...')
    document=document.decode(chardet.detect(document)['encoding'])
    document=lxml.html.fromstring(document)
    return document

# function to import people names and addresses of pages which contain recordings and people data
def people():
    return
    lists=[
        ('http://kkre-1.narod.ru/komp.htm','composers','individual'),
        ('http://kkre-1.narod.ru/poet.htm','poets','individual'),
        ('http://kkre-1.narod.ru/pevi.htm','performers','individual female'),
        ('http://kkre-1.narod.ru/pevc.htm','performers','individual male'),
        ('http://krapp-sa.narod.ru/','performers','group'),
    ]
    for address,category,comtype in lists:
        print('fetching '+address+' (category: '+category+', type: '+comtype+')')
        # Type and subtype from combined type
        type=comtype.split(' ')[0]
        # Fetch and parse index page
        content=UnicodeDammit(open(fetch(address)).read(), is_html=True).unicode_markup
        doc=lxml.html.fromstring(content)
        for link in doc.cssselect('a'):
            # Ignore links that do not point to people pages
            if link.get('href')=='http://kkre-1.narod.ru/': continue
            # Collect information and create a person record
            name=link.text_content()
            # Ensure that name is unique before going further
            if len(name)==1: # Special case for 'first-letter' multi-person pages
                if address=='http://kkre-1.narod.ru/pevi.htm': name=u'певицы на "'+name+'"'
                elif address=='http://kkre-1.narod.ru/pevc.htm': name=u'певцы на "'+name+'"'
            # Check if name is already in database as 'kkre'-form ext_person_name
            # If already present - take its person and add new categories and links (if any), if not - create
            try:
                person=models.ext_person_name.objects.get(form='kkre', name=name).person
            except models.ext_person_name.DoesNotExist:
                # back up kkre name
                name_kkre=name
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
                    if subtype=='': subtype=gender_from_name(name)
                # person still can already exist, if it wasn't created with this script and has no ext_person_name kkre alias
                person,created=models.person.objects.get_or_create(name=name, type=type, subtype=subtype)
                # create kkre original name alias
                # this way we enshure that if we change person.name and re-run this script, duplicate with original kkre name won't be created
                models.ext_person_name.objects.create(form='kkre', name=name_kkre, person=person)
            print '%s: %s' % (name, link.get('href'))
            # Explicit categories
            models.ext_person_category.objects.get(category=category).people.add(person)
            # Page address
            href=link.get('href')
            if href=='http://kkre-2.narod.ru/gladkov.htm/': href='http://kkre-2.narod.ru/gladkov.htm'
            elif href=='http://kkre-48.narod.ru/chuev.htm/': href='http://kkre-48.narod.ru/chuev.htm'
            page_link,created=ext_person_link.objects.get_or_create(href=href, format='kkre')
            page_link.people.add(person)
    # some fixes
    # Вокальный квартет "Гая" -> вокально-инструментальный ансамбль "Гая"
    # Ансамбль "Дружба" -> вокально-инструментальный ансамбль "Дружба"
    for name,name_fix in {
        u'Лазарев-Мильдон, Владимир Яковлевич':u'Лазарев (Лазарев-Мильдон), Владимир Яковлевич'
    }:
        person=models.person.objects.get(name=name)
        person.name=name_fix
        person.save()

# get text from lxml.html node from start till any non-allowed tag
# useful for parsing messy html (e. g. we know recording description line can contain italics and bold text, but there can be <br> inside <b> or <i>,
# and all text after that <br> is not a part of the description - so we call this function with allowedtags=['i','b'])
def inner_text_until_term(element, allowedtags, root=True):
    # if it's a terminating tag - do not add any text and return a marker to stop
    # however, be permissive if root is True (meaning this function instance if a root of the recursion tree, called for a root node, which han be any tag)
    if not root and element.tag not in allowedtags: return '',True
    # otherwise, add element text and start iterating its children
    text=''
    if type(element.text) is unicode: text+=element.text
    for child in element.getchildren():
        text_frag,stop=inner_text_until_term(child, allowedtags, False)
        text+=text_frag
        # if a child has returned stop marker - stop and return text with stop, too (this will propagate recursively)
        if stop:
            # if root is True, this is our final result and we return only a text (same in the end)
            if not root: return text,True
            else: return text
    if type(element.tail) is unicode: text+=element.tail
    if not root: return text,False
    else: return text

def outher_text_until_term(element, allowedtags):
    stop=False
    text=(element.tail if element.tail is not None else '')
    text_frag=''
    while not stop and element.getnext() is not None:
        element=element.getnext()
        text+=text_frag
        text_frag,stop=inner_text_until_term(element, allowedtags, False)
    return text

# import people photos and descriptions
def person_data(page_filename):
    document=lxmlparse(page_filename)
    data={}
    # get photo and description
    for image in document.cssselect('img'):
        # photo can be found by an img tag with image filename equal to page filename
        if '.'.join(filename.split('/')[-1].split('.')[:-1])=='.'.join(image.get('src').split('/')[-1].split('.')[:-1]):
            # first, we need to mirror the image
            #image_link='/'.join(page_link.href.split('/')[:-1])+'/'+image.get('src')
            data['image']=image.get('src')
            # description is in p next to this img
            # or the only p between img and first recording link
            # or the first p after <CENTER><H2>{{ name_short }}</CENTER></H2>
            if image.getnext() is not None and image.getnext().tag=='p':
                data['text']=inner_text_until_term(image.getnext(), ['br']).strip()
            break
    return data

# import recordings
def recordings(page_filename):
    document=lxmlparse(page_filename)
    recordings=[]
    # get all links
    for link in document.cssselect('a'):
        href=link.get('href')
        title=link.text_content().strip()
        legal_status=''
        # Filter recording links
        # Audiofiles
        if href is None: continue # mistyped <a> instead of </a>, http://kkre-34.narod.ru/monin/ulu.mp3
        if not href[-4:] in ['.mp3', '.ogg', '.wma', '.wav', '.vqf']:
            # melody.su links: let's assume there can be only one title on a one disk
            # Problem: there are multi-line links for multiple recordings on a same disk
            if 'melody.su' in href and href.split('melody.su')[1] not in ['', '/']:
                href=href+'#'+title
                legal_status='deleted'
                # We might also want to set some flag indicating that recording is deleted by copyright holder
            else: continue
        description=outher_text_until_term(link, ['b', 'i']).strip()
        print '%s: "%s" %s' % (href, title, description)
        recordings.append({'href':href, 'title':title, 'description':description, 'legal_status':legal_status})
    return recordings

def result_from_recording_description(description):
    result={}
    # split description string into authors and performers
    strings={}
    description.strip()
    if not description: # empty description, but we can still use subjects list
        print 'Warning: empty descripton'
    elif description[0]=='(':
        if len(description)>1:
            description=description.split(')')
            description[0]=re.sub('^\s.\(', '', description[0])[1:].strip()
            if '(' in description[0]:
                print('Error: description string parse error 1')
                return
            description[0]=description[0].replace(u'–', u'-').split(' - ')
            if len(description[0])==1:
                strings['authors']=description[0][0]
            elif len(description[0])==2:
                strings['composers']=description[0][0]
                strings['poets']=description[0][1]
            else:
                print('Error: description string parse error 2')
                return
            description[1]=')'.join(description[1:]).strip() # if there are other bracketed parts after authors
            # if description[1] is not empty, it's a performers list
            if description[1]:
                strings['performers']=description[1]
        else: # begins with '(', but has no ')'
            print('Error: description string parse error 3')
    else: # no authors, all description is a performers list
        if description:
            strings['performers']=description
    for key in strings.keys():
        # name list dividers
        strings[key]=strings[key].replace(',', ';')
        # in certain contexts 'и' is not a divider
        # e. g. 'Хор ВР и ЦТ'
        strings[key]=strings[key].replace(u' и ', ';')
        # in certain contexts '/' is not a divider
        # e. g. 'х/ф', 'п/у'
        # let's assume all of them have '<start_of_line_or_whitespace><single_character>/<single_character><whitespace_or_end_of_line>' pattern,
        # and any '/' out ot this pattern to be a name divider
        # I failed to write a 'start_(end)_of_line or whitespace' expression in a regexp, so I add border whitespaces which will be trimmed later
        strings[key]=' '+strings[key]+' '
        strings[key]=re.sub('(?<!\s\S)/', ';', re.sub('/(?!\S\s)', ';', strings[key]))
        # create an empty result item
        result[key]={'flags':[], 'people':[], 'people_filtered':[]}
        # split list into names and fill result item people list with them
        result[key]['people']=strings[key].split(';')
        # clean up a little
        result[key]['people']=[re.sub('\s+', ' ', re.sub('\.\s*', '. ', name)).strip() for name in result[key]['people']]
        # incomplete strings: if a string begins with 'with ...', it means its set must be completed with people from page subjects set,
        # and people names in this string are given in instrumental case
        for prefix in [u'с ', u'c ', u'со ', u'вместе с ', u'дуэт с ', u'в дуэте с ']:
            if result[key]['people'][0].startswith(prefix):
                result[key]['people'][0]=result[key]['people'][0][len(prefix):]
                result[key]['flags'].append('incomplete')
                # convert cases
                import _ru_mystem_inflect
                for idx in range(0, len(result[key]['people'])):
                    name_norm=_ru_mystem_inflect.name_instrumental_to_nominative(result[key]['people'][idx])
                    if name_norm is None:
                        print('Warning: case normalization failed for name "'+result[key]['people'][idx]+'"')
                        # add 'с ' prefix to the beginning of the name
                    else:
                        # if normalized name differs from original - add original form to people_filtered and replace it with normalized in people
                        if result[key]['people'][idx]!=name_norm:
                            print('Info: case normalization: "'+result[key]['people'][idx]+'" -> "'+name_norm+'"')
                            result[key]['people_filtered'].append(result[key]['people'][idx])
                            result[key]['people'][idx]=name_norm
                break
    return result


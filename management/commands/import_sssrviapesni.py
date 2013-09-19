#!/usr/bin/python
# coding=UTF-8

from common import *

def people():
    filepath=mirror_file('http://sssrviapesni.narod.ru/index.html')
    baseurl=filepath.replace(mirrordir, 'http://').replace('index.html', '')
    content=UnicodeDammit(open(filepath).read(), is_html=True).unicode_markup
    doc=lxml.html.fromstring(content)
    # iterate all a.anamevia links
    for link in doc.cssselect('a.anamevia'):
        href=link.get('href')
        if not (href.endswith('html') or href.endswith('htm') or href.endswith('/')) or href=='oprosy.html' or href=='pamyatvia.html': continue
        if not href.startswith('http://'): href=baseurl+href
        name=link.text_content()
        try:
            p=ext_person_name.objects.get(form='sssrviapesni', name=name).person
        except ext_person_name.DoesNotExist:
            # Name
            name_sssrviapesni=name
            if name==u'Ансамбль п\у Назарова' or name==u'Гр. Валентина Бадьярова':
                subtype=''
            else:
                subtype='ussrvia'
                name=name.replace('(', ' (')
                name=name.replace(')', ') ')
                name=re.sub('\s+', ' ', name)
                name=name.strip()
                # quoting title (very dirty)
                name_head=''
                name_tail=''
                flag_name_head=True
                for name_part in name.split(' '):
                    if name_part.startswith('('): flag_name_head=False
                    if flag_name_head: name_head=name_head+' '+name_part
                    else: name_tail=name_tail+' '+name_part
                name='"'+name_head.strip()+'"'+name_tail
                # prefix
                name=u'Вокально-инструментальный ансамбль '+name
            p,created=person.objects.get_or_create(name=name, type='group', subtype=subtype)
            ext_person_name.objects.create(form='sssrviapesni', name=name_sssrviapesni, person=p)
        
        l,created=ext_person_link.objects.get_or_create(href=href, format='sssrviapesni')
        l.people.add(p)
        
        ext_person_category.objects.get(category='performer').people.add(p)
        
        print(name+' '+href)


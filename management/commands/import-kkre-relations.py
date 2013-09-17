#!/usr/bin/python
# coding=UTF-8

# TODO
# Structure of result item is such that ['flags'][set_key] does not get a new set_key when ['sets'][set_key] does (e. g., 'uothors' moved to 'poets')
# "Guess authors set_key from authors people categories" code doesn't seem to be executed; more exactly, database call in all_in_category doesn't
#  fixed: problem was names which weren't formatted as needed, because "for n in arr: n=<expr>" doesn't change original n instance in arr in Python
# Set keys and categories should be in one form to simplify code, currently keys are in plural ('poets') and categories in single ('poets')
#  fixed
# Cannot remove items from list in loop, because in-place list modification breaks iteration
#  fixed: for item in list(list) iterates over a temporary copy of list, allowing to modify original instance
# Something wrong with quoted parts in description string, seems to deal with pypasring
#  ?
# If there is explicitly given subject person in authors, that's either poet or composer, it can mean that here it's both poet and composer
# see http://vale-patrushev.narod.ru/wesennem-lesu.mp3 for example
#  fixed: done in authors placement heuristics
# Relations structure: instead of just deleting strings of resolved names, we need to pass them to database import code, so that it can delete
# ext_unknown_name relations which can be existing from previous runs, when these names were unknown
# it would also be nice to be able to remove "names" that are not really names (e. g. 'из к/ф ...') but were treated as names on a previous run 
# and added to ext_unknown_name
#  what about having ['sets'][category]['filtered'] list of names that we do not want?
# Instrumental case: what should we do if we don't have a replacement for instrumental name form?
#  ?
# 'е'/'ё' insensitivity

from djmuslib import models
from django.db.models import Q
import pyparsing
import re

# we have 5 sets, 2 internal:
# 'subjects' - people who are subjects of the webpage containing the link;
# if it contains >1 person, we cant be shure that every one ot them is relevant to
# 'authors' - authors of the piece; can be a pair of '-'-separated ('composers' - 'poets') lists, or a single list;
# if it's a single list, we have to determine wether it's 'composers' or 'poets'
# and 3 final which form a result:
# 'poets'
# 'composers'
# 'performers'
# we take advantage of mixed-type arrays to store both string names and int ids in our sets

# resolve name into database id: returns an array which can either be empty (unknown name), contain one id (exact match) or multiple ids (ambigious name)
def name_to_id(name, category=None):
    people=models.person.objects.filter(ext_person_name__in=models.ext_person_name.objects.filter((Q(form='insens')&Q(name__iexact=name))|(Q(form='short')&Q(name__iexact=name))|(Q(form='abbrv')&Q(name__iexact=name))))
    # qualify ambigious result using category information, if it's provided
    if len(people)>1 and category!=None:
        people=people.filter(ext_person_category__in=[models.ext_person_category.objects.get(category=category)])
    # return result as an array of ids
    result=[]
    for person in people:
        result.append(person.id)
    return result

# check if person is in set
def person_in_set(person, set):
    # people in sets can be represented either by their string names or database ids
    # in id-to-name comparison, we assume that, if the name name_to_ids to multiple ids (ambigious), and one of them matches, it's a legitimate match
    # direct id-to-id or name-to-name match:
    if person in set: return True
    # id in set1 to name in set2
    elif type(person) is int:
        for person_from_set in set:
            if type(person_from_set) is unicode and person in name_to_id(person_from_set): return True
    # name in set1 to id in set2
    elif type(person) is unicode:
        for person_from_set in set:
            if type(person_from_set) is int and person_from_set in name_to_id(person): return True
    return False

# how much does set1 resemble set2?
def match_sets(set1, set2):
    counter=0
    for person in set1:
        if person_in_set(person, set2): counter+=1
    return counter

# check if all people are in set
def all_in_set(people, set):
    if match_sets(people, set)==len(people): return True
    else: return False

# check if person with a given id is in category
def person_in_category(id, category):
    return models.person.objects.get(id=id) in models.ext_person_category.objects.get(category=category).people.all()

# check if any people from set belong to category
def any_in_category(set, category):
    for p in set:
        if type(p) is unicode:
            # if name mathes multiple people from the database - check if any of them is in category
            # if no matches - we cannot be shure, return False (recursively called any_in_category() will return False for an empty set)
            if any_in_category(name_to_id(p), category): return True
        elif type(p) is int:
            if person_in_category(p, category): return True
    return False

# check if all people from set belong to category
def all_in_category(set, category):
    for p in set:
        if type(p) is unicode:
            # much like in any_in_category()
            # yes, we call any_in_category() here, not all_in_category(), because idea about ambigious names is same here
            if not any_in_category(name_to_id(p), category): return False
        elif type(p) is int:
            if not person_in_category(p, category): return False
    return True

# merge sets with given keys from all results (as needed for some verification tricks)
def merge_sets(result_array, keys=None):
    merged=[]
    if keys==None: keys=['subjects', 'authors', 'poets', 'composers', 'performers'] # all possible keys
    for result in result_array:
        for key in keys:
            if key in result:
                merged+=result[key]['people']
    return merged

# instrumental case to name case
def name_ins(name):
    return name

# build description analysis result item from description substring
def result_item(string):
    item={'flags':{}, 'people':[], 'people_filtered':[]}
    if len(string)==0: return item
    # incomplete strings: if a string begins with 'with ...', it means its set must be completed with people from page subjects set,
    # and people names in this string are given in instrumental case
    item['flags']['incomplete']=False
    for prefix in [u'с ', u'c', u'со ', u'вместе с ']:
        if string.startswith(prefix):
            item['flags']['incomplete']=True
            string=string[len(prefix):]
            # convert cases after name split
            break
    # name list dividers
    string=string.replace(',', ';')
    # in certain contexts 'и' is not a divider
    # e. g. 'Хор ВР и ЦТ'
    string=string.replace(u' и ', ';')
    # in certain contexts '/' is not a divider
    # e. g. 'х/ф', 'п/у'
    # let's assume all of them have '<start_of_line_or_whitespace><single_character>/<single_character><whitespace_or_end_of_line>' pattern,
    # and any '/' out ot this pattern to be a name divider
    # I failed to write a 'start_(end)_of_line or whitespace' expression in a regexp, so I add border whitespaces which will be trimmed later
    string=' '+string+' '
    string=re.sub('(?<!\s\S)/', ';', re.sub('/(?!\S\s)', ';', string))
    # split list into names
    item['people']=string.split(';')
    # clean up a little
    item['people']=[re.sub('\.\s*', '. ', name).strip() for name in item['people']]
    # name case convertion
    if item['flags']['incomplete']:
        item['people']=[name_ins(name) for name in item['people']]
    return item

# attempt building relations for a given recording
def build_recording_relations(recording):
    links=models.ext_recording_link.objects.filter(recording=recording)
    result_array=[]
    result_reference={'poets':[], 'composers':[], 'performers':[]}
    # first pass: form initial sets from description strings in a straightforward way; find reference sets, if possible
    for link in links:
        print(link.href.href+': "'+link.title+'" '+link.description)
        # if there are linebreaks in the title string, we have a problem
        if '\n' in link.title:
            print('Error: title contains newlines')
            return False
        result={}
        # split description string into authors and performers
        # try parsing it as a bracketed expression
        pyparsing.nestedExpr('(',')').setDefaultWhitespaceChars('') #???
        try: description=pyparsing.nestedExpr('(',')').parseString('('+link.description+')').asList()
        except:
            print('Error: description string parse error 1')
            continue
        # get rid of redundant nesting
        #while type(description) is list and len(description)==1 and type(description[0]) is list: description=description[0]
        description=description[0]
        if len(description)>=1:
            # if first element is a list, we expect its single inner element to be a string of authors
            if type(description[0]) is list and len(description[0])==1 and type(description[0][0]) is unicode:
                # description[0][0] is an authors string
                # it can be aither like 'composers - poets' (in this case we split it)
                # or just 'composers' or 'poets' (in these cases we add it as 'authors' result item, for we can't guess what it means yet)
                description[0][0]=description[0][0].split(' - ')
                if len(description[0][0])==1:
                    result['authors']=result_item(description[0][0][0])
                elif len(description[0][0])==2:
                    result['composers']=result_item(description[0][0][0])
                    result['poets']=result_item(description[0][0][1])
                else:
                    # something wrong
                    print('Error: bad authors substring')
                    break
                # and description[1], if present, is a performers string
                if len(description)>=2:
                    if type(description[1]) is unicode:
                        result['performers']=result_item(description[1])
                    else:
                        print('Error: description string parse error 2')
                        continue
                # if doesn't - ok, we don't have performers here
            # otherwise, it should be a string of performers
            elif type(description[0]) is unicode:
                result['performers']=result_item(description[0])
            else:
                print('Error: description string parse error 3')
                continue
        else:
            # empty description, but we can still use subjects list
            print('Warning: empty description')
        # now we must have sets of clean names
        # take reference sets
        for key in ['poets', 'composers', 'performers']:
            if key in result and not result[key]['flags']['incomplete']:
                result_reference[key]=list(set(result_reference[key]+result[key]['people']))
        # add subjects set
        result['subjects']={'people':[], 'people_filtered':[]} # we only need a list for subjects
        for person in link.href.people.all():
            result['subjects']['people'].append(person.id)
        # push result into res_arr
        result_array.append(result)
    # we can have a music- or poetry-only piece
    # conditions: no (composers - poets) splittable authors string, all authors strings similar
    # nope, we won't check this, our heuristics will simply leave empty poets or composers set in this case, which is much easier to check
    # second pass: clarify results using heuristics
    for result in result_array:
        # if 'subjects' contains multiple people - drop irrelevant ones
        if len(result['subjects']['people'])>1:
            for person in list(result['subjects']['people']):
                # check if this person can be seen in descriptions of other links, otherwise drop it
                if not person_in_set(person, merge_sets(result_array, ['authors', 'poets', 'composers', 'performers'])):
                    print('Warning: multiple subjects verification: '+str(person)+' doesn\'t appear in other sets, will be ignored')
                    result['subjects']['people_filtered'].append(person) # to remove from existing objects on database import stage, if somewhy added earlier
                    result['subjects']['people'].remove(person)
            # what if we have an empty list after this?
        # if we have 'authors' set - guess whether it's 'poets' or 'composers'
        if 'authors' in result:
            # if we have 'poets' and 'composers' reference sets - compare it with them
            if 'poets' in result_reference and 'composers' in result_reference and match_sets(result['authors']['people'], result_reference['poets'])>match_sets(result['authors']['people'], result_reference['composers']):
                result['poets']=result.pop('authors')
            elif 'poets' in result_reference and 'composers' in result_reference and match_sets(result['authors']['people'], result_reference['poets'])<match_sets(result['authors']['people'], result_reference['composers']):
                result['composers']=result.pop('authors')
            # try to guess using categories
            elif all_in_category(result['authors']['people'], 'poets') and not all_in_category(result['authors']['people'], 'composers'):
                # if an authors list is a list of people from webpage subject list - this likely means they are poets and composers simultaneously
                # so we place them into a set they shouldn't normally be in, and other one will be populated later by same people by category match
                if all_in_set(result['authors']['people'], result['subjects']['people']):
                    result['composers']=result.pop('authors')    
                else:
                    result['poets']=result.pop('authors')
            elif all_in_category(result['authors']['people'], 'composers') and not all_in_category(result['authors']['people'], 'poets'):
                if all_in_set(result['authors']['people'], result['subjects']['people']):
                    result['poets']=result.pop('authors')
                else:
                    result['composers']=result.pop('authors')
            # try to guess as the opposite to subjects
            elif all_in_category(result['subjects']['people'], 'poets') and not all_in_category(result['subjects']['people'], 'composers'):
                result['composers']=result.pop('authors')
            elif all_in_category(result['subjects']['people'], 'composers') and not all_in_category(result['subjects']['people'], 'poets'):
                result['poets']=result.pop('authors')
            else:
                # warning flag
                print('Warning: failed to determine authors category')
        # now, if we don't have a required set - it can be empty either because it contains self,
        # or because it's text is placed out of the link description on the page (e. g. single 'performers' string for multiple links)
        # besides, existing set can require completion from 'subjects' ('with... ')
        for key in result_reference:
            if key not in result or result[key]['flags']['incomplete']:
                if key not in result: result[key]=result_item('')
                # try populating the set with people from 'subjects'
                for key2 in 'people', 'people_filtered':
                    for person in result['subjects'][key2]:
                        # if subject person is in matching category - add it
                        if person_in_category(person, key):
                            result[key][key2].append(person)
        # what if we failed to place subjects? - warning flag
        # TODO we must now replace result in result_array with a modified result
        # WTF why it works with just that? Don't we make everthing with a local copy of result?
    # now we can form a final result
    result_final={}
    for key in result_reference.keys():
        result_final[key]=result_item('')
        for result in result_array:
            for key2 in ['people', 'people_filtered']:
                result_final[key][key2]=list(set(result_final[key][key2]+result[key][key2]))
    # resolve names
    # we cannot remove elements in-place, because changing the list breaks iteration
    for key in result_final.keys():
        for person in list(result_final[key]['people']):
            if type(person) is unicode:
                ids=name_to_id(person, key)
                if len(ids)==1:
                    # one more safety measure: any recognized person must be either in category-matching list, or be present in one of the 'subjects' lists
                    if person_in_category(ids[0], key) or ids[0] in merge_sets(result_array, ['subjects']):
                        result_final[key]['people'].append(ids[0])
                    else:
                        print('Warning: name "'+person+'" resolved, but is neither in appropriate category nor in subjects lists, ignored')
                    result_final[key]['people'].remove(person)
                    result_final[key]['people_filtered'].append(person)
                else:
                    # unknown name
                    if len(ids)==0:
                        # mistyped name?
                        print('Warning: unknown name "'+person+'"')
                    # ambigious name
                    elif len(ids)>1:
                        print('Warning: ambigious name "'+person+'"')
        # deduplicate, possibly using number duplicates to rate the reliability of a relation guess
        for key2 in ['people', 'people_filtered']:
            result_final[key][key2]=list(set(result_final[key][key2]))
        print(key+': '+str(result_final[key]['people']))
    # if poets or composers sets are empty - it's a music-only or a text-only piece
    # warning: this may also mean that poets or composers string is placed out-of-description for this recording on all webpages,
    #  and poets or composers do not have their own pages
    # what if we don't have anybody in people, but _do_ have somebody in people_filtered?
    #  this would mean that with new data we now don't think we this kind of piece for this recording
    #  so we delete only people list, not a whole result item
    for key in ['poets', 'composers']:
        if len(result_final[key]['people'])==0:
            print('Warning: '+key+' set is empty, removed')
            result_final[key].pop('people')
    return result_final

# check if we can merge pieces
# -for any specific model field, in any selected object which has non-empty value in this field, this value must the the same one;
#  (because if not, we don't know if we can take one of multiple non-empty values available for this field and drop all the others)
# -any verified object cannot be modified;
def merge_possible(selection):
    if len(selection)<=1: return True
    # create a dictionary from all fields, except M2M and 'title'
    piece_dict={}
    for field in [field.name for field in selection.model._meta.fields if field.name!='id']:
        piece_dict[field.name]=None
    for piece in selection:
        for key in piece_dict.keys():
            # if field is not empty
            if getattr(piece, key):
                # if field is empty in dictionary: fill it with corrent value
                if piece_dict[key] is None: piece_dict[key]=getattr(piece, key)
                # if field is not empty in dictionary: if current value differs from the dictionary value - merge impossible
                elif piece_dict[key]!=getattr(piece, key): return False
    return True

# merge selected pieces
# -collect non-empty values of regular fields and fill first selected object with them
# -merge M2M fields, copying all references existing in selected objects to the first selected object
#  btw, what about implementing such a mechanism for M2M relations with extra fields?
# -redirect all pointers from other objects referencing selected object to the first selected object
# -delete all selected objects except the first one
def merge(selection):
    # copy everything to first piece (from pieces 1...last to piece 0)
    for piece in selection[1:]:
        # check for non-empty regular fields
        for field in [field.name for field in selection.model._meta.fields if field.name!='id']:
            # if non-empty in current piece and empty in the first piece - copy to the first piece
            if getattr(piece, field) and not getattr(selection[0], field):
                setattr(selection[0], field, getattr(piece, field))
        # check for relations via m2m fields
        for m2m_field in [field.name for field in selection.model._meta._many_to_many()]:
            # move from piece.m2m_field to selection[0].m2m_field
            for instance in getattr(piece, m2m_field).all():
                getattr(selection[0], m2m_field).add(instance)
                #getattr(piece, m2m_field).remove(instance) # it's not nesessary to delete instance from piece, because piece itself will be deleted
        # check for relations via m2m fields of other models
        for m2m_set in [related_object.get_accessor_name() for related_object in selection.model._meta.get_all_related_many_to_many_objects()]:
            # add objects from piece m2m_set to selection[0] m2m_set and delete them from piece m2m_set
            # which should be equal to deleting piece from m2m_field of each item and adding selection[0] instead
            for item in getattr(piece, m2m_set).all():
                getattr(selection[0], m2m_set).add(item)
                #getattr(piece, m2m_set).remove(item)
        # check for relations via fk fields of other models
        for fk_set in [related_object.get_accessor_name() for related_object in selection.model._meta.get_all_related_objects()]:
            # add objects from piece fk_set to selection[0] fk_set and delete them from piece fk_set
            # which should be equal to changing each fk_field of each item from piece to selection[0]
            for item in getattr(piece, fk_set).all():
                getattr(selection[0], fk_set).add(item)
                #getattr(piece, fk_set).remove(item)
        piece.delete()
    return selection[0]

# get all titles for a recording
def recording_titles(recording):
    titles=[]
    for link in recording.ext_recording_link_set.all():
        titles.append(link.title)
    return titles

# get all titles for a piece
def piece_titles(piece):
    titles=[]
    # can we get all ext_recording_link objects at once?
    for recording in piece.recording_set.all():
        titles+=recording_titles(recording)
    return titles

# export relations into database objects
# relations_data object structure:
# category(poets,composers,performers)/
#  ids/: list of database ids of person objects
#  names/: list of names that failed
#   we have ext_unknown_names table to track them for statistics and ext_unknown_names_<category> to track their relations with recording/music/poetry objects
#   this allows us to see which names cause most problems, automatically re-run relations import as we create person objects for them,
#   meanwhile displaying them in lists on webpages like known people names
# titles/
# meta/
def import_recording_relations(recording):
    result_final=build_recording_relations(recording)
    if result_final==False: return False
    # recording
    # even if we will fail with poetry and music, recording will show up on performers pages as an 'Unknown Piece'
    # we also add unknown names and drop filtered names
    for person in result_final['performers']['people']:
        if type(person) is int:
            recording.performers.add(person)
        elif type(person) is unicode:
            name,created=models.ext_unknown_name.objects.get_or_create(name=person)
            name.recordings.add(recording)
    for person in result_final['performers']['people_filtered']:
        if type(person) is int:
            recording.performers.remove(person)
        elif type(person) is unicode:
            try: name=recording.ext_unknown_name_set.get(name=person)
            except: pass
            else: name.recordings.delete(recording)
    # poetry
    if 'poets' in result_final and 'people' in result_final['poets']: # otherwise, a music-only piece
        # recording can already have an associated poetry piece
        # there can also be other poetry pieces with same title and poets
        # select poetry that should be merged with the result: poetry which has title from titles list and either has poets from poets list or is associated
        #  with the current recording and has no poets
        # TODO: result_final['poets']['names_unknown']+result_final['poets']['people_filtered'] ?
        poetry=models.poetry.objects.filter((Q(title__in=recording_titles(recording))|Q(recording__ext_recording_link__title__in=recording_titles(recording)))&(Q(poets__in=[person for person in result_final['poets']['people'] if type(person) is int])|Q(ext_unknown_name__name__in=[person for person in result_final['poets']['people'] if type(person) is unicode])|Q(recording=recording))).distinct()
        #poetry=models.poetry.objects.filter((Q(title__in=recording_titles(recording))|Q(recording__ext_recording_link__title__in=recording_titles(recording)))&(Q(poets__in=[person for person in result_final['poets']['people'] if type(person) is int])|Q(recording=recording))).distinct()
        # recording.poetry should be either in the selection or None, otherwise raise error
        # we also enshure that selection is mergeable to avoid possible merge problems (e. g. different creation years specified in different objects)
        if (recording.poetry is not None and recording.poetry not in poetry) or not merge_possible(poetry):
            print('Error: cannot merge poetry results with data already present in the database')
            print(poetry)
        else:
            if len(poetry)==0: # if no results - create, add poets and use
                poetry=models.poetry.objects.create(title=recording_titles(recording)[0])
                print('Info: poetry created, id='+str(poetry.id))
            elif len(poetry)==1: # if one - add missing poets (if any) and use
                poetry=poetry[0]
                print('Info: poetry already exists, id='+str(poetry.id))
            elif len(poetry)>1: # if multiple - merge, add missing poets (if any) and use
                poetry=merge(poetry)
                print('Info: multiple poetry pieces merged, id='+str(poetry.id))
            # poets
            for person in result_final['poets']['people']:
                if type(person) is int:
                    poetry.poets.add(person)
                elif type(person) is unicode:
                    name,created=models.ext_unknown_name.objects.get_or_create(name=person)
                    name.poetry.add(poetry)
            for person in result_final['poets']['people_filtered']:
                if type(person) is int:
                    poetry.poets.delete(person)
                elif type(person) is unicode:
                    try: name=poetry.ext_unknown_name_set.get(name=person)
                    except: pass
                    else: name.poetry.remove(poetry)
            # create relation
            recording.poetry=poetry
            recording.save()
            # update main title, if needed
            # this must be done after creating relation with recording, title is selected as the most common title in all related recording links
            poetry.title=piece_titles(poetry)[0]
            poetry.save()
        # if there is an empty poets set, a poetry with no poets will be created
        # in this case, for recordings with same poetry there will be duplicates, because empty poets sets will not give information to trigger merge(),
        # causing a new poetry object to be created for each recording
        # however, when this function will be re-run for these recordings after we create person objects for poets of its poetry,
        # its poetry objects will we completed with now-recognizeable poets and merged altogether, one after another
    else:
        poetry=None
        # TODO: we can still have people_filtered
    # music
    if 'composers' in result_final and 'people' in result_final['composers']: # otherwise, a poetry-only piece
        # if the poetry is not available, this is a standalone musical piece
        #music=models.music.objects.filter((Q(title__in=result_final['titles'])|Q(ext_music_title__title__in=result_final['titles'])|Q(poetry__title__in=result_final['titles'])|Q(poetry__ext_poetry_title__in=result_final['titles']))&(Q(composers__in=result['composers'])|(Q(composers=None)&Q(recording=recording)))).distinct()
        # if some composers have standalone music with some title and poetry-asociated music for poetry with the same title - should we merge these
        # music pieces inpo one poetry-associated piece?
        # I think not, because there are few cases when composer has music for different poetry pieces with same titles
        # in such a case, standalone music with same title will be attached to the first poetry found by this module, which is a questionable behaviour
        # so, if we have poetry - we select music by poetry key, if we don't - we select by title
        if poetry is not None:
            music=models.music.objects.filter(Q(poetry=poetry)&(Q(composers__in=[person for person in result_final['composers']['people'] if type(person) is int])|Q(ext_unknown_name__name__in=[person for person in result_final['composers']['people'] if type(person) is unicode]))).distinct()
        else:
            music=models.music.objects.filter((Q(poetry=None)&(Q(title__in=recording_titles(recording))|Q(recording__ext_recording_link__title__in=recording_titles(recording))))&(Q(composers__in=[person for person in result_final['composers']['people'] if type(person) is int])|Q(ext_unknown_name__name__in=[person for person in result_final['composers']['people'] if type(person) is unicode]))).distinct()
        if (recording.music is not None and recording.music not in music) or not merge_possible(music):
            print('Error: cannot merge music results with data already present in the database')
            print(music)
        else:
            if len(music)==0:
                # use inline if here to set either poetry key, if poetry is available, or title, if not
                # should we have empty title set to '' or to None (NULL)?
                music=models.music.objects.create(poetry=(poetry if poetry is not None else None), title=(recording_titles(recording)[0] if poetry is None else ''))
                print('Info: music created, id='+str(music.id))
            elif len(music)==1:
                music=music[0]
                print('Info: music already exists, id='+str(music.id))
            elif len(music)>1:
                music=merge(music)
                print('Info: multiple music pieces merged, id='+str(music.id))
            # composers
            for person in result_final['composers']['people']:
                if type(person) is int:
                    music.composers.add(person)
                elif type(person) is unicode:
                    name,created=models.ext_unknown_name.objects.get_or_create(name=person)
                    name.music.add(music)
            for person in result_final['composers']['people_filtered']:
                if type(person) is int:
                    music.composers.remove(person)
                elif type(person) is unicode:
                    try: name=music.ext_unknown_name_set.get(name=person)
                    except: pass
                    else: name.music.remove(music)
            # relation
            recording.music=music
            recording.save()
            # title
            if music.poetry is None: music.title=piece_titles(music)[0]
            music.save()
    # finish him!
    recording.save()
    return True

def relations(arg=None):
    if arg==None: recordings=models.recording.objects.filter(music=None, poetry=None)
    elif arg.isdigit():
        recordings=models.recording.objects.filter(id=int(arg))
        if len(recordgings)==0:
            print('Error: int argument is not a valid id')
    else:
        recordings=models.recording.objects.filter(href=arg)
        if len(recordings)==0:
            # retry with arg as a person page URL
            try: recordings=models.ext_person_link.objects.get(href=arg).recordings.all()
            except: print('Error: string argument is neither a recording nor a person webpage URL')
    count=recordings.count()
    counter=1
    for recording in recordings:
        print(str(counter)+'/'+str(count)+': '+recording.href)
        import_recording_relations(recording)
        counter+=1
    return

from django.core.management.base import BaseCommand
class Command(BaseCommand):
    def handle(self, *args, **options):
        if len(args)>0:
            relations(args[0])
        else:
            relations()

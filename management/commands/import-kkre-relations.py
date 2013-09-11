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
def merge_sets(result_array, keys):
    merged=[]
    for result in result_array:
        for key in keys:
            if key in result['sets']:
                merged+=result['sets'][key]
    return merged

# instrumental case to name case
def name_ins(name):
    return name

# attempt building relations for a given recording
def build_relations(recording):
    links=models.ext_recording_link.objects.filter(recording=recording)
    result_array=[]
    # TODO not shure if it's really good to separate reference and final results
    result_final=result_reference={'poets':[], 'composers':[], 'performers':[]}
    # first pass: form initial sets from description strings in a straightforward way; find reference sets, if possible
    for link in links:
        print(link.href.href+': "'+link.title+'" '+link.description)
        # if there are linebreaks in the title string, we have a problem
        if '\n' in link.title:
            print('Error: title contains newlines')
            return False
        result={'strings':{}, 'sets':{}, 'flags':{}}
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
                result['strings']['authors']=description[0][0]
                if len(description)>=2:
                    if type(description[1]) is unicode:
                        result['strings']['performers']=description[1]
                    else:
                        print('Error: description string parse error 2')
                        continue
                # if doesn't - ok, we don't have performers here
            # otherwise, it should be a string of performers
            elif type(description[0]) is unicode:
                result['strings']['performers']=description[0]
            else:
                print('Error: description string parse error 3')
                continue
        else:
            # empty description, but we can still use subjects list
            print('Warning: empty description')
        # now we must have strings to build sets
        # if possible, split authors into poets and composers
        if 'authors' in result['strings']:
            result['strings']['authors']=result['strings']['authors'].split(' - ')
            if len(result['strings']['authors'])==1:
                result['strings']['authors']=result['strings']['authors'][0]
            elif len(result['strings']['authors'])==2:
                result['strings']['composers']=result['strings']['authors'][0]
                result['strings']['poets']=result['strings']['authors'][1]
                result['strings'].pop('authors')
            else:
                # something wrong
                print('Error: bad authors substring')
                break
        # split strings into names
        for key in ['authors', 'poets', 'composers', 'performers']:
            if key in result['strings']:
                # incomplete strings: if a string begins with 'with ...', it means its set must be completed with people from page subjects set,
                # and people names in this string are given in instrumental case
                result['flags'][key]={}
                result['flags'][key]['incomplete']=False
                for prefix in [u'с ', u'c', u'со ', u'вместе с ']:
                    if result['strings'][key].startswith(prefix):
                        result['flags'][key]['incomplete']=True
                        result['strings'][key]=result['strings'][key][len(prefix):]
                        # convert cases after name split
                        break
                # name list dividers
                result['strings'][key]=result['strings'][key].replace(',', ';')
                # in certain contexts 'и' is not a divider
                # e. g. 'Хор ВР и ЦТ'
                result['strings'][key]=result['strings'][key].replace(u' и ', ';')
                # in certain contexts '/' is not a divider
                # e. g. 'х/ф', 'п/у'
                # let's assume all of them have '<start_of_line_or_whitespace><single_character>/<single_character><whitespace_or_end_of_line>' pattern,
                # and any '/' out ot this pattern to be a name divider
                # I failed to write a 'start_(end)_of_line or whitespace' expression in a regexp, so I add border whitespaces which will be trimmed later
                result['strings'][key]=' '+result['strings'][key]+' '
                result['strings'][key]=re.sub('(?<!\s\S)/', ';', re.sub('/(?!\S\s)', ';', result['strings'][key]))
                # split list into names
                result['sets'][key]=result['strings'][key].split(';')
                # clean up a little
                result['sets'][key]=[re.sub('\.\s*', '. ', name).strip() for name in result['sets'][key]]
                # name case convertion
                if result['flags'][key]['incomplete']:
                    result['sets'][key]=[name_ins(name) for name in result['sets'][key]]
        # now we must have sets of clean names
        # take reference sets
        for key in ['poets', 'composers', 'performers']:
            if key in result['sets'] and not result['flags'][key]['incomplete']:
                result_reference[key]=list(set(result_reference[key]+result['sets'][key]))
        # add subjects set
        result['sets']['subjects']=[]
        for person in link.href.people.all():
            result['sets']['subjects'].append(person.id)
        # push result into res_arr
        result_array.append(result)
    # we can have a music- or poetry-only piece
    # conditions: no (composers - poets) splittable authors string, all authors strings similar
    # nope, we won't check this, our heuristics will simply leave empty poets or composers set in this case, which is much easier to check
    # second pass: clarify results using heuristics
    for result in result_array:
        # TODO temporary
        res=result['sets']
        # if 'subjects' contains multiple people - drop irrelevant ones
        if len(res['subjects'])>1:
            for person in list(res['subjects']):
                # check if this person can be seen in descriptions of other links, otherwise drop it
                if not person_in_set(person, merge_sets(result_array, ['authors', 'poets', 'composers', 'performers'])):
                    print('Warning: multiple subjects verification: '+str(person)+' doesn\'t appear in other sets, will be ignored')
                    res['subjects'].remove(person)
            # what if we have an empty list after this?
        # if we have 'authors' set - guess whether it's 'poets' or 'composers'
        if 'authors' in res:
            # if we have 'poets' and 'composers' reference sets - compare it with them
            if 'poets' in result_reference and 'composers' in result_reference and match_sets(res['authors'], result_reference['poets'])>match_sets(res['authors'], result_reference['composers']):
                res['poets']=res.pop('authors')
                result['flags']['poets']=result['flags'].pop('authors')
            elif 'poets' in result_reference and 'composers' in result_reference and match_sets(res['authors'], result_reference['poets'])<match_sets(res['authors'], result_reference['composers']):
                res['composers']=res.pop('authors')
                result['flags']['composers']=result['flags'].pop('authors')
            # try to guess using categories
            elif all_in_category(res['authors'], 'poets') and not all_in_category(res['authors'], 'composers'):
                # if an authors list is a list of people from webpage subject list - this likely means they are poets and composers simultaneously
                # so we place them into a set they shouldn't normally be in, and other one will be populated later by same people by category match
                if all_in_set(res['authors'], res['subjects']):
                    res['composers']=res.pop('authors')    
                    result['flags']['composers']=result['flags'].pop('authors')
                else:
                    res['poets']=res.pop('authors')
                    result['flags']['poets']=result['flags'].pop('authors')
            elif all_in_category(res['authors'], 'composers') and not all_in_category(res['authors'], 'poets'):
                if all_in_set(res['authors'], res['subjects']):
                    res['poets']=res.pop('authors')
                    result['flags']['poets']=result['flags'].pop('authors')
                else:
                    res['composers']=res.pop('authors')
                    result['flags']['composers']=result['flags'].pop('authors')
            # try to guess as the opposite to subjects
            elif all_in_category(res['subjects'], 'poets') and not all_in_category(res['subjects'], 'composers'):
                res['composers']=res.pop('authors')
                result['flags']['composers']=result['flags'].pop('authors')
            elif all_in_category(res['subjects'], 'composers') and not all_in_category(res['subjects'], 'poets'):
                res['poets']=res.pop('authors')
                result['flags']['poets']=result['flags'].pop('authors')
            else:
                # warning flag
                print('Warning: failed to determine authors category')
        # now, if we don't have a required set - it can be empty either because it contains self,
        # or because it's text is placed out of the link description on the page (e. g. single 'performers' string for multiple links)
        # besides, existing set can require completion from 'subjects' ('with... ')
        for key in result_reference:
            if key not in res or result['flags'][key]['incomplete']:
                if key not in res: res[key]=[]
                # try populating the set with people from 'subjects'
                for person in res['subjects']:
                    # if subject person is in matching category - add it
                    if person_in_category(person, key):
                        res[key].append(person)
        # what if we failed to place subjects? - warning flag
        # TODO temp
        result['sets']=res
    # now we can form a final result
    for result in result_array:
        for key in result_reference.keys():
            result_final[key]=list(set(result_final[key]+result['sets'][key]))
    # if poets or composers sets are empty - it's a music-only or a text-only piece
    # warning: this may also mean that poets or composers string is placed out-of-description for this recording on all webpages,
    #  and poets or composers do not have their own pages
    for key in ['poets', 'composers']:
        if len(result_final[key])==0:
            print('Warning: '+key+' set is empty, removed')
            result_final.pop(key)
    # resolve names
    # we cannot remove elements in-place, because changing the list breaks iteration
    for key in result_final.keys():
        for person in list(result_final[key]):
            if type(person) is unicode:
                ids=name_to_id(person, key)
                if len(ids)==1:
                    # one more safety measure: any recognized person must be either in category-matching list, or be present in one of the 'subjects' lists
                    if person_in_category(ids[0], key) or ids[0] in merge_sets(result_array, ['subjects']):
                        result_final[key].append(ids[0])
                    else:
                        print('Warning: name "'+person+'" resolved, but is neither in appropriate category nor in subjects lists, ignored')
                # unknown name
                elif len(ids)==0:
                    # mistyped name?
                    print('Warning: unknown name "'+person+'"')
                # ambigious name
                elif len(ids)>1:
                    print('Warning: ambigious name "'+person+'"')
                result_final[key].remove(person)
        # deduplicate, possibly using number duplicates to rate the reliability of a relation guess
        result_final[key]=list(set(result_final[key]))
    print(result_final)
    return result_final

# export relations into database objects
# relations_data object structure:
# category(poets,composers,performers)/
#  ids/: list of database ids of person objects
#  names/: list of names that failed
#   we have ext_failed_names table to track them for statistics and ext_failed_names_<category> to track their relations with recording/music/poetry objects
#   this allows us to see which names cause most problems, automatically re-run relations import as we create person objects for them,
#   meanwhile displaying them in lists on webpages like known people names
# titles/
# meta/
def import_relations(result_final):
    if result_final==False: return False
    return
    # recording: if we have performers, then even if we will fail with poetry and music, it will still show up on performers pages as an 'Unknown Piece'
    if 'performers' in result_final:
        for person in result_final['performers']:
            recording.performers.add(person)
    # title
    # recording may have different titles on different pages
    # poetry
    if 'poets' in result_final: # otherwise, a music-only piece
        # recording can already have an associated poetry piece
        # there can also be other poetry pieces with same title and poets
        #if recording.poetry==None or is_compatible(recording.poetry, result):
        # if existing poetry incoroporates result - we shouldn't do anything
        #elif is_superset(recording.poetry, result)
        #
        if len(result_final['poets'])>0:
            # here we filter poetry objects that have given title and any of given poets
            poetry=models.poetry.objects.filter(title=title, poets__in=result['poets']).distinct()
            if not t: # if no results - create, add poets and use
                poetry=models.poetry.objects.create(title=title)
                for person in result['poets']: poetry.poets.add(person)
                print('poetry: "'+poetry.title+'" created')
            elif len(poetry)==1: # if one - add missing poets (if any) and use
                poetry=poetry[0]
                for person in result['poets']: poetry.poets.add(person)
                print('poetry: "'+poetry.title+'" already exists')
            elif len(poetry)>1: # if multiple - join, add missing poets (if any) and use
                #for t_i in t[1:]:
                #    #
                print('poetry: multiple "'+poetry[0].title.encode+'" have to be joined')
                return
            recording.poetry=poetry
        else: # poetry assumed, but no poets in list
            # we can create a poetry without poets, which will mean it's a poetry by an unknown poet
            # the problem is that when we'll retry with a succesfully obtained list of poets, we will have to find this poetry and merge with it,
            #  but not with some other unauthored poetry with same title - can we? yes, we can, because it will be attached to the recording
            #  that we will be retrying for
            # another problem is that for multiple recordings with common unauthored poetry we will have one poetry object for each recording,
            #  (because it will be too complicated to take care of information that can help us guess that they must be a single object),
            #  if they have a common music piece by same composer, there will be one music object per poetry, too; we will have to join music as well
            pass
    # music
    if 'composers' in result_final: # otherwise, a poetry-only piece
        if len(result_final['composers'])>0:
            # it is possible that we have no poets -> no poetry -> this is a standalone musical piece
            # in this case, t is not available
            music=models.music.objects.filter(poetry=t, composers__in=result['composer']).distinct()
            if not m:
                music=models.music.objects.create(poetry=t)
                for person in result['composer']: music.composers.add(person)
                print('music: "'+music.poetry.title.encode('utf8')+'" created')
            elif len(music)==1:
                music=music[0]
                for person in result['composer']: music.composers.add(p)
                print('music: "'+music.poetry.title.encode('utf8')+'" already exists')
            elif len(music)>1:
                print('music: multiple "'+music[0].poetry.title.encode('utf8')+'" have to be joined')
                return
            recording.music=music
        else:
            pass
    # finish him!
    recording.save()
    return True

def relations(arg=None):
    if arg==None: recordings=models.recording.objects.filter(music=None, poetry=None)
    elif arg.isdigit():
        recordings=models.recording.objects.filter(id=int(arg))
        if len(recordgings)==0:
            print('Error: argument is not a valid id')
    else:
        recordings=models.recording.objects.filter(href=arg)
        if len(recordings)==0:
            # retry with arg as a person page URL
            recordings=models.ext_person_link.objects.get(href=arg).recordings.all()
            if len(recordings)==0:
                print('Error: argument is neither a recording URL nor a person webpage URL')
                return
    count=recordings.count()
    counter=1
    for recording in recordings:
        print(str(counter)+'/'+str(count)+': '+recording.href)
        import_relations(build_relations(recording))
        counter+=1
    return

from django.core.management.base import BaseCommand
class Command(BaseCommand):
    def handle(self, *args, **options):
        if len(args)>0:
            relations(args[0])
        else:
            relations()

#!/usr/bin/python
# coding=UTF-8

import re

# function to select most relevant normal form from mystem output
def mystem(word, filter_strict, filter_loose=[]):
    debug = False
    mystem = './mystem'
    from subprocess import Popen, PIPE
    # TODO: escape word
    stem_result = Popen([mystem, '-e utf-8', '-i', '-l'], stdin=PIPE, stdout=PIPE, stderr=PIPE).communicate(word.encode('utf-8'))[0].decode('utf8')
    # get stem group in {}
    # there should be only one such group
    stem_result = stem_result[1:-1]
    if '{' in stem_result or '}' in stem_result:
        return
    #print stem_result
    stem_result_dict = {}
    word = ''
    # split by |
    import re
    for word_form in stem_result.split('|'):
        # get current word as beginning of the word_form line consisting of cyrillic letters only
        form = re.sub(u'^[а-яА-Я]+', '', word_form)
        # cut form from end of  word_form to get word
        if word_form[:-len(form)]: word = word_form[:-len(form)]
        stem_result_dict[form] = word
    # now we have a dict of variants, can filter
    if debug:
        print 'Initial dict:'
        for key in stem_result_dict:
            print key + ': ' + stem_result_dict[key]
    # common situation: last name ends with 'ий'/'ая' and is treated as an ajective
    # if 'S', 'фам' is wanted, but result contains only 'A's:
    #  delete 'S' from filters
    #  if now we have one matching word with 'жен' or 'муж'
    #   if it ends with 'ий' and has 'жен' - change 'ий' to 'ая', if 'муж' - leave as is
    ajective_last_name_dirty_hack = False
    if u'S' in filter_strict and u'фам' in filter_loose and not False in [True if u'A' in stem_result_form else False for stem_result_form in stem_result_dict.keys()]:
        filter_strict.remove(u'S')
        filter_strict.append(u'A')
        ajective_last_name_dirty_hack = True
    # delete all stem_result items which do not match strict filter
    for criteria in filter_strict:
        for stem_result_form in stem_result_dict.keys():
            if criteria not in stem_result_form:
                stem_result_dict.pop(stem_result_form)
    if debug:
        print 'Dict after strict filtering:'
        for key in stem_result_dict:
            print key + ': ' + stem_result_dict[key]
    # back to our dirty hack
    if ajective_last_name_dirty_hack:
        # delete results with 'сред'
        for stem_result_form in stem_result_dict.keys():
            if u'сред' in stem_result_form:
                stem_result_dict.pop(stem_result_form)
        if len(stem_result_dict) == 1 and stem_result_dict[stem_result_dict.keys()[0]].endswith(u'ий'):
            if u'жен' in stem_result_dict.keys()[0]:
                stem_result_dict[stem_result_dict.keys()[0]] = stem_result_dict[stem_result_dict.keys()[0]][:-2] + u'ая'
            return stem_result_dict[stem_result_dict.keys()[0]], stem_result_dict.keys()[0]
        else: return
    # if multiple items, and only part of them do not match loose filter - delete those that don't
    for criteria in filter_loose:
        for stem_result_form in stem_result_dict.keys():
            if len(stem_result_dict) > 1:
                if criteria not in stem_result_form:
                    stem_result_dict.pop(stem_result_form)
            else: break
        if len(stem_result_dict) <= 1: break
    # if one and only one remaining form - return it with its grammar tags
    # or... what if many but with same word?
    if debug:
        print 'Dict after loose filtering:'
        for key in stem_result_dict:
            print key + ': ' + stem_result_dict[key]
    if len(stem_result_dict) > 0:
        stem_result_word_final = stem_result_dict[stem_result_dict.keys()[0]]
        stem_result_dict_final = []
        for stem_result_form in stem_result_dict.keys():
            if stem_result_dict[stem_result_form] != stem_result_word_final: return
            if stem_result_form not in stem_result_dict_final: stem_result_dict_final.append(stem_result_form)
        return stem_result_word_final, stem_result_dict_final
    return

def name_instrumental_to_nominative(name):
    # typical cases:
    # Name Surname
    if re.match(u'^[А-ЯЁ][а-яё]+\s[А-ЯЁ][а-яё]+$', name):
        try:
            first_name, grammar = mystem(name.split(' ')[0], [u'твор', u'S'], [u'имя', u'ед'])
            last_name, grammar = mystem(name.split(' ')[1], [u'твор', u'S'], [u'фам', u'ед'])
            return first_name[0].upper() + first_name[1:] + ' ' + last_name[0].upper() + last_name[1:]
        except: return
    # N. Surname
    elif re.match(u'^[А-ЯЁ]\.\s[А-ЯЁ][а-яё]+$', name):
        try:
            last_name, grammar = mystem(name.split(' ')[1], [u'твор', u'S'], [u'фам', u'ед'])
            return name.split(' ')[0] + ' ' + last_name[0].upper() + last_name[1:]
        except:
            return
    # Group title, starts with abbriveature
    elif re.match(u'^[А-ЯЁ]+\s', name) or re.match(u'^[А-ЯЁ]+$', name):
        return name
    return


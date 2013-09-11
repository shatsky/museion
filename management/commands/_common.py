#!/usr/bin/python
# coding=UTF-8

# current problems
# name fixes and case handling

import os
import re
import pycurl
import json
from pprint import pprint

import lxml.html
from bs4 import UnicodeDammit

from xml.dom.pulldom import SAX2DOM
import lxml.sax

from djmuslib.models import *
from django.db.models import Q

basedir=os.path.dirname(__file__)
mirrordir='./mirror/'
work_offline=True

# function downloads or updates file from remote address
# and returns local path (which is just the address without the protocol handler)
# it does not write a file if server returns an error
# it returns false if there is no file
def fetch(addr):
    print('fetching '+addr)
    if addr.endswith('/'): addr+='index.htm'
    path=mirrordir+addr.replace('http://', '')
    if work_offline==True:
        if os.path.exists(path):
            #print('offline')
            return path
        else:
            return False
    else:
        #download=False
        curl=pycurl.Curl()
        #curl.setopt(pycurl.URL, addr.encode('ascii'))
        #curl.setopt(pycurl.HEADER, True)
        #curl.setopt(pycurl.NOBODY, True)
        #curl.setopt(pycurl.OPT_FILETIME, True)
        #curl.perform()
        #remote_timestamp=curl.getinfo(pycurl.INFO_FILETIME)
        #curl.reset()
        #if os.path.exists(path): # if local file exists - compare mtime with remote
        #    if os.stat(path).st_mtime<remote_timestamp: # file needs to be updated
        #        download=True
        #    else: # file is up to date
        #        return path
        #else: # file needs to be downloaded anyway
        #    download=True
        download=True
        if download==True:
            curl.setopt(pycurl.URL, addr.encode('ascii'))
            curl.setopt(pycurl.OPT_FILETIME, True)
            if not os.path.exists(os.path.dirname(path)): os.makedirs(os.path.dirname(path))
            file = open(path, "wb")
            curl.setopt(pycurl.WRITEDATA, file)
            curl.perform()
            file.close()
            if False: # handle download errors
                if(os.path.exists(path)): # if download failed - still check if there is a local file, if yes - return path
                    return path # this is WRONG because we there always IS a local file after fopen() call
                else: # otherwise, return false
                    return False
            else: # if download succeeded - preserve timestamp
                print('applying timestamp')
                remote_timestamp=curl.getinfo(pycurl.INFO_FILETIME)
                pprint(remote_timestamp)
                pprint(path)
                os.utime(path, tuple([remote_timestamp, remote_timestamp]))
            curl.close()
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

def insens(string):
    string=string.lower()
    string=string.replace(u'ё', u'е') # ё/е insensetive
    return string

def gender_from_name(name):
    # Gender from third name endings: 'вич', 'мич', 'ьич', 'оглы' - male, 'вна', 'чна' - female
    if name[-3:] in [u'вич', u'мич', u'ьич'] or name[-4:]==u'оглы': return 'male'
    elif name[-3:] in [u'вна', u'чна']: return 'female'
    else: return ''


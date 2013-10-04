#!/usr/bin/python
# coding=UTF-8

# make string case and ё/е insensetive
def str_insens(string):
    return string.lower().replace(u'ё', u'е')

# guess gender from name
def gender_from_name(name):
    # Gender from third name endings: 'вич', 'мич', 'ьич', 'оглы' - male, 'вна', 'чна' - female
    if name[-3:] in [u'вич', u'мич', u'ьич'] or name[-4:] == u'оглы': return 'male'
    elif name[-3:] in [u'вна', u'чна']: return 'female'
    else: return ''

# function to mirror file from remote URL or return a local copy if it already exists
# returns the local path for the mirrored file (which is just the address without the protocol handler) 
#  or False if download failed and there's no existing mirrored copy
# behaviour depends on 2 env variables:
#  MIRROR_DIR=[path] - path to directory to be used as a root for mirrored files hierarchy (./mirror by default)
#  REDOWNLOAD=[0|1] - wether to check for a newer remote version of alredy mirrored files and redownload if available,
#   or just return the path (default)
def mirror_file(addr):
    import os
    mirror_dir = os.getenv('MIRROR_DIR', './mirror/')
    if not os.path.exists(mirror_dir): os.makedirs(mirror_dir)
    print('Info: mirrored copy of "' + addr + '" requested')
    if addr.endswith('/'): addr += 'index.htm'
    path = mirror_dir + addr.replace('http://', '')
    # Attempt downloading file only if it doesn't exist or REDOWNLOAD env var is true
    if not (os.getenv('REDOWNLOAD', '0') == '0' and os.path.exists(path)):
        import pycurl
        curl = pycurl.Curl()
        # if file exists - first, make head-only request
        # make shure answer is OK and remote file is newer than local copy
        if os.path.exists(path):
            curl.setopt(pycurl.URL, addr.encode('ascii'))
            curl.setopt(pycurl.HEADER, True)
            curl.setopt(pycurl.NOBODY, True)
            curl.setopt(pycurl.OPT_FILETIME, True)
            curl.perform()
            remote_timestamp = curl.getinfo(pycurl.INFO_FILETIME)
            if not os.stat(path).st_mtime<remote_timestamp: # file doesn't need to be updated
                return path
            curl.reset()
        curl.setopt(pycurl.URL, addr.encode('ascii'))
        curl.setopt(pycurl.OPT_FILETIME, True)
        curl.setopt(pycurl.FAILONERROR, True)
        # get available temporary filename in the mirror directory
        tmp_file = os.path.join(mirror_dir, 'tmp')
        counter = 0
        while os.path.exists(tmp_file):
            tmp_file = os.path.join(mirror_dir, 'tmp_'+str(counter))
            counter += 1
        file = open(tmp_file, "wb")
        curl.setopt(pycurl.WRITEDATA, file)
        try: curl.perform()
        except pycurl.error, error:
            print('Error: ' + error[1])
            file.close()
            os.remove(tmp_file)
            if os.path.exists(path): return path # there still can be a previously existing local copy
            return False # but if not - we can't do anything else, give up
        else: # if download succeeded - move temporerary file and apply timestamp
            file.close()
            if not os.path.exists(os.path.dirname(path)): os.makedirs(os.path.dirname(path))
            os.rename(tmp_file, path)
            print('Info: saved as "' + path + '"')
            remote_timestamp = curl.getinfo(pycurl.INFO_FILETIME)
            print('Info: applying timestamp ' + str(remote_timestamp))
            os.utime(path, tuple([remote_timestamp, remote_timestamp]))                
        curl.close() # what if we don't close() before return?
    return path


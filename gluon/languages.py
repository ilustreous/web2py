#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
This file is part of web2py Web Framework (Copyrighted, 2007)
Developed by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: GPL v2
"""

import sys
import os
import re
import cgi
from fileutils import listdir

__all__ = ['translator', 'findT', 'update_all_languages']

# pattern to find T(bla bla bla) expressions

PY_STRING_LITERAL_RE = r'(?<=[^\w]T\()(?P<name>'\
     + r"[uU]?[rR]?(?:'''(?:[^']|'{1,2}(?!'))*''')|"\
     + r"(?:'(?:[^'\\]|\\.)*')|" + r'(?:"""(?:[^"]|"{1,2}(?!"))*""")|'\
     + r'(?:"(?:[^"\\]|\\.)*"))'

regex_translate = re.compile(PY_STRING_LITERAL_RE, re.DOTALL)

# patter for a valid accept_language

regex_language = \
    re.compile('^[a-zA-Z]{2}(\-[a-zA-Z]{2})?(\-[a-zA-Z]+)?$')

def read_dict(filename):
    return eval(open(filename, 'r').read().replace('\r\n','\n'))

class lazyT(object):

    """ 
    never to be called explicitly, returned by translator.__call__ 
    """

    def __init__(
        self,
        message,
        symbols={},
        self_t=None,
        ):
        self.m = message
        self.s = symbols
        self.t = self_t

    def __str__(self):
        m = self.m
        if self.t and self.t.has_key(m):
            m = self.t[m]
        if self.s or self.s == 0:
            return m % self.s
        else:
            return m

    def xml(self):
        return cgi.escape(str(self))


class translator(object):

    """ 
    this class is intantiated once in gluon/main.py as the T object 

    T.force(None) # turns off translation
    T.force('fr, it') # forces web2py to translate using fr.py or it.py

    T(\"Hello World\") # translates \"Hello World\" using the selected file

    notice 1: there is no need to force since, by default, T uses accept_langauge
    to determine a translation file. 

    notice 2: en and en-en are considered different languages!
    """

    def __init__(self, request):
        self.folder = request.folder
        self.current_languages = []
        self.http_accept_language = request.env.http_accept_language
        self.forced = False

    def force(self, languages=None):
        self.forced = True
        if languages:
            if isinstance(languages, (str, unicode)):
                accept_languages = languages.split(';')
                languages = []
                for al in accept_languages:
                    languages += al.split(',')
            for language in languages:
                language = language.strip()
                if language in self.current_languages:
                    break
                if not regex_language.match(language):
                    continue
                filename = os.path.join(self.folder, 'languages/',
                        '%s.py' % language)
                if os.path.exists(filename):
                    self.accepted_language = language
                    self.t = read_dict(filename)
                    return
        self.t = None  # ## no langauge by default

    def __call__(self, message, symbols={}):
        if not self.forced:
            self.force(languages=self.http_accept_language)
        return lazyT(message, symbols, self.t)


def findT(application_path, language='en-us'):
    """ 
    must be run by the admin app 
    """

    path = application_path
    try:
        sentences = read_dict(os.path.join(path, 'languages', '%s.py' 
                              % language))
    except:
        sentences = {}
    mp = os.path.join(path, 'models')
    cp = os.path.join(path, 'controllers')
    vp = os.path.join(path, 'views')
    for file in listdir(mp, '.+\.py', 0) + listdir(cp, '.+\.py', 0)\
         + listdir(vp, '.+\.html', 0):
        data = open(file, 'r').read()
        items = regex_translate.findall(data)
        for item in items:
            try:
                msg = eval(item)
                if msg and not sentences.has_key(msg):
                    sentences[msg] = '*** %s' % msg
            except:
                pass
    keys = sorted(sentences)
    file = open(os.path.join(path, 'languages', '%s.py' % language), 'w')
    file.write('{\n')
    for key in keys:
        file.write('%s:%s,\n' % (repr(key), repr(str(sentences[key]))))
    file.write('}\n')
    file.close()


def update_all_languages(application_path):
    path = os.path.join(application_path, 'languages/')
    for language in listdir(path, '.+'):
        findT(application_path, language[:-3])



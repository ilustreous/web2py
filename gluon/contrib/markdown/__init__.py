from markdown2 import *
from gluon.html import XML

def WIKI(text,**attributes):
    if not text: test=''
    if attributes.has_key('extras'): extras=attributes['extras']
    else: extras=None
    return XML(markdown(text,extras=extras,safe_mode='escape').encode('utf8','xmlcharrefreplace'),**attributes)
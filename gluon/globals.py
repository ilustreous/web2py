"""
This file is part of web2py Web Framework (Copyrighted, 2007)
Developed by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: GPL v2
"""

from storage import Storage
from compileapp import run_view_in
import sys, cPickle, cgi, cStringIO, thread, time, shelve

__all__=['Request','Response','Session']

class Request(Storage):
    """
    defines the request object and the default values of its members
    """
    def __init__(self):
        self.env=Storage()
        self.cookies=Storage()
        self.get_vars=Storage()
        self.post_vars=Storage()
        self.vars=Storage()
        self.application=None
        self.function=None        
        self.args=[]
    pass

class Response(Storage):
    """
    defines the response object and the default values of its members
    response.write(....) can be used to write in the output html
    """
    def __init__(self):
        self.status=200
        self.headers=Storage()
        self.body=cStringIO.StringIO()
        self.session_id=None
        self.cookies=Storage()
        self.keywords=''     # used by the default view layout
        self.description=''  # used by the default view layout
        self.flash=None      # used by the default view layout
        self.menu=None       # used by the default view layout     
        self._vars=None
        self._view_environment=None
    def write(self,data,escape=True):
        if not escape: self.body.write(str(data))
        else: 
            try: self.body.write(data.xml())
            except AttributeError: self.body.write(cgi.escape(str(data)))
    def render(self,*a,**b):
        if len(a)>1 or (len(a)==1 and not hasattr(a,'items')): 
            raise SyntaxError        
        self._vars=a[0] if len(a) else {}
        for key,value in b.items(): self._vars[key]=value
        for key,value in self._vars.items(): self._view_environment[key]=value
        run_view_in(self._view_environment)
        self.body=self.body.getvalue()
        return self.body

class Session(Storage): 
    """
    defines the session object and the default values of its members (None)
    """
    pass


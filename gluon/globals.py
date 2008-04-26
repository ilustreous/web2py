"""
This file is part of web2py Web Framework (Copyrighted, 2007)
Developed by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: GPL v2
"""

from storage import Storage
from compileapp import run_view_in
from streamer import streamer, stream_file_or_304_or_206
from xmlrpc import handler
from contenttype import contenttype
from html import xmlescape
import sys, cPickle, cStringIO, thread, time, shelve, os, stat

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
        else: self.body.write(xmlescape(data))
    def render(self,*a,**b):
        if len(a)>1 or (len(a)==1 and not hasattr(a[0],'items')):
            raise SyntaxError        
        if len(a): self._vars=a[0] 
        else: self._vars={}
        for key,value in b.items(): self._vars[key]=value
        for key,value in self._vars.items(): self._view_environment[key]=value
        run_view_in(self._view_environment)
        self.body=self.body.getvalue()
        return self.body
    def stream(self,stream,chunk_size=10**6,request=None):
        """
        if a controller function
        > return response.stream(file,100)
        the file content will be streamed at 100 bytes at the time
        """
        if isinstance(stream,str):
            stream_file_or_304_or_206(stream,request=request,chunk_size=chunk_size,headers=self.headers)
        ### the following is for backward compatibility
        if hasattr(stream,'name'): filename=stream.name
        else: filename=None
        keys=[item.lower() for item in self.headers.keys()]
        if filename and not 'content-type' in keys:
             self.headers['Content-Type']=contenttype(filename)
        if filename and not 'content-length' in keys:
             self.headers['Content-Length']=os.stat(filename)[stat.ST_SIZE]
        self.body=streamer(stream,chunk_size)
        return self.body
    def xmlrpc(self,request,methods):
        """
        assuming: 
        > def add(a,b): return a+b
        if a controller function "func" 
        > return response.xmlrpc(request,[add])
        the controller will be able to handle xmlrpc requests for 
        the add function. Example:
        > import xmlrpclib
        > connection=xmlrpclib.ServerProxy('http://hostname/app/contr/func')
        > print connection.add(3,4)        
        """
        return handler(request,self,methods)

class Session(Storage): 
    """
    defines the session object and the default values of its members (None)
    """
    pass


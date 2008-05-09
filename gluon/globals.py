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
from http import HTTP
import sys, cPickle, cStringIO, thread, time, shelve, os, stat, uuid

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
        self.body=handler(request,self,methods)
        return self.body

class Session(Storage): 
    """
    defines the session object and the default values of its members (None)
    """
    def get_from(self,field,request,master=None):
        if not master==request.application: master=request.application
        session_id_name='session_id_%s'%master
        try:
             key=request.cookies[session_id_name].value
             session_id,key1=key.split(':')
             if session_id=='0': raise Exception
             rows=field._table._db(field._table.id==session_id).select()
             if len(rows)==0: raise Exception
             key2,session=cPickle.loads(rows[0][field.name])
             if key1!=key2: raise Exception
        except Exception, e:
             session_id,key1,session=None,str(uuid.uuid4()),{}
        self._dbfield_and_key=(session_id_name,field,session_id,key1)
        self.update(session)
    def put_in(self,response):
        if self._dbfield_and_key:
            session_id_name,field,session_id,key1=self._dbfield_and_key
            del self._dbfield_and_key
            dd={field.name:cPickle.dumps((key1,dict(self)))}
            if session_id:
                field._table._db(field._table.id==session_id).update(**dd)
            else:
                session_id=field._table.insert(**dd)
            response.cookies[session_id_name]='%s:%s' % (session_id,key1)
            response.cookies[session_id_name]['path']="/"
            return True
        return False


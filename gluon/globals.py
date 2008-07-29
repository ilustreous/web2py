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
from sql import SQLField
from fileutils import up
import portalocker
import sys, cPickle, cStringIO, thread, time, shelve, os, stat, uuid
import datetime,re,random
now=datetime.datetime.today()

regex_session_id=re.compile('([0-9:]+\.)+[0-9]+')

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
    response.write(   ) can be used to write in the output html
    """
    def __init__(self):
        self.status=200
        self.headers=Storage()
        self.body=cStringIO.StringIO()
        self.session_id=None
        self.cookies=Storage()
        self.postprocessing=[]
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
        if len(a)>2: raise SyntaxError
        elif len(a)==2: view,self._vars=a[0],a[1]
        elif len(a)==1 and isinstance(a[0],str): view,self._vars=a[0],{}
        elif len(a)==1 and isinstance(a[0],dict): view,self._vars=None,a[0]
        else: view,self._vars=None,{}
        self._vars.update(b)
        self._view_environment.update(self._vars)
        if view:
            import cStringIO
            obody,oview=self.body,self.view
            self.body,self.view=cStringIO.StringIO(),view
            run_view_in(self._view_environment)
            page=self.body.getvalue()
            self.body,self.view=obody,oview
        else:
            run_view_in(self._view_environment)
            page=self.body.getvalue()
        return page
    """
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
    """
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
    def connect(self,request,response,db=None,tablename='web2py_session',masterapp=None):
        self._unlock(response)
        if not masterapp: masterapp=request.application
        response.session_id_name='session_id_%s'%masterapp
        if not db:
            if request.cookies.has_key(response.session_id_name):
                response.session_id=request.cookies[response.session_id_name].value
                if regex_session_id.match(response.session_id):
                     response.session_filename=os.path.join(up(request.folder),masterapp,'sessions',response.session_id)
                else: response.session_id=None
            if response.session_id:
                try:
                     response.session_file=open(response.session_filename,'rb+')
                     portalocker.lock(response.session_file,portalocker.LOCK_EX)
                     self.update(cPickle.load(response.session_file))
                     response.session_file.seek(0)
                except:
                     self._unlock(response)
                     response.session_id=None
            if not response.session_id:
                response.session_id=request.env.remote_addr+'.'+str(int(time.time()))+'.'+str(random.random())[2:]
                response.session_filename=os.path.join(up(request.folder),masterapp,'sessions',response.session_id)
                response.session_new=True
        else:
             table=db.define_table(tablename+'_'+masterapp,
                 SQLField('locked','boolean',default=False),
                 SQLField('client_ip'),
                 SQLField('created_datetime','datetime',default=now),
                 SQLField('modified_datetime','datetime'),
                 SQLField('unique_key'),
                 SQLField('session_data','text'))
             try:
                 key=request.cookies[response.session_id_name].value
                 record_id,unique_key=key.split(':')
                 if record_id=='0': raise Exception
                 rows=db(table.id==record_id).select()
                 if len(rows)==0 or rows[0].unique_key!=unique_key:
                     raise Exception, "No record"
                 #rows[0].update_record(locked=True)
                 session_data=cPickle.loads(rows[0].session_data) 
                 self.update(session_data)
             except Exception, e:
                 record_id,unique_key,session_data=None,str(uuid.uuid4()),{}
             finally:
                 response._dbtable_and_field=(response.session_id_name,table,record_id,unique_key)
                 response.session_id='%s:%s' % (record_id,unique_key)
        response.cookies[response.session_id_name]=response.session_id
        response.cookies[response.session_id_name]['path']="/"
        if self.flash: response.flash, self.flash=self.flash, None
    def secure(self):
        self._secure=True
    def forget(self):
        self._forget=True
    def _try_store_in_db(self,request,response):      
        if not response._dbtable_and_field or not response.session_id or self._forget: return
        record_id_name,table,record_id,unique_key=response._dbtable_and_field
        dd=dict(locked=False,
                client_ip=request.env.remote_addr,
                modified_datetime=now,
                session_data=cPickle.dumps(dict(self)),
                unique_key=unique_key)
        if record_id:
            table._db(table.id==record_id).update(**dd)
        else:
            record_id=table.insert(**dd)
        response.cookies[response.session_id_name]='%s:%s' % (record_id,unique_key)
        response.cookies[response.session_id_name]['path']="/"
    def _try_store_on_disk(self,request,response):        
        if response._dbtable_and_field or not response.session_id or self._forget:
            self._unlock(response)
            return
        if response.session_new:
            response.session_file=open(response.session_filename,'wb')
            portalocker.lock(response.session_file,portalocker.LOCK_EX)
        cPickle.dump(dict(self),response.session_file)
        self._unlock(response)
    def _unlock(self,response):
        if response.session_file:
            portalocker.unlock(response.session_file)
            del response.session_file

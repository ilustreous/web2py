"""
This file is part of web2py Web Framework (Copyrighted, 2007)
Developed by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: GPL v2
"""

import cgi, cStringIO, Cookie, cPickle, os
import re, copy, sys, types, time, thread
import datetime, signal, socket, stat
import tempfile
#from wsgiref.simple_server import make_server, demo_app
from random import random
from storage import Storage, load_storage, save_storage
from restricted import RestrictedError
from languages import translator
from http import HTTP, redirect
from globals import Request, Response, Session
from cache import Cache
from compileapp import run_models_in, run_controller_in, run_view_in
from fileutils import listdir, copystream
from contenttype import contenttype
from sql import SQLDB, SQLField
from sqlhtml import SQLFORM, SQLTABLE
from rewrite import rewrite
from xmlrpc import handler
from streamer import streamer
import html
import validators
import myregex
import wsgiserver
import portalocker
### contrib moduels
import contrib.simplejson
import contrib.pyrtf
import contrib.rss2
import contrib.feedparser
import contrib.markdown
import contrib.memcache

__all__=['wsgibase', 'save_password', 'appfactory', 'HttpServer']

### Security Checks: validate URL and session_id here, accept_language is validated in languages
# pattern to find valid paths in url /application/controller/...
regex_url=re.compile('(?:^$)|(?:^(\w+/?){0,3}$)|(?:^(\w+/){3}\w+(/?\.?[\w\-\.]+)*/?$)|(?:^(\w+)/static(/\.?[\w\-\.]+)*/?$)')
# patter used to validate session ids
regex_session_id=re.compile('([0-9]+\.)+[0-9]+')

error_message='<html><body><h1>Invalid request</h1></body></html>'
error_message_ticket='<html><body><h1>Internal error</h1>Ticket issued: <a href="/admin/default/ticket/%s" target="_blank">%s</a></body></html>'

working_folder=os.getcwd()

def RFC1123_DATETIME(seconds):
    return time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(seconds))

def serve_controller(request,response,session):    
    """
    this function is used to generate a dynmaic page.
    It first runs all models, then runs the function in the controller,
    and then tries to render the output using a view/template.    
    this function must run from the [applciation] folder. 
    A typical examples would be the call to the url
    /[applicaiton]/[controller]/[function] that would result in a call
    to [function]() in applications/[application]/[controller].py
    renedred by applications/[application]/[controller]/[view].html
    """
    ###################################################
    # build evnironment for controller and view
    ###################################################
    environment={}
    for key in html.__all__: environment[key]=eval('html.%s' % key)      
    for key in validators.__all__: environment[key]=eval('validators.%s' % key)
    environment['T']=translator(request)        
    environment['HTTP']=HTTP
    environment['redirect']=redirect
    environment['request']=request
    environment['response']=response    
    environment['session']=session
    environment['cache']=Cache(request)
    environment['SQLDB']=SQLDB
    SQLDB._set_thread_folder(os.path.join(request.folder,'databases'))    
    environment['SQLField']=SQLField
    environment['SQLFORM']=SQLFORM
    environment['SQLTABLE']=SQLTABLE
    # set default view, controller can override it
    response.view='%s/%s.html' % (request.controller,request.function)
    # also, make sure the flash is passed through
    if session.flash: response.flash, session.flash=session.flash, None  
    ###################################################
    # process models, controller and view (if required)
    ###################################################     
    run_models_in(environment)
    response._view_environment=copy.copy(environment)  
    run_controller_in(request.controller,request.function,environment)
    if not type(response.body) in [types.StringType, types.GeneratorType]:
        for key,value in response._vars.items(): 
            response._view_environment[key]=value
        run_view_in(response._view_environment)
        response.body=response.body.getvalue()
    raise HTTP(200,response.body,**response.headers)

def wsgibase(environ, responder):    
    """
    this is the gluon wsgi application. the furst function called when a page 
    is requested (static or dynamical). it can be called by paste.httpserver
    or by apache mod_wsgi.
    """
    ### os.chdir(working_folder) ### to recover if the app does chdir
    request=Request()
    response=Response()
    session=Session()
    try:
        try:
            session_file=None
            session_new=False
            ###################################################
            # parse the environment variables - DONE
            ###################################################
            for key, value in environ.items():
                request.env[key.lower().replace('.','_')]=value
            if not request.env.web2py_path: request.env.web2py_path=working_folder
            ###################################################
            # valudate the path in url
            ###################################################
            if not request.env.path_info and request.env.request_uri:
                request.env.path_info=request.env.request_uri # for fcgi
            path=request.env.path_info[1:].replace('\\','/')
            if not regex_url.match(path): 
                raise HTTP(400,error_message,web2py_error='invalid path')
            items=path.split('/')
            ###################################################
            # serve if a static file
            ###################################################
            
            if len(items)>2 and items[1]=='static':
                static_file=os.path.join(request.env.web2py_path,'applications',items[0],'static','/'.join(items[2:]))
                if not os.access(static_file,os.R_OK): 
                    raise HTTP(400,error_message,web2py_error='invalid application')
                stat_file=os.stat(static_file)
                mtime=RFC1123_DATETIME(stat_file[stat.ST_MTIME])
                headers={'Content-Type':contenttype(static_file),
                         'Content-Length':stat_file[stat.ST_SIZE],
                         'Last-Modified':mtime}
                if environ.get('HTTP_IF_MODIFIED_SINCE', '') == mtime:
                    raise HTTP(304)
                else:
                    raise HTTP(200,streamer(open(static_file,'rb')),**headers)
            ###################################################
            # parse application, controller and function
            ###################################################
            if len(items) and items[-1]=='': del items[-1]
            if len(items)==0: redirect('/init/default/index')
            if len(items)==1: redirect('/%s/default/index' % items[0])
            if len(items)==2: redirect('/%s/%s/index' % tuple(items))
            if len(items)>3: items,request.args=items[:3],items[3:]
            if request.args==None: request.args=[]
            request.application=items[0]
            request.controller=items[1]
            request.function=items[2]
            request.folder=os.path.join(request.env.web2py_path,'applications',request.application)+'/'
            ###################################################
            # access the requested application
            ################################################### 
            if not os.access(request.folder,os.F_OK):
                if items==['init','default','index']: 
                   redirect('/welcome/default/index')
                raise HTTP(400,error_message,web2py_error='invalid application')
            ###################################################
            # get the GET and POST data -DONE
            ###################################################
            request.body=tempfile.TemporaryFile()            
            if request.env.content_length:
                copystream(request.env.wsgi_input,request.body,
                           int(request.env.content_length))
            if request.env.request_method in ['POST', 'BOTH']:
                dpost=cgi.FieldStorage(fp=request.body,
                                       environ=environ,keep_blank_values=1)
                request.body.seek(0)
                try: keys=dpost.keys()
                except TypeError: keys=[]
                for key in keys: 
                    dpk=dpost[key]
                    if type(dpk)==types.ListType:
                        request.post_vars[key]=request.vars[key]=[x.value for x in dpk]        
                    elif not dpk.filename: #or type(dpk.file)==type(cStringIO.StringIO()):
                        request.post_vars[key]=request.vars[key]=dpk.value
                    else:
                        request.post_vars[key]=request.vars[key]=dpk        
            if request.env.request_method in ['GET', 'BOTH']:
                dget=cgi.FieldStorage(environ=environ,keep_blank_values=1)
                for key in dget.keys():
                    request.get_vars[key]=request.vars[key]=dget[key].value        
            ###################################################
            # load cookies
            ###################################################
            request.cookies=Cookie.SimpleCookie()
            response.cookies=Cookie.SimpleCookie()
            if request.env.http_cookie: 
                request.cookies.load(request.env.http_cookie)
            ###################################################
            # try load session or create new session file
            ###################################################
            session_id_name='session_id_%s'%request.application
            if request.cookies.has_key(session_id_name):
                response.session_id=request.cookies[session_id_name].value
                if regex_session_id.match(response.session_id):
                     session_filename=os.path.join(request.folder,'sessions/',response.session_id)
                else: response.session_id=None            
            if response.session_id:
                try: 
                     session_file=open(session_filename,'rb+')
                     portalocker.lock(session_file,portalocker.LOCK_EX)
                     session=Storage(cPickle.load(session_file))
                     session_file.seek(0)
                except:
                     if session_file: portalocker.unlock(session_file)
                     response.session_id=None
            if not response.session_id:
                response.session_id=request.env.remote_addr+'.'+str(int(time.time()))+'.'+str(random())[2:]
                session_filename=os.path.join(request.folder,'sessions/',response.session_id)
                session_new=True
            response.cookies[session_id_name]=response.session_id
            response.cookies[session_id_name]['path']="/"
            response.session_id_name=session_id_name
            ###################################################
            # run controller
            ###################################################
            if not items[1]=='static':
                serve_controller(request,response,session)        
        except HTTP, http_response:
            ###################################################
            # on sucess, committ database
            ###################################################                
            SQLDB.close_all_instances(SQLDB.commit)
            ###################################################
            # save cookies is session (static files do not have a session)
            ###################################################
            if response.session_id:
                http_response.headers['Set-Cookie']=[str(response.cookies[i])[11:] for i in response.cookies.keys()]
                if session_new:
                    session_file=open(session_filename,'wb')
                    portalocker.lock(session_file,portalocker.LOCK_EX)
                cPickle.dump(dict(session),session_file)
            ###################################################   
            # whatever happens return the intended HTTP response
            ###################################################                
            if session_file: portalocker.unlock(session_file)
            return http_response.to(responder)
        except RestrictedError, e:
            ###################################################
            # on application error, rollback database
            ###################################################                
            SQLDB.close_all_instances(SQLDB.rollback)
            ticket=e.log(request)
            if session_file: portalocker.unlock(session_file)
            return HTTP(200,error_message_ticket % (ticket,ticket),\
               web2py_error='ticket %s'%ticket).to(responder)
    except Exception, exception:
        ###################################################
        # on application error, rollback database
        ###################################################        
        ### os.chdir(working_folder) ### to recover if the app does chdir
        try: SQLDB.close_all_instances(SQLDB.rollback)
        except: pass
        e=RestrictedError('Framework','','',locals())
        try: ticket=e.log(request)
        except:
            ticket='unrecoverable'
            print '*'*10,'intenral error traceback','*'*10
            print e.traceback
            print '*'*49
        if session_file: portalocker.unlock(session_file)
        return HTTP(200,error_message_ticket % (ticket,ticket),
                web2py_error='ticket %s'%ticket).to(responder)

wsgibase,html.URL=rewrite(wsgibase,html.URL)

def save_password(password,port):
    """
    used by main() to save the password in the parameters.py file.
    """
    if password=='<recycle>': return
    import gluon.validators
    crypt=gluon.validators.CRYPT()
    file=open('parameters_%i.py'%port,'w')
    if len(password)>0: file.write('password="%s"\n' % crypt(password)[0])
    else: file.write('password=None\n')
    file.close()

def appfactory(wsgiapp=wsgibase,logfilename='httpsever.log',web2py_path=working_folder):
    def app_with_logging(environ, responder):
        environ['web2py_path']=web2py_path
        status_headers=[]
        def responder2(s,h):
            status_headers.append(s)
            status_headers.append(h)
            return responder(s,h)
        time_in=time.time()
        ret=wsgiapp(environ,responder2)
        try:
            if not logfilename: raise IOError
            line='%s, %s, %s, %s, %s, %s, %f\n' % (environ['REMOTE_ADDR'], datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S'), environ['REQUEST_METHOD'],environ['PATH_INFO'].replace(',','%2C'),environ['SERVER_PROTOCOL'],status_headers[0][:3],time.time()-time_in)
            open(logfilename,'a').write(line)
        except: pass
        return ret
    return app_with_logging

class HttpServer:
    def __init__(self,ip='127.0.0.1',port=8000,password='',
                 pid_filename='httpserver.pid',
                 log_filename='httpserver.log',
                 ssl_certificate=None,
                 ssl_private_key=None,
                 server_name=None,
                 path=working_folder):
        """
        starts the web server.
        """
        save_password(password,port)
        self.pid_filename=pid_filename
        if not server_name: server_name=socket.gethostname()
        print 'starting web server...'        
        self.server=wsgiserver.CherryPyWSGIServer((ip, port),
                    appfactory(wsgibase,log_filename,web2py_path=path),
 	            server_name=server_name)
        if not ssl_certificate or not ssl_private_key:
            print 'SSL is off'
        elif not wsgiserver.SSL:
            print 'Error: OpenSSL libraries available. SSL is OFF'
        elif not os.access(ssl_certificate,os.R_OK):
            print 'Error: unable to open SSL certificate. SSL is OFF'
        elif not os.access(ssl_private_key,os.R_OK):
            print 'Error: unable to open SSL private key. SSL is OFF'
        else:
            self.server.ssl_certificate=ssl_certificate
            self.server.ssl_private_key=ssl_private_key
            print 'SSL is ON'
    def start(self):
        try: signal.signal(signal.SIGTERM,lambda a,b,s=self:s.stop())
        except: pass
        open(self.pid_filename,'w').write(str(os.getpid()))
        self.server.start()
    def stop(self):
        self.server.stop()
        os.unlink(self.pid_filename)
"""
This file is part of web2py Web Framework (Copyrighted, 2007)
Developed by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: GPL v2
"""

import cgi, cStringIO, Cookie, cPickle, os
import re, copy, sys, types, time, thread
import datetime, signal, socket, stat
import tempfile, logging
#from wsgiref.simple_server import make_server, demo_app
from random import random
from storage import Storage, load_storage, save_storage
from restricted import RestrictedError
from http import HTTP, redirect
from globals import Request, Response, Session
from compileapp import build_environment, run_models_in, run_controller_in, run_view_in
from fileutils import listdir, copystream
from contenttype import contenttype
from rewrite import rewrite, error_message, error_message_ticket, symbols as rewriteSymbols
from xmlrpc import handler
from sql import SQLDB
import html
import myregex
try: import wsgiserver
except: logging.warn("unable to import wsgiserver")
### contrib moduels
import contrib.simplejson
import contrib.pyrtf
import contrib.rss2
import contrib.feedparser
import contrib.markdown
import contrib.memcache

__all__=['wsgibase', 'save_password', 'appfactory', 'HttpServer']

### Security Checks: validate URL and session_id here, accept_language is validated in languages
# pattern to replace spaces with underscore in URL
regex_space=re.compile('(\+|\s|%20)+')
# pattern to find valid paths in url /application/controller/...
regex_url=re.compile('(?:^$)|(?:^\w+/?$)|(?:^\w+/[\w\-]+/?$)|(?:^\w+/[\w\-]+/\w+/?$)|(?:^\w+/[\w\-]+/\w+(/[\w\-]+(\.[\w\-]+)*)+$)|(?:^(\w+)/static(/[\w\-]+(\.[\w\-]+)*)+$)')
# patter used to validate client address
regex_client=re.compile('[\w\-:]*(\.[\w\-]+)*\.?') ### to account for IPV6

working_folder=os.getcwd()

def get_client(env):
    g=regex_client.search(env.get('http_x_forwarded_for',''))
    if g: return g.group()
    g=regex_client.search(env.get('remote_addr',''))
    if g: return g.group()
    return '127.0.0.1'

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
    environment=build_environment(request,response,session)
    # set default view, controller can override it
    response.view='%s/%s.html' % (request.controller,request.function)
    # also, make sure the flash is passed through
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

def check_error_route(status, app):
    """ Unless the error code is redirected, we want to send error messages out
    with HTTP status 200.  Otherwise IE won't display them. """
    
    error_list = rewriteSymbols.get('routes_onerror', [])
    error_map = dict(list(error_list))

    if not error_list: return 200
    for redir in [x[0] for x in error_list]:
        if redir.endswith('/%s' % status) and error_map[redir] != '!':
            return status
        if (redir == '%s/*' % app or redir == '*/*') and error_map[redir] != '!':
            return status
    return 200
    
def wsgibase(environ, responder):
    """
    this is the gluon wsgi application. the furst function called when a page
    is requested (static or dynamical). it can be called by paste.httpserver
    or by apache mod_wsgi.
    """
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
            if not request.env.web2py_path:
                request.env.web2py_path=working_folder
            ###################################################
            # valudate the path in url
            ###################################################
            if not request.env.path_info and request.env.request_uri:
                # for fcgi, decode path_info and query_string
                items=request.env.request_uri.split('?')
                request.env.path_info=items[0]               
                if len(items)>1: request.env.query_string=items[1]
                else: request.env.query_string=''
            path=request.env.path_info[1:].replace('\\','/')
            path=regex_space.sub('_',path)
            if not regex_url.match(path):
                raise HTTP(400,error_message,web2py_error='invalid path')
            items=path.split('/')
            ###################################################
            # serve if a static file
            ###################################################
            if len(items)>1 and items[1]=='static':
                 if len(items)<3 or not items[2]: raise HTTP(400,error_message)
                 static_file=os.path.join(request.env.web2py_path,\
                    'applications',items[0],'static','/'.join(items[2:]))
                 response.stream(static_file,request=request)
            ###################################################
            # parse application, controller and function
            ###################################################
            if len(items) and items[-1]=='': del items[-1]
            if len(items)==0: items=['init']
            if len(items)==1: items.append('default')
            if len(items)==2: items.append('index')
            if len(items)>3: items,request.args=items[:3],items[3:]
            if request.args==None: request.args=[]
            request.application=items[0]
            request.controller=items[1]
            request.function=items[2]
            request.client=get_client(request.env)
            request.folder=os.path.join(request.env.web2py_path,\
               'applications',request.application)+'/'
            ###################################################
            # access the requested application
            ###################################################
            if not os.path.exists(request.folder):
                if items==['init','default','index']:
                   items[0]='welcome'
                   redirect(html.URL(*items))
                raise HTTP(400,error_message,web2py_error='invalid application')
            ###################################################
            # get the GET and POST data -DONE
            ###################################################
            request.body=tempfile.TemporaryFile()
            if request.env.content_length:
                copystream(request.env.wsgi_input,request.body,
                           int(request.env.content_length))
            ### parse GET vars, even if POST
            dget=cgi.parse_qsl(request.env.query_string,keep_blank_values=1)
            for key,value in dget:
                if request.vars.has_key(key):
                    if isinstance(request.vars[key],list):
                        request.vars[key].append(value)
                    else:
                        request.vars[key]=[request.vars[key],value]
                else: request.vars[key]=value
                request.get_vars[key]=request.vars[key]
            ### parse POST vars if any
            if request.env.request_method in ['POST', 'BOTH']:
                dpost=cgi.FieldStorage(fp=request.body,
                                       environ=environ,keep_blank_values=1)
                request.body.seek(0)
                try: keys=dpost.keys()
                except TypeError: keys=[]
                for key in keys:
                    dpk=dpost[key]
                    if isinstance(dpk,list): value=[x.value for x in dpk]
                    elif not dpk.filename: value=dpk.value
                    else: value=dpk
                    request.post_vars[key]=request.vars[key]=value
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
            session.connect(request,response)
            ###################################################
            # set no-cache headers
            ###################################################
            response.headers['Cache-Control']=\
               "no-store, no-cache, must-revalidate, post-check=0, pre-check=0"
            response.headers['Expires']=\
               time.strftime("%a, %d %b %Y %H:%M:%S GMT",time.gmtime())
            response.headers['Pragma']="no-cache"
            ###################################################
            # run controller
            ###################################################
            if not items[1]=='static':
                serve_controller(request,response,session)
        except HTTP, http_response:
            ###################################################
            # on sucess, try store session in database
            ###################################################
            session._try_store_in_db(request,response)
            ###################################################
            # on sucess, committ database
            ###################################################
            if response._custom_commit: reponse._custom_commit()
            else: SQLDB.close_all_instances(SQLDB.commit)
            ###################################################
            # if session not in db try store session on filesystem
            ###################################################
            session._try_store_on_disk(request,response)
            ###################################################
            # store cookies in headers
            ###################################################
            if session._secure:
                response.cookies[response.session_id_name]['secure']=True
            http_response.headers['Set-Cookie']=\
                [str(cookie)[11:] for cookie in response.cookies.values()]
            ###################################################
            # whatever happens return the intended HTTP response
            ###################################################
            session._unlock(response)
            return http_response.to(responder)
        except RestrictedError, e:
            ###################################################
            # on application error, rollback database
            ###################################################
            if response._custom_rollback: reponse._custom_rollback()
            else: SQLDB.close_all_instances(SQLDB.rollback)
            try: ticket=e.log(request)
            except:
                 ticket='unknown'
                 logging.error(e.traceback)
            session._unlock(response)
            http_error_status = check_error_route(500, items[0])
            return HTTP(http_error_status,error_message_ticket % dict(ticket=ticket),\
               web2py_error='ticket %s'%ticket).to(responder)
    except:
        ###################################################
        # on application error, rollback database
        ###################################################
        try: 
            if response._custom_rollback: reponse._custom_rollback()
            else: SQLDB.close_all_instances(SQLDB.rollback)
        except: pass
        e=RestrictedError('Framework','','',locals())
        try: ticket=e.log(request)
        except:
            ticket='unrecoverable'
            logging.error(e.traceback)
        session._unlock(response)
        http_error_status = check_error_route(500, items[0])
        return HTTP(http_error_status,error_message_ticket % dict(ticket=ticket),
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
            line='%s, %s, %s, %s, %s, %s, %f\n' % (environ['REMOTE_ADDR'], datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S'), environ['REQUEST_METHOD'],environ['PATH_INFO'].replace(',','%2C'),environ['SERVER_PROTOCOL'],status_headers[0][:3],time.time()-time_in)
            if logfilename: open(logfilename,'a').write(line)
            else: sys.stdout.write(line)
        except: pass
        return ret
    return app_with_logging

class HttpServer(object):
    def __init__(self,ip='127.0.0.1',port=8000,password='',
                 pid_filename='httpserver.pid',
                 log_filename='httpserver.log',
                 ssl_certificate=None,
                 ssl_private_key=None,
                 numthreads=10,
                 server_name=None,
                 request_queue_size=5,
                 timeout=10,
                 shutdown_timeout=5,
                 path=working_folder):
        """
        starts the web server.
        """
        save_password(password,port)
        self.pid_filename=pid_filename
        if not server_name: server_name=socket.gethostname()
        logging.info('starting web server...')
        self.server=wsgiserver.CherryPyWSGIServer((ip, port),
                    appfactory(wsgibase,log_filename,web2py_path=path),
                    numthreads=int(numthreads), server_name=server_name,
                    request_queue_size=int(request_queue_size),
                    timeout=int(timeout),
                    shutdown_timeout=int(shutdown_timeout))
        if not ssl_certificate or not ssl_private_key:
            logging.info('SSL is off')
        elif not wsgiserver.SSL:
            logging.warning('OpenSSL libraries unavailable. SSL is OFF')
        elif not os.path.exists(ssl_certificate):
            logging.warning('unable to open SSL certificate. SSL is OFF')
        elif not os.path.exists(ssl_private_key):
            logging.warning('unable to open SSL private key. SSL is OFF')
        else:
            self.server.ssl_certificate=ssl_certificate
            self.server.ssl_private_key=ssl_private_key
            logging.info('SSL is ON')
    def start(self):
        try: signal.signal(signal.SIGTERM,lambda a,b,s=self:s.stop())
        except: pass
        open(self.pid_filename,'w').write(str(os.getpid()))
        self.server.start()
    def stop(self):
        self.server.stop()
        os.unlink(self.pid_filename)

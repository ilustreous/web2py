# This sees request, response, session, expose, redirect, HTTP

############################################################
### import required modules/functions
############################################################
from gluon.fileutils import listdir,cleanpath,tar,tar_compiled,untar,fix_newlines
from gluon.languages import findT, update_all_languages
from gluon.myregex import *
from gluon.restricted import *
from gluon.contrib.markdown import WIKI
from gluon.compileapp import compile_application, remove_compiled_application
import time,os,sys,re,urllib,socket

############################################################
### make sure administrator is on localhost
############################################################

http_host = request.env.http_host.split(':')[0]
remote_addr = request.env.remote_addr
if remote_addr not in (http_host, socket.gethostbyname(remote_addr)):
    raise HTTP(400)

############################################################
### generate menu
############################################################

_f=request.function
response.menu=[('site',_f=='site','/%s/default/site'%request.application)]
if request.args:
    _t=(request.application,request.args[0])   
    response.menu.append(('about',_f=='about','/%s/default/about/%s'%_t))
    response.menu.append(('design',_f=='design','/%s/default/design/%s'%_t))
    response.menu.append(('errors',_f=='errors','/%s/default/errors/%s'%_t))    
if not session.authorized: response.menu=[('login',True,'')]
else: response.menu.append(('logout',False,'/%s/default/logout'%request.application))
response.menu.append(('help',False,'/examples/default/index'))

############################################################
### exposed functions
############################################################

def apath(path=''): 
    return os.path.join(request.folder,'..',path).replace('\\','/')

try:
    _config={}
    port=int(request.env.server_port)
    restricted(open(apath('../parameters_%i.py'%port),'r').read(),_config)
    if not _config.has_key('password') or not _config['password']:
        raise HTTP(400)
except: raise HTTP(400)

############################################################
### session expiration
############################################################

EXPIRATION=10*60 # logout after 10 minutes of inactivity
t0=time.time()
if session.authorized:
    if session.last_time and session.last_time<t0-EXPIRATION:
        session.flash='session expired'
        session.authorized=False
    else: session.last_time=t0

if not session.authorized and not request.function=='index': 
    redirect(URL(r=request,f='index'))

def index():
    """ admin controller function """
    if request.vars.password:
        if _config['password']==CRYPT()(request.vars.password)[0]:
            session.authorized=True
            try:        
                version=urllib.urlopen('http://mdp.cti.depaul.edu/examples/default/version').read()
                myversion=open(apath('../VERSION'),'r').read()
                if version!=myversion: session.flash='A new version of web2py is available, you should upgrade at http://mdp.cti.depaul.edu/examples'
            except: pass
            session.last_time=t0
            redirect(URL(r=request,f='site'))
        else: response.flash='invalid password'
    apps=[file for file in os.listdir(apath()) if file.find('.')<0]    
    return dict(apps=apps)

def logout():
    """ admin controller function """
    session.authorized=None
    redirect(URL(r=request,f='index'))

def site():
    """ admin controller function """
    if request.vars.filename and not request.vars.has_key('file'):
        try:
            appname=cleanpath(request.vars.filename)
            path=apath(appname)
            os.mkdir(path)
            untar('welcome.tar',path)
            response.flash='new application "%s" created' % appname
        except:
            response.flash='unable to create new application "%s"' % request.vars.filename
    elif request.vars.has_key('file') and not request.vars.filename:
        response.flash='you must specify a name for the uploaded application'
    elif request.vars.filename and request.vars.has_key('file'):
        try:
            appname=cleanpath(request.vars.filename)
            tarname=apath('../deposit/%s.tar' % appname)
            open(tarname,'wb').write(request.vars.file.file.read())
            path=apath(appname)
            os.mkdir(path)
            untar(tarname,path)
            fix_newlines(path)
            response.flash='application %s installed' % appname
        except:
            response.flash='unable to install application "%s"' % request.vars.filename
    regex=re.compile('^\w+$')
    apps=[file for file in os.listdir(apath()) if regex.match(file)]
    return dict(app=None,apps=apps)

def pack():        
    """ admin controller function """
    try: 
        app=request.args[0]
        filename=apath('../deposit/%s.tar' % app)
        tar(filename,apath(app),'^[\w\.\-]+$')
    except: redirect(URL(r=request,f='site'))
    response.headers['Content-Type']='application/x-tar'
    return open(filename,'rb').read()

def pack_compiled():        
    """ admin controller function """
    try: 
        app=request.args[0]
        filename=apath('../deposit/%s.tar' % app)
        tar_compiled(apath(app),'[^[\w\.\-]+$')
    except: redirect(URL(r=request,f='site'))
    response.headers['Content-Type']='application/x-tar'
    return open(filename,'rb').read()

def uninstall():
    """ admin controller function """
    try:
        app=request.args[0]
        if not request.vars.has_key('delete'): return dict(app=app)
        elif request.vars['delete']!='YES':
             session.flash=''
             redirect(URL(r=request,f='site'))        
        filename=apath('../deposit/%s.tar' % app )
        path=apath(app)
        tar(filename,path,'^[\w\.]+$')
        for root,dirs,files in os.walk(path,topdown=False):
            for name in files: os.remove(os.path.join(root,name))
            for name in dirs: os.rmdir(os.path.join(root,name))
        os.rmdir(path)
        session.flash='application "%s" uninstalled' % app
    except:
        session.flash='unable to uninstall "%s"' % app
    redirect(URL(r=request,f='site'))

def cleanup():        
    """ admin controller function """
    app=request.args[0]
    files=listdir(apath('%s/errors/' % app),'',0)
    for file in files: os.unlink(file)
    files=listdir(apath('%s/sessions/' % app),'',0)
    for file in files: os.unlink(file)
    session.flash="cache, errors and sessions cleaned"
    files=listdir(apath('%s/cache/' % app),'',0)
    for file in files: 
        try: os.unlink(file)
        except: session.flash="cache is in use, errors and sessions cleaned"
    redirect(URL(r=request,f='site'))

def compile_app():
    """ admin controller function """
    app=request.args[0]
    folder=apath(app)
    try:
        compile_application(folder)
        session.flash='application compiled'
    except Exception, e:
        remove_compiled_application(folder)
        session.flash='plase debug the application first (%s)' % str(e)
    redirect(URL(r=request,f='site'))

def remove_compiled_app():
    """ admin controller function """
    app=request.args[0]
    remove_compiled_application(apath(app))
    session.flash='compiled application removed'
    redirect(URL(r=request,f='site'))

def delete():
    """ admin controller function """
    filename='/'.join(request.args)
    sender=request.vars.sender
    try:
        if not request.vars.has_key('delete'): return dict(filename=filename,sender=sender)
        elif request.vars['delete']!='YES':
             session.flash='file "%s" was not deleted' % filename
             redirect(URL(r=request,f=sender))
        os.unlink(apath(filename))
        session.flash='file "%s" deleted' % filename
    except:
        session.flash='unable to delete file "%s"' % filename
    redirect(URL(r=request,f=sender))

def peek():
    """ admin controller function """
    filename='/'.join(request.args)
    try:
        data=open(apath(filename),'r').read()
    except IOError: 
        session.flash='file does not exist'
        redirect(URL(r=request,f='site'))
    extension=filename[filename.rfind('.')+1:].lower()    
    return dict(app=request.args[0],filename=filename,data=data,extension=extension)

def test():
    app=request.args[0]
    controllers=listdir(apath('%s/controllers/' % app), '.*\.py$')
    return dict(app=app,controllers=controllers)

def edit():
    """ admin controller function """
    filename='/'.join(request.args)    
    if filename[-3:]=='.py': filetype='python'
    elif filename[-5:]=='.html': filetype='html'
    else: filetype=''
    ### check if file is not there 
    data=open(apath(filename),'r').read()
    try:
        data=request.vars.data.replace('\r\n','\n').strip()
        open(apath(filename),'w').write(data)
        response.flash="file saved on "+time.ctime()       
    except: pass
    return dict(app=request.args[0],filename=filename,filetype=filetype,data=data)


def edit_language():
    """ admin controller function """
    filename='/'.join(request.args)    
    ### check if file is not there 
    strings=eval(open(apath(filename),'r').read())
    keys=strings.keys()
    keys.sort()
    rows=[]
    rows.append(TR(B('Original'),B('Translation')))
    for keyi in range(len(keys)):
        key=keys[keyi]
        if len(key)<=40:
            rows.append(TR(key+' ',INPUT(_type='text',_name=str(keyi),value=strings[key],_size=40)))
        else:
            rows.append(TR(key+':',TEXTAREA(_name=str(keyi),value=strings[key],_cols=40,_rows=5)))
    rows.append(TR('',INPUT(_type='submit',_value='update')))
    form=FORM(TABLE(*rows))
    if form.accepts(request.vars,keepvalues=True):
        txt='{\n'
        for keyi in range(len(keys)):
            key=keys[keyi]
            txt+='%s:%s,\n' % (repr(key),repr(form.vars[str(keyi)]))
        txt+='}\n'
        open(apath(filename),'w').write(txt)        
        response.flash="file saved on "+time.ctime()       
    return dict(app=request.args[0],filename=filename,form=form)

def htmledit():
    """ admin controller function """
    filename='/'.join(request.args)    
    ### check if file is not there 
    data=open(apath(filename),'r').read()
    try:
        data=request.vars.data.replace('\r\n','\n') 
        open(apath(filename),'w').write(data)
        response.flash="file saved on "+time.ctime()       
    except: pass
    return dict(app=request.args[0],filename=filename,data=data)

def about():
    """ admin controller function """
    app=request.args[0] 
    ### check if file is not there 
    about=open(apath('%s/ABOUT' % app),'r').read()
    license=open(apath('%s/LICENSE' % app),'r').read()
    return dict(app=app,about=WIKI(about),license=WIKI(license))

def design():
    """ admin controller function """
    app=request.args[0] 
    if not response.slash and app==request.application:
        response.flash='ATTENTION: you cannot edit the running application!'
    if os.access(apath('%s/compiled' % app),os.R_OK):
        session.flash='application is compiled and cannot be designed'
        redirect(URL(r=request,f='site'))
    models=listdir(apath('%s/models/' % app), '.*\.py$')
    defines={}
    for m in models:
        data=open(apath('%s/models/%s'%(app,m)),'r').read()
        defines[m]=regex_tables.findall(data)
        defines[m].sort()
    controllers=listdir(apath('%s/controllers/' % app), '.*\.py$')
    controllers.sort()
    functions={}    
    for c in controllers:
        data=open(apath('%s/controllers/%s' % (app,c)),'r').read()
        items=regex_expose.findall(data)
        functions[c]=items
    views=listdir(apath('%s/views/' % app),'.*\.html$')
    views.sort()
    extend={}
    include={}
    for c in views:
        data=open(apath('%s/views/%s' % (app,c)),'r').read()
        items=regex_extend.findall(data)
        if items: extend[c]=items[0][1]
        items=regex_include.findall(data)
        include[c]=[i[1] for i in items]
    statics=listdir(apath('%s/static/' % app))
    statics.sort()
    languages=listdir(apath('%s/languages/' % app), '[\w-]*\.py')
    return dict(app=app,models=models,defines=defines,controllers=controllers,functions=functions,views=views,extend=extend,include=include,statics=statics,languages=languages)


def create_file():
    """ admin controller function """
    try:
        path=apath(request.vars.location)
        filename=re.sub('[^\w./-]+','_',request.vars.filename)        
        if path[-11:]=='/languages/':
            if len(filename)==0: raise SyntaxError
            app=path.split('/')[-3] 
            findT(apath(app),filename)
            session.flash='language file "%s" created/updated' % filename
            redirect(request.vars.sender)
        elif path[-8:]=='/models/': 
            if not filename[-3:]=='.py': filename+='.py'
            if len(filename)==3: raise SyntaxError
            fn=re.sub('\W','',filename[:-3].lower())
            text='# try something like\n%s=SQLDB("sqlite://%s.db")' % (fn,fn)
        elif path[-13:]=='/controllers/':
            if not filename[-3:]=='.py': filename+='.py'
            if len(filename)==3: raise SyntaxError
            text='# try something like\ndef index(): return dict(message="hello from %s")' % filename
        elif path[-7:]=='/views/':
            if not filename[-5:]=='.html': filename+='.html'
            if len(filename)==5: raise SyntaxError
            text="{{extend 'layout.html'}}\n<h1>This is the %s template</h1>\n{{=BEAUTIFY(response._vars)}}" % filename
        else:
            redirect(request.vars.sender)
        filename=os.path.join(path,filename)
        dirpath=os.path.dirname(filename)
        if not os.path.exists(dirpath): os.makedirs(dirpath)
        if os.access(filename,os.R_OK): raise SyntaxError
        open(filename,'w').write(text)
        session.flash='file "%s" created' % filename[len(path):]
    except Exception, e:
        session.flash='cannot create file "%s"' % filename
    redirect(request.vars.sender)

def upload_file(): 
    """ admin controller function """
    try:
        path=apath(request.vars.location)
        filename=re.sub('[^\w./]+','_',request.vars.filename)
        if path[-8:]=='/models/' and not filename[-3:]=='.py': filename+='.py'
        if path[-13:]=='/controllers/' and not filename[-3:]=='.py': filename+='.py'
        if path[-7:]=='/views/' and not filename[-5:]=='.html': filename+='.html'
        if path[-11:]=='/languages/' and not filename[-3:]=='.py': filename+='.py'
        filename=os.path.join(path,filename)
        items=filename.split('/')
        p=''
        for item in items[:-1]:
            p=os.path.join(p,item)
            try: os.mkdir(p)
            except: pass
        open(filename,'w').write(request.vars.file.file.read())
        session.flash='file "%s" uploaded' %  filename[len(path):]
    except: 
        session.flash='cannot upload file "%s"' % filename[len(path):]
    redirect(request.vars.sender)

def errors(): 
    """ admin controller function """
    app=request.args[0] 
    for item in request.vars:
        if item[:7]=='delete_':
            os.unlink(apath('%s/errors/%s' % (app,item[7:])))
    tickets=os.listdir(apath('%s/errors/' % app))
    return dict(app=app,tickets=tickets)

def ticket():        
    """ admin controller function """
    app=request.args[0] 
    ticket=request.args[1] 
    e=RestrictedError()
    e.load(apath('%s/errors/%s' % (app,ticket)))
    return dict(app=app,ticket=ticket,traceback=e.traceback,code=e.code,layer=e.layer)

def update_languages():
    """ admin controller function """
    app=request.args[0]
    update_all_languages(apath(app))
    session.flash='languages updated'
    redirect(URL(r=request,f='design/'+app))

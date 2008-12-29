
############################################################
### import required modules/functions
############################################################
from gluon.fileutils import listdir,cleanpath,tar,tar_compiled,untar,fix_newlines
from gluon.languages import findT, update_all_languages
from gluon.myregex import *
from gluon.restricted import *
from gluon.contrib.markdown import WIKI
from gluon.compileapp import compile_application, remove_compiled_application
import time,os,sys,re,urllib,socket,md5


############################################################
### make sure administrator is on localhost
############################################################

http_host = request.env.http_host.split(':')[0]

try:
     from gluon.contrib.gql import GQLDB
     session_db=GQLDB()
     session.connect(request,response,db=session_db)
     hosts=(http_host,)
except Exception:
     hosts=(http_host,socket.gethostname(),socket.gethostbyname(http_host))

remote_addr = request.env.remote_addr

if request.env.http_x_forwarded_for or \
   request.env.wsgi_url_scheme in ['https','HTTPS']:
    session.secure()
elif not remote_addr in hosts:
    raise HTTP(200,T('Admin is disabled because unsecure channel'))

############################################################
### generate menu
############################################################

_f=request.function
response.menu=[(T('site'),_f=='site','/%s/default/site'%request.application)]
if request.args:
    _t=(request.application,request.args[0])   
    response.menu.append((T('about'),_f=='about','/%s/default/about/%s'%_t))
    response.menu.append((T('design'),_f=='design','/%s/default/design/%s'%_t))
    response.menu.append((T('errors'),_f=='errors','/%s/default/errors/%s'%_t))    
if not session.authorized: response.menu=[(T('login'),True,'')]
else: response.menu.append((T('logout'),False,'/%s/default/logout'%request.application))
response.menu.append((T('help'),False,'/examples/default/index'))

############################################################
### exposed functions
############################################################

def apath(path=''):
    from gluon.fileutils import up
    opath=up(request.folder)
    #TODO: This path manipulation is very OS specific.
    while path[:3]=='../': opath,path=up(opath),path[3:]
    return os.path.join(opath,path).replace('\\','/')

try:
    _config={}
    port=int(request.env.server_port)
    restricted(open(apath('../parameters_%i.py'%port),'r').read(),_config)
    if not _config.has_key('password') or not _config['password']:
        raise HTTP(200,T('admin disabled because no admin password'))
except Exception: raise HTTP(200,T('admin disabled because unable to access password file'))

############################################################
### session expiration
############################################################

t0=time.time()
if session.authorized:
    if session.last_time and session.last_time<t0-EXPIRATION:
        session.flash=T('session expired')
        session.authorized=False
    else: session.last_time=t0

if not session.authorized and not request.function=='index': 
    if request.env.query_string: query_string='?'+request.env.query_string
    else: query_string=''
    url=request.env.path_info+query_string
    redirect(URL(r=request,f='index',vars=dict(send=url)))

def index():
    """ admin controller function """
    send=request.vars.send
    if not send: send=URL(r=request,f='site')
    if request.vars.password:
        if _config['password']==CRYPT()(request.vars.password)[0]:
            session.authorized=True
            if CHECK_VERSION: session.check_version=True
            else: session.check_version=False
            session.last_time=t0
            redirect(send)
        else: response.flash=T('invalid password')
    apps=[file for file in os.listdir(apath()) if file.find('.')<0]    
    return dict(apps=apps,send=send)

def check_version():
    try:
         myversion=open(apath('../VERSION'),'r').read()
         version=urllib.urlopen(WEB2PY_VERSION_URL).read()
         if version>myversion: 
             return A(T('A new version of web2py is available'),_href=WEB2PY_URL)
         else:
             return A(T('web2py is up to date'),_href=WEB2PY_URL)
    except Exception:
        return A(T('Unable to check for upgrades'),_href=WEB2PY_URL)

def logout():
    """ admin controller function """
    session.authorized=None
    redirect(URL(r=request,f='index'))

def site():
    """ admin controller function """
    myversion=open(apath('../VERSION'),'r').read()
    if request.vars.filename and not request.vars.has_key('file'):
        try:
            appname=cleanpath(request.vars.filename).replace('.','_')
            path=apath(appname)
            os.mkdir(path)
            untar('welcome.tar',path)
            response.flash=T('new application "%(appname)s" created',dict(appname=appname))
        except Exception:
            response.flash=T('unable to create new application "%(appname)s"',dict(appname=request.vars.filename))
    elif (request.vars.has_key('file') or request.vars.has_key('appurl')) and not request.vars.filename:
        response.flash=T('you must specify a name for the uploaded application')
    elif request.vars.filename and (request.vars.has_key('file') or request.vars.has_key('appurl')):
        mkdir=False
        try:   
            appname=cleanpath(request.vars.filename).replace('.','_')
            tarname=apath('../deposit/%s.tar' % appname)
            if request.vars.appurl is not '':
               tarfile = urllib.urlopen(request.vars.appurl).read()
            elif request.vars.file is not '':
               tarfile = request.vars.file.file.read()
            open(tarname,'wb').write(tarfile)
            path=apath(appname)
            os.mkdir(path)
            mkdir=True
            untar(tarname,path)
            fix_newlines(path)
            response.flash=T('application %(appname)s installed with md5sum: %(digest)s',dict(appname=appname,digest=md5.new(tarfile).hexdigest()))
        except Exception:
            if mkdir:
                 for root,dirs,files in os.walk(path,topdown=False):
                     for name in files: os.remove(os.path.join(root,name))
                     for name in dirs: os.rmdir(os.path.join(root,name))
                 os.rmdir(path)
            response.flash=T('unable to install application "%(appname)s"',dict(appname=request.vars.filename))
    regex=re.compile('^\w+$')
    apps=[(file.upper(),file) for file in os.listdir(apath()) if regex.match(file)]
    apps.sort()
    apps=[item[1] for item in apps]
    return dict(app=None,apps=apps,myversion=myversion)

def pack():        
    """ admin controller function """
    try: 
        app=request.args[0]
        filename=apath('../deposit/%s.tar' % app)
        tar(filename,apath(app),'^[\w\.\-]+$')
    except Exception:
        session.flash=T('internal error')
        redirect(URL(r=request,f='site'))
    response.headers['Content-Type']='application/x-tar'
    response.headers['Content-Disposition']='attachment; filename=web2py.app.%s.tar'%app
    return open(filename,'rb').read()

def pack_compiled():        
    """ admin controller function """
    try: 
        app=request.args[0]
        filename=apath('../deposit/%s.tar' % app)
        tar_compiled(filename,apath(app),'^[\w\.\-]+$')
    except Exception:
        session.flash=T('internal error')
        redirect(URL(r=request,f='site'))
    response.headers['Content-Type']='application/x-tar'
    response.headers['Content-Disposition']='attachment; filename=web2py.app.%s.compiled.tar'%app
    return open(filename,'rb').read()

def uninstall():
    """ admin controller function """
    try:
        app=request.args[0]
        if not request.vars.has_key('delete'): return dict(app=app)
        elif request.vars['delete']!='YES':
             #TODO: It looks like this was overlooked.  When it gets filled in, don't forget to T() it.  -mdm 6/9/08
             session.flash=''
             redirect(URL(r=request,f='site'))        
        filename=apath('../deposit/%s.tar' % app )
        path=apath(app)
        tar(filename,path,'^[\w\.]+$')
        for root,dirs,files in os.walk(path,topdown=False):
            for name in files: os.remove(os.path.join(root,name))
            for name in dirs: os.rmdir(os.path.join(root,name))
        os.rmdir(path)
        session.flash=T('application "%(appname)s" uninstalled',dict(appname=app))
    except Exception:
        session.flash=T('unable to uninstall "%(appname)s"',dict(appname=app))
    redirect(URL(r=request,f='site'))

def cleanup():        
    """ admin controller function """
    app=request.args[0]
    files=listdir(apath('%s/errors/' % app),'^\d.*$',0)
    for file in files: os.unlink(file)
    files=listdir(apath('%s/sessions/' % app),'\d.*',0)
    for file in files: os.unlink(file)
    session.flash=T("cache, errors and sessions cleaned")
    files=listdir(apath('%s/cache/' % app),'cache.*',0)
    for file in files:
        try: os.unlink(file)
        except: session.flash=T("some files could not be removed")
    redirect(URL(r=request,f='site'))

def compile_app():
    """ admin controller function """
    app=request.args[0]
    folder=apath(app)
    try:
        compile_application(folder)
        session.flash=T('application compiled')
    except Exception, e:
        remove_compiled_application(folder)
        session.flash=T('please debug the application first (%(e)s)',dict(e=str(e)))
    redirect(URL(r=request,f='site'))

def remove_compiled_app():
    """ admin controller function """
    app=request.args[0]
    remove_compiled_application(apath(app))
    session.flash=T('compiled application removed')
    redirect(URL(r=request,f='site'))

def delete():
    """ admin controller function """
    filename='/'.join(request.args)
    sender=request.vars.sender
    try:
        if not request.vars.has_key('delete'): return dict(filename=filename,sender=sender)
        elif request.vars['delete']!='YES':
             session.flash=T('file "%(filename)s" was not deleted',dict(filename=filename))
             redirect(URL(r=request,f=sender))
        os.unlink(apath(filename))
        session.flash=T('file "%(filename)s" deleted',dict(filename=filename))
    except Exception:
        session.flash=T('unable to delete file "%(filename)s"',dict(filename=filename))
    redirect(URL(r=request,f=sender))

def peek():
    """ admin controller function """
    filename='/'.join(request.args)
    try:
        data=open(apath(filename),'r').read()
    except IOError: 
        session.flash=T('file does not exist')
        redirect(URL(r=request,f='site'))
    extension=filename[filename.rfind('.')+1:].lower()    
    return dict(app=request.args[0],filename=filename,data=data,extension=extension)

def test():
    app=request.args[0]
    if len(request.args)>1: file=request.args[1]
    else: file='.*\.py'
    controllers=listdir(apath('%s/controllers/' % app), file + '$')
    return dict(app=app,controllers=controllers)

def edit():
    """ admin controller function """
    filename='/'.join(request.args)
    if filename[-3:]=='.py': filetype='python'
    elif filename[-5:]=='.html': filetype='html'
    elif filename[-4:]=='.css': filetype='css'
    elif filename[-3:]=='.js': filetype='js'
    else: filetype='text'
    ### check if file is not there
    path=apath(filename)
    if request.vars.restore and os.path.exists(path+'.bak'):
        data=open(path+'.bak','r').read()
        data1=open(path,'r').read()
        file_hash=md5.new(data).hexdigest()
        open(path,'w').write(data)
        open(path+".bak",'w').write(data1)
        response.flash=T('file "%s" restored',filename)
    else:
        data=open(path,'r').read()
        file_hash=md5.new(data).hexdigest()    
        if request.vars.file_hash and request.vars.file_hash!=file_hash: 
            session.flash=T("file changed on disk")
            data=request.vars.data.replace('\r\n','\n').strip()+'\n'
            open(path+'.1','w').write(data)
            redirect(URL(r=request,f='resolve',args=request.args))
        elif request.vars.data:
            open(path+'.bak','w').write(data)
            data=request.vars.data.replace('\r\n','\n').strip()+'\n'
            open(path,'w').write(data)
            file_hash=md5.new(data).hexdigest()    
            response.flash=T("file saved on %(time)s",dict(time=time.ctime()))
    edit_controller=None
    if filetype=='html' and request.args>=3:
        cfilename=os.path.join(request.args[0],'controllers',request.args[2]+'.py')
        if os.path.exists(apath(cfilename)):
            edit_controller=URL(r=request,f='edit',args=[cfilename])
    if len(request.args)>2 and request.args[1]=='controllers':
        controller=request.args[2][:-3]
        functions=regex_expose.findall(data)
    else:
        controller,functions=None,None
    return dict(app=request.args[0],filename=filename,filetype=filetype,data=data,edit_controller=edit_controller,file_hash=file_hash,controller=controller,functions=functions)

def resolve():
    import difflib
    filename='/'.join(request.args)
    if filename[-3:]=='.py': filetype='python'
    elif filename[-5:]=='.html': filetype='html'
    elif filename[-4:]=='.css': filetype='css'
    elif filename[-3:]=='.js': filetype='js'
    else: filetype='text'
    ### check if file is not there
    path=apath(filename)
    a=open(path,'r').readlines()
    try: b=open(path+'.1','r').readlines()
    except IOError:
        session.flash='Other file, no longer there'
        redirect(URL(r=request,f='edit',args=request.args))
    d=difflib.ndiff(a,b)
    def leading(line):
        z=''
        for k,c in enumerate(line):            
            if c==' ': z+='&nbsp;'
            elif c==' \t': z+='&nbsp;'
            elif k==0 and c=='?': pass
            else: break
        return XML(z)
    def getclass(item):
        if item[0]==' ': return 'normal'
        if item[0]=='+': return 'plus'
        if item[0]=='-': return 'minus'
    if request.vars:
        c=''.join(*[item[2:] for i,item in enumerate(d) if item[0]==' ' or request.vars.has_key('line%i'%i)])
        open(path,'w').write(c)
        session.flash='files merged'
        redirect(URL(r=request,f='edit',args=request.args))
    else:
        diff=TABLE(*[TR(TD('' if not item[:1] in ['+','-'] else INPUT(_type='checkbox',_name='line%i'%i,value=item[0]=='+')),TD(item[0]),TD(leading(item[2:]),TT(item[2:].rstrip())),_class=getclass(item)) for i,item in enumerate(d) if item[0]!='?'])
    return dict(diff=diff,filename=filename)

def edit_language():
    """ admin controller function """
    filename='/'.join(request.args)    
    ### check if file is not there 
    strings=eval(open(apath(filename),'r').read())
    keys=strings.keys()
    keys.sort()
    rows=[]
    rows.append(TR(B(T('Original')),B(T('Translation'))))
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
        response.flash=T("file saved on %(time)s",dict(time=time.ctime()))       
    return dict(app=request.args[0],filename=filename,form=form)

def htmledit():
    """ admin controller function """
    filename='/'.join(request.args)    
    ### check if file is not there 
    data=open(apath(filename),'r').read()
    try:
        data=request.vars.data.replace('\r\n','\n') 
        open(apath(filename),'w').write(data)
        response.flash=T("file saved on %(time)s",dict(time=time.ctime()))       
    except Exception: pass
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
        response.flash=T('ATTENTION: you cannot edit the running application!')
    if os.path.exists(apath('%s/compiled' % app)):
        session.flash=T('application is compiled and cannot be designed')
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
    statics=listdir(apath('%s/static/' % app),'[^\.#].*')
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
            session.flash=T('language file "%(filename)s" created/updated',dict(filename=filename))
            redirect(request.vars.sender)
        elif path[-8:]=='/models/': 
            if not filename[-3:]=='.py': filename+='.py'
            if len(filename)==3: raise SyntaxError
            fn=re.sub('\W','',filename[:-3].lower())
            text='# %s\n%s=SQLDB("sqlite://%s.db")' % (T('try something like'),fn,fn)
        elif path[-13:]=='/controllers/':
            if not filename[-3:]=='.py': filename+='.py'
            if len(filename)==3: raise SyntaxError
            text='# %s\ndef index(): return dict(message="hello from %s")' % (T('try something like'),filename)
        elif path[-7:]=='/views/':
            if not filename[-5:]=='.html': filename+='.html'
            if len(filename)==5: raise SyntaxError
            text="{{extend 'layout.html'}}\n<h1>%s</h1>\n{{=BEAUTIFY(response._vars)}}" % \
                 T('This is the %(filename)s template',dict(filename=filename))
        elif path[-8:]=='/static/':
            text=""
        else:
            redirect(request.vars.sender)
        full_filename=os.path.join(path,filename)
        dirpath=os.path.dirname(full_filename)
        if not os.path.exists(dirpath): os.makedirs(dirpath)
        if os.path.exists(full_filename): raise SyntaxError
        open(full_filename,'w').write(text)
        session.flash=T('file "%(filename)s" created',dict(filename=full_filename[len(path):]))
        redirect(URL(r=request,f='edit',args=[os.path.join(request.vars.location,filename)]))
    except Exception, e:
        session.flash=T('cannot create file')
    redirect(request.vars.sender)

def upload_file(): 
    """ admin controller function """
    try:
        path=apath(request.vars.location)
        filename=re.sub('[^\w\./]+','_',request.vars.filename)
        if path[-8:]=='/models/' and not filename[-3:]=='.py': filename+='.py'
        if path[-13:]=='/controllers/' and not filename[-3:]=='.py': filename+='.py'
        if path[-7:]=='/views/' and not filename[-5:]=='.html': filename+='.html'
        if path[-11:]=='/languages/' and not filename[-3:]=='.py': filename+='.py'
        filename=os.path.join(path,filename)
        dirpath=os.path.dirname(filename)
        if not os.path.exists(dirpath): os.makedirs(dirpath)
        open(filename,'w').write(request.vars.file.file.read())
        session.flash=T('file "%(filename)s" uploaded',dict(filename=filename[len(path):]))
    except Exception: 
        session.flash=T('cannot upload file "%(filename)s"',dict(filename[len(path):]))
    redirect(request.vars.sender)

def errors(): 
    """ admin controller function """
    app=request.args[0] 
    for item in request.vars:
        if item[:7]=='delete_':
            os.unlink(apath('%s/errors/%s' % (app,item[7:])))
    tickets=sorted(os.listdir(apath('%s/errors/' % app)), key=lambda p: os.stat(apath('%s/errors/%s' % (app,p))).st_mtime,reverse=True)
    return dict(app=app,tickets=tickets)


editable = {"controllers": ".py",
            "models" : ".py",
            "views" : ".html",
            }


def make_link (path):
    tryFile = path.replace("\\", "/")
    if (os.path.isabs(tryFile) and os.path.isfile(tryFile)):
        (dir, file) = os.path.split(tryFile)
        (base, ext) = os.path.splitext(file)
        app = request.args[0]
        for key in editable.keys():
           if (ext.lower() == editable[key]) and dir.endswith(app + "/" + key):
                return A('"'+tryFile+'"',_href=URL(r=request,f='edit/%s/%s/%s' % (app, key, file))).xml()
    return ''


def make_links(traceback):
    lwords = traceback.split('"')
    result = lwords[0] if len(lwords) != 0 else ''
    i = 1 
    while i < len(lwords):
        link = make_link(lwords[i])
        if link == '' :
            result += '"' + lwords[i]
        else:
            result += link
            if (i+1 < len(lwords)):
                result += lwords[i+1]
                i = i + 1
        i = i + 1
    return result


class TRACEBACK:
    def __init__ (self, text):
        self.s = make_links(CODE(text).xml())
        
    def xml (self):
        return self.s


def ticket():        
    """ admin controller function """
    if len(request.args)!=2:
        session.flash=T("invalid ticket")
        redirect(URL(r=request,f='site'))
    app=request.args[0]
    ticket=request.args[1]
    e=RestrictedError()
    e.load(apath('%s/errors/%s' % (app,ticket)))
    return dict(app=app,ticket=ticket,traceback=TRACEBACK(e.traceback),code=e.code,layer=e.layer)
    


def update_languages():
    """ admin controller function """
    app=request.args[0]
    update_all_languages(apath(app))
    session.flash=T('languages updated')
    redirect(URL(r=request,f='design/'+app))

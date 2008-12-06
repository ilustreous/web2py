"""
This file is part of web2py Web Framework (Copyrighted, 2007)
Developed by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: GPL v2
"""

import sys; sys.path.append('../gluon')
import os, stat, thread
from template import parse_template
from restricted import restricted
from fileutils import listdir
from myregex import regex_expose
from languages import translator
from sql import SQLDB, SQLField
from sqlhtml import SQLFORM, SQLTABLE
from cache import Cache
import html
import validators
from http import HTTP, redirect
import os, marshal, imp, types, doctest, logging
try: import py_compile
except: logging.warning("unable to import py_compile")
from rewrite import error_message_custom

try: magic=imp.get_magic()
except: is_gae=True
else: is_gae=False

TEST_CODE=r"""
def _TEST():
    import doctest, sys, cStringIO, types, cgi, gluon.fileutils
    if not gluon.fileutils.check_credentials(request):
        raise HTTP(400,web2py_error='invalid credentials')
    stdout=sys.stdout
    html='<h2>Testing controller "%s.py" ... done.</h2><br/>\n' % request.controller
    for key in [key for key in globals() if not key in __symbols__+['_TEST']]:
        if type(eval(key))==types.FunctionType: 
            if doctest.DocTestFinder().find(eval(key)):
                sys.stdout=cStringIO.StringIO()
                name='%s/controllers/%s.py in %s.__doc__' % (request.folder, request.controller, key)
                doctest.run_docstring_examples(eval(key),globals(),False,name=name)
                report=sys.stdout.getvalue().strip()
                if report: pf='failed'
                else: pf='passed'
                html+='<h3 class="%s">Function %s [%s]</h3>'%(pf,key,pf)
                if report: html+=CODE(report,language='web2py',link='/examples/global/vars/').xml()
                html+='<br/>\n'
            else:
                html+='<h3 class="nodoctests">Function %s [no doctests]</h3><br/>'%(key)
    response._vars=html
    sys.stdout=stdout
_TEST()
"""

cfs={} # for speed-up
cfs_lock=thread.allocate_lock() # and thread safety
def getcfs(key,filename,filter=None):
     t=os.stat(filename)[stat.ST_MTIME]
     cfs_lock.acquire()
     item=cfs.get(key,None)
     cfs_lock.release()
     if item and item[0]==t: return item[1]
     if not filter: data=open(filename,'r').read()
     else: data=filter()
     cfs_lock.acquire()
     cfs[key]=(t,data)
     cfs_lock.release()
     return data

def build_environment(request,response,session):
    """
    Build and return evnironment dictionary for controller and view.
    """
    environment={}
    for key in html.__all__: environment[key]=getattr(html,key)
    for key in validators.__all__: environment[key]=getattr(validators,key)
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
    return environment

def save_pyc(filename):
    py_compile.compile(filename)

def read_pyc(filename):
    data=open(filename,'rb').read()
    try: magic=imp.get_magic()
    except: pass
    else:
        if data[:4]!=magic: raise SystemError, "compiled code is incompatible"
    return marshal.loads(data[8:]) 

def compile_views(folder):
    """
    compiles all the views in the applicaiton specified by the
    current folder
    """
    path=os.path.join(folder,'views/')
    for file in listdir(path,'.+\.html$'):
        data=parse_template(file,path)
        filename=os.path.join(folder,'compiled/',('views/'+file[:-5]+'.py').replace('/','_').replace('\\','_'))
        open(filename,'w').write(data)
        save_pyc(filename)
        os.unlink(filename)

def compile_models(folder):
    """
    compiles all the models in the applicaiton specified by the
    current folder
    """
    path=os.path.join(folder,'models/')
    for file in listdir(path,'.+\.py$'):
        data=open(os.path.join(path,file),'r').read()
        filename=os.path.join(folder,'compiled/',('models/'+file).replace('/','_'))
        open(filename,'w').write(data)
        save_pyc(filename)
        os.unlink(filename)

def compile_controllers(folder):
    """
    compiles all the controllers in the applicaiton specified by the
    current folder
    """
    path=os.path.join(folder,'controllers/')
    for file in listdir(path,'.+\.py$'):
        save_pyc(os.path.join(path,file))
        data=open(path+file,'r').read()
        exposed=regex_expose.findall(data)
        for function in exposed:
            command=data+'\n\nresponse._vars=response._caller(%s)' % function
            filename=os.path.join(folder,'compiled/',('controllers/'+file[:-3]).replace('/','_')+'_'+function+'.py')
            open(filename,'w').write(command)
            save_pyc(filename)
            os.unlink(filename)

def run_models_in(environment):
    """
    runs all models (in the app specified by the current folder) 
    in the environment. it tries precompiled models first.
    """
    folder=environment['request'].folder
    path=os.path.join(folder,'compiled/')
    if os.path.exists(path):
         for model in listdir(path,'^models_.+\.pyc$',0):
             restricted(read_pyc(model),environment,layer=model)
    else:
        models=listdir(os.path.join(folder,'models/'),'^\w+\.py$',0)      
        for model in models:
              layer=model
              if is_gae:
                   code=getcfs(model,model,lambda:compile(open(model,'r').read().replace('\r\n','\n'),layer,'exec'))
              else:
                   code=getcfs(model,model,None)
              restricted(code,environment,layer)

def run_controller_in(controller,function,environment):
    """
    runs the controller.function() (for the app specified by 
    the current folder)  in the environment. 
    it tries precompiled controller_function.pyc first.
    """
    # if compiled should run compiled!
    folder=environment['request'].folder
    path=os.path.join(folder,'compiled/')
    if os.path.exists(path):
        filename=os.path.join(path,'controllers_%s_%s.pyc' %(controller,function))
        if not os.path.exists(filename):
            raise HTTP(400,error_message_custom % 'invalid function',
                       web2py_error='invalid function')
        restricted(read_pyc(filename),environment,layer=filename)
    elif function=='_TEST':
        filename=os.path.join(folder,'controllers/%s.py' % controller)
        if not os.path.exists(filename):
            raise HTTP(400,error_message_custom % 'invalid controller',
                       web2py_error='invalid controller')
        environment['__symbols__']=environment.keys()
        code=open(filename,'r').read()
        code+=TEST_CODE
        restricted(code,environment,layer=filename)
    else:
        filename=os.path.join(folder,'controllers/%s.py' % controller)
        if not os.path.exists(filename):
            raise HTTP(400,error_message_custom % 'invalid controller',
                       web2py_error='invalid controller')
        code=open(filename,'r').read()
        exposed=regex_expose.findall(code)
        if not function in exposed: 
            raise HTTP(400,error_message_custom % 'invalid function',
                       web2py_error='invalid function')
        code='%s\n\nresponse._vars=response._caller(%s)\n' % (code,function)
        if is_gae:
            layer=filename+':'+function
            code=getcfs(layer,filename,lambda:compile(code.replace('\r\n','\n'),layer,'exec'))
        restricted(code,environment,filename)
    response=environment['response']
    if response.postprocessing:
        for p in response.postprocessing:
            response._vars=p(response._vars)
    if type(response._vars)==types.StringType:
        response.body=response._vars
    elif type(response._vars)==types.GeneratorType:
        response.body=response._vars
    elif type(response._vars)!=types.DictType:
        response.body=str(response._vars)

def run_view_in(environment):
    """ 
    exectutes the view in resposne.view or generic.html.
    it tries the precompiled views_controller_funciton.pyc first.
    """
    folder=environment['request'].folder
    response=environment['response']
    path=os.path.join(folder,'compiled/')
    if os.path.exists(path):
        filename=os.path.join(path,'views_%s.pyc' % response.view[:-5].replace('/','_'))
        if not os.path.exists(filename): 
             filename=os.path.join(folder,'compiled/','views_generic.pyc')
        if not os.path.exists(filename): 
            raise HTTP(400,error_message_custom % 'invalid view',
                       web2py_error='invalid view')
        code=read_pyc(filename)
        restricted(code,environment,layer=filename) 
    else:
        filename=os.path.join(folder,'views/',response.view)
        if not os.path.exists(filename):
             response.view='generic.html'
        filename=os.path.join(folder,'views/',response.view)
        if not os.path.exists(filename):
             raise HTTP(400,error_message_custom % 'invalid view',
                        web2py_error='invalid view')
        layer=filename
        if is_gae:
            ccode=getcfs(layer,filename,lambda:compile(parse_template(response.view,os.path.join(folder,'views/'),context=environment).replace('\r\n','\n'),layer,'exec'))
        else:
            ccode=parse_template(response.view,os.path.join(folder,'views/'),context=environment)
        restricted(ccode,environment,layer)

def remove_compiled_application(folder):
    try:
        path=os.path.join(folder,'compiled/')
        for file in listdir(path): os.unlink(os.path.join(path,file))
        os.rmdir(path)
    except OSError: pass

def compile_application(folder):
    remove_compiled_application(folder)
    os.mkdir(os.path.join(folder,'compiled/'))
    compile_models(folder)
    compile_controllers(folder)
    compile_views(folder)
    
def test():
    """
    Example:
    >>> import traceback, types
    >>> environment={'x':1}
    >>> open('a.py','w').write('print 1/x')
    >>> save_pyc('a.py')
    >>> os.unlink('a.py')
    >>> if type(read_pyc('a.pyc'))==types.CodeType: print 'code'
    code
    >>> exec read_pyc('a.pyc') in environment
    1
    """
    return

if __name__=='__main__':
   import doctest
   doctest.testmod()

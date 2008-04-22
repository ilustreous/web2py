"""
This file is part of web2py Web Framework (Copyrighted, 2007)
Developed by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: GPL v2
"""

import sys; sys.path.append('../gluon')
from template import parse_template
from restricted import restricted
from fileutils import listdir
from myregex import regex_expose
from http import HTTP
from html import CODE
import os, marshal, imp, types, doctest, logging
try: import py_compile
except: logging.warning("unable to import py_compile")

error_message='<html><body><h1>Invalid request</h1>%s</body></html>'

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

def save_pyc(filename):
    py_compile.compile(filename)

def read_pyc(filename):
    data=open(filename,'rb').read()
    if data[:4]!=imp.get_magic(): 
        raise SystemError, "compiled code is incompatible"
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
        data=open(path+file,'r').read()
        exposed=regex_expose.findall(data)
        for function in exposed:
            command=data+'\n\nresponse._vars=%s()' % function
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
              restricted(open(model,'r').read(),environment,layer=model)

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
            raise HTTP(400,error_message % 'invalid function',
                       web2py_error='invalid function')
        restricted(read_pyc(filename),environment,layer=filename)
    elif function=='_TEST':
        filename=os.path.join(folder,'controllers/%s.py' % controller)
        if not os.path.exists(filename):
            raise HTTP(400,error_message % 'invalid controller',
                       web2py_error='invalid controller')
        environment['__symbols__']=environment.keys()
        code=open(filename,'r').read()
        code+=TEST_CODE
        restricted(code,environment,layer=filename)
    else:
        filename=os.path.join(folder,'controllers/%s.py' % controller)
        if not os.path.exists(filename):
            raise HTTP(400,error_message % 'invalid controller',
                       web2py_error='invalid controller')
        code=open(filename,'r').read()
        exposed=regex_expose.findall(code)
        if not function in exposed: 
            raise HTTP(400,error_message % 'invalid function',
                       web2py_error='invalid function')
        code+='\n\nresponse._vars=%s()' % function        
        restricted(code,environment,layer=filename)
    response=environment['response']
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
            raise HTTP(400,error_message % 'invalid view',
                       web2py_error='invalid view')
        code=read_pyc(filename)
        #response.body=restricted(code,environment,layer=filename) 
        restricted(code,environment,layer=filename) 
    else:
        filename=os.path.join(folder,'views/',response.view)
        if not os.path.exists(filename):
             response.view='generic.html'
        filename=os.path.join(folder,'views/',response.view)
        if not os.path.exists(filename):
             raise HTTP(400,error_message % 'invalid view',
                        web2py_error='invalid view')
        code=parse_template(response.view,os.path.join(folder,'views/'))
        #response.body=restricted(code,environment,layer=filename) 
        restricted(code,environment,layer=filename)

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

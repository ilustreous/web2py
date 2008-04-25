#   Programmer: limodou
#   E-mail:     limodou@gmail.com
#
#   Copyleft 2008 limodou
#
#   Distributed under the terms of the BSD license.

import os, sys, code, logging
from optparse import OptionParser
from glob import glob
from gluon.fileutils import untar

def env(app, import_models=False, dir=''):
    import gluon.html as html
    import gluon.validators as validators
    from gluon.http import HTTP, redirect
    from gluon.languages import translator
    from gluon.cache import Cache
    from gluon.globals import Request, Response, Session
    from gluon.sql import SQLDB, SQLField
    from gluon.sqlhtml import SQLFORM, SQLTABLE

    request=Request()
    response=Response()
    session=Session()
    request.application = app
    
    if not dir:
        request.folder = os.path.join('applications', app)
    else:
        request.folder = dir
        
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
    
    if import_models:
        model_path = os.path.join(request.folder,'models', '*.py')
        for f in glob(model_path):
            fname, ext = os.path.splitext(f)
            execfile(f, environment)
    return environment

def run(appname, plain=False, import_models=False, startfile=None):
    path=os.path.join('applications',appname)
    if not os.path.exists(path):
        if raw_input('application %s does not exit, create (y/n)?' % appname).lower() in ['y','yes']:
            os.mkdir(path)
            untar('welcome.tar',path)    
        else: return

    _env = env(appname, import_models)
    
    if startfile:
        pythonrc = os.environ.get("PYTHONSTARTUP")
        if pythonrc and os.path.isfile(pythonrc):
            try:
                execfile(pythonrc)
            except NameError:
                pass
        execfile(startfile, _env)
    else:
        if not plain:
            try:
                import IPython
                shell = IPython.Shell.IPShell(argv=[], user_ns=_env)
                shell.mainloop()
                return
            except:
                logging.warning('import IPython error, use default python shell')
        try:
            import readline, rlcompleter
        except ImportError:
            pass
        else:
            readline.set_completer(rlcompleter.Completer(_env).complete)
            readline.parse_and_bind("tab:complete")

        pythonrc = os.environ.get("PYTHONSTARTUP")
        if pythonrc and os.path.isfile(pythonrc):
            try:
                execfile(pythonrc)
            except NameError:
                pass
        code.interact(local=_env)

def get_usage():
    usage = """
  %prog [options] pythonfile
"""
    return usage

def execute_from_command_line(argv=None):
    if argv is None:
        argv = sys.argv

    parser = OptionParser(usage=get_usage())

    parser.add_option('-S', '--shell',
                  dest='shell', metavar='APPNAME',
                  help='run web2py in interactive shell or IPython(if installed) with specified appname')
    parser.add_option('-P', '--plain', action='store_true', default=False,
                  dest='plain',
                  help='only use plain python shell, should be used with --shell option')
    parser.add_option('-M', '--import_models', action='store_true', default=False,
                  dest='import_models',
                  help='auto import model files, default is False, should be used with --shell option')
    parser.add_option('-R', '--run', dest='run', metavar='PYTHON_FILE', default='',
                  help='run PYTHON_FILE in web2py environment, should be used with --shell option')

    options, args = parser.parse_args(argv[1:])

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    if len(args) > 0:
        startfile = args[0]
    else:
        startfile = ''
    run(options.shell, options.plain, startfile=startfile)

if __name__ == '__main__':
    execute_from_command_line()
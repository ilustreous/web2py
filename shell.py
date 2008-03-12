#   Programmer: limodou
#   E-mail:     limodou@gmail.com
#
#   Copyleft 2008 limodou
#
#   Distributed under the terms of the BSD license.

import os, sys
import gluon.html as html
import gluon.validators as validators
from gluon.http import HTTP, redirect
from gluon.languages import translator
from gluon.cache import Cache
from gluon.globals import Request, Response, Session
from gluon.sql import SQLDB, SQLField
from gluon.sqlhtml import SQLFORM, SQLTABLE
from optparse import OptionParser

def env(app):
    request=Request()
    response=Response()
    session=Session()
    
    request.folder = os.path.join('applications', app)
    
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
    return environment

def run(app):
    import code
    imported_objects = env(app)
    try:
        import readline
    except ImportError:
        pass
    else:
        import rlcompleter
        readline.set_completer(rlcompleter.Completer(imported_objects).complete)
        readline.parse_and_bind("tab:complete")

    pythonrc = os.environ.get("PYTHONSTARTUP")
    if pythonrc and os.path.isfile(pythonrc):
        try:
            execfile(pythonrc)
        except NameError:
            pass
    code.interact(local=imported_objects)

def get_usage():
    usage = """
  %prog app
"""
    return usage

def execute_from_command_line(argv=None):
    if argv is None:
        argv = sys.argv

    parser = OptionParser(usage=get_usage())
    options, args = parser.parse_args(argv[1:])

    if len(args) != 1:
        parser.print_help()
        sys.exit(0)

    run(args[0])

if __name__ == '__main__':
    execute_from_command_line()
"""
This is a WSGI handler for Apache
Requires apache+mod_wsgi. In httpd.conf put something like:

  LoadModule wsgi_module modules/mod_wsgi.so
  WSGIScriptAlias / /path/to/wsgihandler.py

"""

import sys, os
sys.path.insert(0,'')
path=os.path.dirname(os.path.abspath(__file__))
if not path in sys.path: sys.path.append(path)

import gluon.main
application=gluon.main.wsgibase
## or
# application=gluon.main.wsgibase_with_logging
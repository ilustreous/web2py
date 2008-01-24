"""
in apache with mod_wsgi put something like:

  LoadModule wsgi_module modules/mod_wsgi.so
  WSGIScriptAlias / /path/to/wsgihandler.py

"""

import gluon.main
application=gluon.main.wsgibase

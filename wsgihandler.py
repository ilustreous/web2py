"""
This is a WSGI handler for Apache
Requires apache+mod_wsgi. In httpd.conf put something like:

  LoadModule wsgi_module modules/mod_wsgi.so
  WSGIScriptAlias / /path/to/wsgihandler.py

"""

import gluon.main
application=gluon.main.wsgibase
## or
# application=gluon.main.wsgibase_with_logging
"""
This is a handler for lighttpd+fastcgi
This file has to be in the PYTHONPATH
Put something like this in the lighttpd.conf file:

  server.port = 8000
  server.bind = "127.0.0.1"
  server.event-handler = "freebsd-kqueue"
  server.modules = ( "mod_rewrite", "mod_fastcgi" )
  server.error-handler-404 = "/test.fcgi"
  server.document-root = "/somewhere/web2py/"
  server.errorlog      = "/tmp/error.log"
  fastcgi.server =    ( ".fcgi" =>
                        ( "localhost" =>
                            ( "min-procs" => 1,
                              "socket"    => "/tmp/fcgi.sock"
                            )
                        )
                    )
"""

import gluon.main
import gluon.contrib.gateways.fcgi as fcgi
application=gluon.main.wsgibase

## or
# application=gluon.main.wsgibase_with_logging
fcgi.WSGIServer(application,bindAddress='/tmp/fcgi.sock').run()

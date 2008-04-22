import gluon.main
import gluon.contrib.gateways.fcgi as fcgi
import wsgiref.handlers

application=gluon.main.wsgibase
wsgiref.handlers.CGIHandler().run(application)

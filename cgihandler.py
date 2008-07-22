import gluon.main, wsgiref.handlers

wsgiref.handlers.CGIHandler().run(gluon.main.wsgibase)

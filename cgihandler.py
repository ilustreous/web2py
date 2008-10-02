import time,os,sys,logging
import wsgiref.handlers
import gluon.main

wsgiref.handlers.CGIHandler().run(gluon.main.wsgibase)

"""
This file is part of web2py Web Framework (Copyrighted, 2007)
Developed by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: GPL v2
"""

import sys, cStringIO, cPickle, traceback, copy, cgi, types, time
from random import random
from html import BEAUTIFY

__all__=['RestrictedError','restricted']

class RestrictedError:
    """
    class used to wrap an exception that occurs in the restricted environment
    below. the traceback is used to log the exception and generate a ticket.
    """
    def __init__(self,layer='',code='',output='',environment={}):
        """
        layer here is some description of where in the system the exception
        occurred.
        """
        self.layer=layer
        self.code=code
        self.output=output
        self.traceback=traceback.format_exc()
        self.environment=environment

    def log(self,request):
        """
        logs the exeption.
        """
        a=request.application
        d={'layer':str(self.layer),
           'code':str(self.code),
           'output':str(self.output),
           'traceback':str(self.traceback)}
        f=request.env.remote_addr+'.'+str(int(time.time()))+'.'+str(random())[2:]
        cPickle.dump(d,open(request.folder+'errors/'+f,'wb'))
        return '<a href="/admin/default/ticket/%s/%s" target="_blank">%s/%s</a>' % (a,f,a,f)
    def load(self,file):
        """
        loads a logged exception.
        """
        d=cPickle.load(open(file,'rb'))
        self.layer=d['layer']
        self.code=d['code']
        self.output=d['output']
        self.traceback=d['traceback']

def restricted(code,environment={},layer='Unkown'):
    """
    runs code in evrionment and returns the output. if an exeception occurs 
    in code it raises a RestrictedError containg the traceback. layer is passed
    to RestrictedError to identify where the error occurred.
    """
    try: 
        if type(code)==types.CodeType: ccode=code
        else: ccode=compile(code,layer,'exec')             
        exec ccode in environment
    except Exception, exception:
        raise RestrictedError(layer,code,'',environment)


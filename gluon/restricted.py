#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
This file is part of web2py Web Framework (Copyrighted, 2007)
Developed by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: GPL v2
"""

import sys
import cStringIO
import cPickle
import traceback
import copy
import cgi
import types
import time
import os
import uuid
import datetime
from html import BEAUTIFY
from http import HTTP

__all__ = ['RestrictedError', 'restricted']


class RestrictedError:

    """
    class used to wrap an exception that occurs in the restricted environment
    below. the traceback is used to log the exception and generate a ticket.
    """

    def __init__(
        self,
        layer='',
        code='',
        output='',
        environment={},
        ):
        """
        layer here is some description of where in the system the exception
        occurred.
        """

        self.layer = layer
        self.code = code
        self.output = output
        if layer:
            self.traceback = traceback.format_exc()
        else:
            self.traceback = '(no error)'
        self.environment = environment

    def log(self, request):
        """
        logs the exeption.
        """

        a = request.application
        d = {
            'layer': str(self.layer),
            'code': str(self.code),
            'output': str(self.output),
            'traceback': str(self.traceback),
            }
        f = '%s.%s.%s' % (request.client.replace(':', '_'),
                          datetime.datetime.now().strftime('%Y-%m-%d.%H-%M-%S'
                          ), uuid.uuid4())
        cPickle.dump(d, open(os.path.join(request.folder, 'errors', f),
                     'wb'))
        return '%s/%s' % (a, f)

    def load(self, file):
        """
        loads a logged exception.
        """

        d = cPickle.load(open(file, 'rb'))
        self.layer = d['layer']
        self.code = d['code']
        self.output = d['output']
        self.traceback = d['traceback']


def restricted(code, environment={}, layer='Unkown'):
    """
    runs code in evrionment and returns the output. if an exeception occurs 
    in code it raises a RestrictedError containg the traceback. layer is passed
    to RestrictedError to identify where the error occurred.
    """

    try:
        if type(code) == types.CodeType:
            ccode = code
        else:
            ccode = compile(code.replace('\r\n', '\n'), layer, 'exec')
        exec ccode in environment
    except HTTP:
        raise
    except Exception, exception:
        raise RestrictedError(layer, code, '', environment)



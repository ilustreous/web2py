#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
This file is part of web2py Web Framework (Copyrighted, 2007)
Developed by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: GPL v2
"""

__all__ = ['HTTP', 'redirect']

defined_status = {
    200: 'OK',
    201: 'CREATED',
    202: 'ACCEPTED',
    203: 'NON-AUTHORITATIVE INFORMATION',
    204: 'NO CONTENT',
    205: 'RESET CONTENT',
    206: 'PARTIAL CONTENT',
    301: 'MOVED PERMANENTLY',
    302: 'FOUND',
    303: 'SEE OTHER',
    304: 'NOT MODIFIED',
    305: 'USE PROXY',
    307: 'TEMPORARY REDIRECT',
    400: 'BAD REQUEST',
    401: 'UNAUTHORIZED',
    403: 'FORBIDDEN',
    404: 'NOT FOUND',
    405: 'METHOD NOT ALLOWED',
    406: 'NOT ACCEPTABLE',
    407: 'PROXY AUTHENTICATION REQUIRED',
    408: 'REQUEST TIMEOUT',
    409: 'CONFLICT',
    410: 'GONE',
    411: 'LENGHT REQUIRED',
    412: 'PRECONDITION FAILED',
    413: 'REQUEST ENTITY TOO LARGE',
    414: 'REQUEST-URI TOO LONG',
    415: 'UNSUPPORTED MEDIA TYPE',
    416: 'REQUESTED RANGE NOT SATISFIABLE',
    417: 'EXPECTATION FAILED',
    500: 'INTERNAL SERVER ERROR',
    501: 'NOT IMPLEMENTED',
    502: 'BAD GATEWAY',
    503: 'SERVICE UNAVAILABLE',
    504: 'GATEWAY TIMEOUT',
    505: 'HTTP VERSION NOT SUPPORTED',
    }


class HTTP(BaseException):

    def __init__(
        self,
        status,
        body='',
        **headers
        ):
        self.args = (status, body, headers)
        if status in defined_status:
            self.status = '%d %s' % (status, defined_status[status])
        else:
            self.status = str(status) + ' '
        self.body = body
        if not headers.has_key('Content-Type'):
            headers['Content-Type'] = 'text/html'
        self.headers = headers

    def to(self, responder):
        headers = []
        for (k, v) in self.headers.items():
            if isinstance(v, list):
                for item in v:
                    headers.append((k, str(item)))
            else:
                headers.append((k, str(v)))
        responder(self.status, headers)
        if hasattr(self.body, '__iter__') and not isinstance(self.body,
                str):
            return self.body
        body = str(self.body)
        self.headers['Content-Length'] = len(body)
        return [body]


def redirect(location, how=303):
    location = location.replace('\r', '%0D').replace('\n', '%0A')
    raise HTTP(how, 'You are being redirected <a href="%s">here</a>'
                % location, Location=location)



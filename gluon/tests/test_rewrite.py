import sys
import os
import logging
sys.path.append(os.path.realpath('../'))

import unittest
import tempfile
from html import URL
from http import HTTP

oldOpen = open
def newOpen(filename, mode='rb'):
    if filename != 'routes.py':
        return oldOpen(filename, mode)
    else:
        try: import cStringIO as StringIO
        except ImportError, e: import StringIO
        return StringIO.StringIO('''\
routes_in=( ('/js/(?P<js>[\w\./_-]+)','/init/static/js/\g<js>'), )
routes_out=( ('/init/static/js/(?P<js>[\w\./_-]+)','/js/\g<js>'), )
routes_onerror = (
     ('*/401' , '/init/default/login')
    ,('init/501' , '/init/default/logout')
    ,('*/404' , '!')
    ,('test/*' , '/init/default/login2')
    ,('*/*', '/init/default/error')
)
error_message = 'error_message'
error_message_ticket = 'error_message_ticket'
''')

bodydict = {
     '/':'/'
    ,'/init/static/js/blargh.js':'/init/static/js/blargh.js'
    ,'/test/static/js/blargh.js':'/init/static/js/blargh.js'
    ,'/init/default/login':'/init/default/login'
    ,'/init/default/error':'/init/default/error'
    ,'/init/static/error':'/init/static/error'
    ,'/init/static/lastResort.html?code=500&ticket=None':'lastResort'
    }

def newExists(pathname):
    if pathname == 'routes.py': return True
    else: return os.path.exists(pathname)

def NullFunction(*args, **kwargs):
    return

def fakeWSGIInApp(envir, responder):
    response = HTTP(envir.get('ERROR_CODE', 200), bodydict.get(envir.get('PATH_INFO'), "404'd"))
    retval = response.to(responder)
    return retval

def fakeWSGIOutApp(envir, responder):
    args = envir.get('PATH_INFO').split('/')
    response = HTTP(envir.get('ERROR_CODE', 200), URL(a=args[1], c=args[2], f=args[3], args=args[4:]) )
    retval = response.to(responder)
    return retval

def fakeWSGIERRApp(envir, responder):
    codedict = envir.get('CODE_DICT', {})
    body = envir.get('PATH_INFO')
    code = codedict.get(envir.get('PATH_INFO'), 200)
    if envir.get('PATH_INFO') not in codedict:
        body = bodydict.get(envir.get('PATH_INFO'))
    else:
        body = "Complete Utter Failure"
    response = HTTP(code, body)
    retval = response.to(responder)
    return retval

    
os.path.exists = newExists
try: __builtins__.open = newOpen
except: __builtins__['open'] = newOpen
logging.warning = NullFunction

import rewrite

class InboundRoutesTest(unittest.TestCase):
    def setUp(self):
        self.wsgibase, self.NullFunction = rewrite.rewrite(fakeWSGIInApp, NullFunction)

    def testNoModify(self):
        self.envir = dict( PATH_INFO = "/", REMOTE_ADDR = "localhost" )
        self.response = self.wsgibase(self.envir, NullFunction)
        self.assertEqual(self.response, ["/"], "Got wrong path back: %s" % self.response[0] )

    def testInboundRouting(self):
        self.envir = dict( PATH_INFO = "/js/blargh.js", REMOTE_ADDR = "localhost" )
        self.response = self.wsgibase(self.envir, NullFunction)
        self.assertEqual(self.response, ["/init/static/js/blargh.js"], "Got wrong path back.")

class CustomErrorMessagesTest(unittest.TestCase):
    def testCustomErrorMessages(self):
        self.assertEqual(rewrite.error_message, "error_message", "Custom default error message not assigned.")
        self.assertEqual(rewrite.error_message_ticket, "error_message_ticket", "Custom default ticket error message not assigned." )

class OutboundRoutesURLTranslationTest(unittest.TestCase):
    def setUp(self):
        self.wsgibase, self.NullFunction = rewrite.rewrite(fakeWSGIOutApp, NullFunction)

    def testOutboundRouting(self):
        self.envir = dict( PATH_INFO = "/js/blargh.js", REMOTE_ADDR = "localhost" )
        self.response = self.wsgibase(self.envir, NullFunction)
        self.assertEqual(self.response, ["/init/static/js/blargh.js"], "Got wrong path back: %s" % self.response)

class ErrorHandlingRoutesTest(unittest.TestCase):
    def setUp(self):
        self.wsgibase, self.NullFunction = rewrite.rewrite(fakeWSGIERRApp, NullFunction)

    def testNoErrorHandling(self):
        codedict = {}
        self.envir = dict( PATH_INFO = "/js/blargh.js"
                         , REMOTE_ADDR = "localhost"
                         , CODE_DICT = codedict)
        self.response = self.wsgibase(self.envir, NullFunction)
        self.assertEqual(self.response, ["/init/static/js/blargh.js"], "Got wrong path back: %s" % self.response)
        
    def testApplicationsSpecificErrorHandling(self):
        codedict = {'/init/static/js/blargh.js': 501 }
        self.envir = dict( PATH_INFO = "/js/blargh.js"
                         , REMOTE_ADDR = "localhost"
                         , CODE_DICT = codedict)
        self.response = self.wsgibase(self.envir, NullFunction)
        self.assertEqual(self.response, ['You are being redirected <a href="/init/default/logout?code=501&ticket=None">here</a>.'], "Got wrong response back: %s" % self.response)

    def testListOrderPrecedence(self):
        codedict = {'/test/static/js/blargh.js': 501 }
        self.envir = dict( PATH_INFO = '/test/static/js/blargh.js'
                         , REMOTE_ADDR = "localhost"
                         , CODE_DICT = codedict)
        self.response = self.wsgibase(self.envir, NullFunction)
        self.assertEqual(self.response, ['You are being redirected <a href="/init/default/login2?code=501&ticket=None">here</a>.'], "Got wrong response back: %s" % self.response)

    def testSpecificErrorHandling(self):
        codedict = {'/init/static/js/blargh.js': 401 }
        self.envir = dict( PATH_INFO = "/js/blargh.js"
                         , REMOTE_ADDR = "localhost"
                         , CODE_DICT = codedict)
        self.response = self.wsgibase(self.envir, NullFunction)
        self.assertEqual(self.response, ['You are being redirected <a href="/init/default/login?code=401&ticket=None">here</a>.'], "Got wrong response back: %s" % self.response)

    def testDefaultErrorHandling(self):
        codedict = {'/init/static/js/blargh.js': 405 }
        self.envir = dict( PATH_INFO = "/js/blargh.js"
                         , REMOTE_ADDR = "localhost"
                         , CODE_DICT = codedict)
        self.response = self.wsgibase(self.envir, NullFunction)
        self.assertEqual(self.response, ['You are being redirected <a href="/init/default/error?code=405&ticket=None">here</a>.'], "Got wrong response back: %s" % self.response)

    def testOverrideErrorHandling(self):
        codedict = {'/init/static/js/blargh.js': 404 }
        self.envir = dict( PATH_INFO = "/js/blargh.js"
                         , REMOTE_ADDR = "localhost"
                         , CODE_DICT = codedict)
        self.response = self.wsgibase(self.envir, NullFunction)
        self.assertEqual(self.response, ['Complete Utter Failure'], "Got wrong response back: %s" % self.response)

    def testErrorHandlingError(self):
        codedict = {'/init/static/js/blargh.js': 405
                    ,'/init/default/error': 500
                    ,'/init/default/error?code=405&ticket=None' : 500
                    ,'/init/default/error?code=500&ticket=None' : 500
                    ,'/init/static/lastResort.html?code=500&ticket=None' : 404}
        self.envir = dict( PATH_INFO = "/js/blargh.js"
                         , REMOTE_ADDR = "localhost"
                         , CODE_DICT = codedict)
        self.response = self.wsgibase(self.envir, NullFunction)
        self.assertEqual(self.response, ['You are being redirected <a href="/init/default/error?code=405&ticket=None">here</a>.'], "Got wrong response back: %s" % self.response)
        r = self.response[0]
        newURL = r[r.find('href="')+6:r.rfind('">')]
        self.envir = dict( PATH_INFO = newURL
                         , REMOTE_ADDR = "localhost"
                         , CODE_DICT = codedict)
        self.response = self.wsgibase(self.envir, NullFunction)
        self.assertEqual(self.response, ["Complete Utter Failure"], "Got response: %s" % self.response)

if __name__ == '__main__':
    unittest.main()
import os
import re
import logging
import urllib
from http import HTTP

regex_at=re.compile('(?<!\\\\)\$[\w_]+')
regex_iter=re.compile(r'.*code=(?P<code>\d+)&ticket=(?P<ticket>.+).*')
error_message='<html><body><h1>Invalid request</h1></body></html>'
error_message_custom='<html><body><h1>%s</h1></body></html>'
error_message_ticket='<html><body><h1>Internal error</h1>Ticket issued: <a href="/admin/default/ticket/%(ticket)s" target="_blank">%(ticket)s</a></body></html>'
symbols={}

if os.path.exists('routes.py'):
    try: exec(open('routes.py','r').read()) in symbols
    except SyntaxError, e:
        logging.warning('Your routes.py has a syntax error.  Please fix it before you restart web2py')
        raise e
    if 'error_message' in symbols: error_message = symbols['error_message']
    if 'error_message_ticket' in symbols: error_message_ticket = symbols['error_message_ticket']


def rewrite(wsgibase,URL):
    global symbols
    if not os.path.exists('routes.py'): return wsgibase,URL
    logging.warning('URL rewrite is on. configuration in route.py')
    routes_in=[]
    if 'routes_in' in symbols:
        for k,v in symbols['routes_in']:
            if not k[0]=='^': k='^%s'%k
            if not k[-1]=='$': k='%s$'%k
            if k.find(':')<0: k='^.*:%s' % k[1:]
            for item in regex_at.findall(k):
                k=k.replace(item,'(?P<%s>[\\w_]+)'%item[1:])
            for item in regex_at.findall(v):
                v=v.replace(item,'\\g<%s>'%item[1:])
            routes_in.append((re.compile(k,re.DOTALL),v))
    routes_out=[]
    if 'routes_out' in symbols:
        for k,v in symbols['routes_out']:
            if not k[0]=='^': k='^%s'%k
            if not k[-1]=='$': k='%s$'%k
            for item in regex_at.findall(k):
                k=k.replace(item,'(?P<%s>\\w+)'%item[1:])
            for item in regex_at.findall(v):
                v=v.replace(item,'\\g<%s>'%item[1:])
            routes_out.append((re.compile(k,re.DOTALL),v))
    def filter_in(e):
        path=e['PATH_INFO']
        key=e['REMOTE_ADDR']+':'+path
        for regex,value in routes_in:
            if regex.match(key): 
                path=regex.sub(value,key)
                break
        e['PATH_INFO']=path
        return e
    def filter_out(url):
        items=url.split('?',1)
        for regex,value in routes_out:
            if regex.match(items[0]): return '?'.join([regex.sub(value,items[0])]+items[1:])
        return url
    def handle_errors(envir, responder, error_list):
        class responder_wrapper:
            def __init__(self, responder):
                self.theRealSlimShady = responder
                self.status = None
                self.headers = None
            def storeValues(self, status, headers):
                self.status = status
                self.headers = headers
            def sendIt(self):
                self.theRealSlimShady(self.status, self.headers)
        error_map = dict([(x[0], x) for x in error_list])
        error_list = list(error_list)
        pre_translated_path = envir['PATH_INFO']
        respond_wrap = responder_wrapper(responder)
        routed_environ = filter_in(envir)
        app = routed_environ['PATH_INFO'].strip('/').split('/')
        if len(app) > 0: app = app[0]
        else: app = 'init'   ### THIS NEEDS FIX
        data = wsgibase(routed_environ, respond_wrap.storeValues)
        http_status = int(respond_wrap.status.split()[0])
        body = data
        if http_status >= 400:
            query = regex_iter.search(envir.get('query_string', ''))
            if query: query = query.groupdict()
            else: query = {}
            code = query.get('code')
            ticket = dict(respond_wrap.headers).get('web2py_error', 'None None')
            if 'ticket' in ticket: ticket = ticket.split()[1]
            else: ticket = 'None'
            redir = []
            for handler in [  '%s/%s' % (app, http_status)
                            , '%s/*' % app
                            , '*/%s' % http_status
                            , '*/*'
                            , None ]:
                if handler and handler in error_map:
                    error_redir = error_map[handler]
                    if error_redir[1] == '!':
                        redir = []
                        break
                    else:
                        redir.append(error_redir)
            redir.sort(lambda x, y: error_list.index(x) - error_list.index(y))
            if redir and not pre_translated_path.startswith(redir[0][1]) and http_status != code:
                redir = redir[0][1]
            elif len(redir) > 1: redir = redir[1][1]
            else: redir = None
            if redir:
                if '?' in redir: url = redir+'&'
                else: url = redir+'?'
                url += "code=%s&ticket=%s"
                url %= (http_status, ticket)
                response = HTTP(303
                                ,'You are being redirected <a href="%s">here</a>.' % url
                                ,Location=url)
                return response.to(responder)
                
        respond_wrap.sendIt()
        return body
    if 'routes_onerror' in symbols:
        wsgibase_new=lambda e, r: handle_errors(e, r, symbols['routes_onerror'])
    else:
        wsgibase_new=lambda e,r: wsgibase(filter_in(e),r)
    URL_new=lambda *a,**b: filter_out(URL(*a,**b))
    return wsgibase_new, URL_new
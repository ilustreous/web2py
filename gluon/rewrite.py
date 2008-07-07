import os, re, logging

regex_at=re.compile('(?<!\\\\)\$[\w_]+')

def rewrite(wsgibase,URL):
    if not os.path.exists('routes.py'): return wsgibase,URL
    logging.warning('URL rewrite is on. configuration in route.py')
    symbols={}
    exec(open('routes.py','r').read()) in symbols
    routes_in=[]
    if symbols.has_key('routes_in'):
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
    if symbols.has_key('routes_out'):
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
    wsgibase_new=lambda e,r: wsgibase(filter_in(e),r)
    URL_new=lambda *a,**b: filter_out(URL(*a,**b))
    return wsgibase_new, URL_new
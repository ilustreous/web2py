import os, re

def rewrite(wsgibase,URL):
    if not os.access('routes.py',os.R_OK):
        return wsgibase,URL
    print '***************** ATTENTION *******************'
    print '* you are using web2py rewrite feature        *'
    print '* the use of this feature is discouraged      *'
    print '* unless you really know what you are doing   *'
    print '***********************************************'
    symbols={}
    exec(open('routes.py','r').read()) in symbols
    routes_in=[(re.compile(k),v) for k,v in symbols['routes_in']]
    routes_out=[(re.compile(k),v) for k,v in symbols['routes_out']]    
    def filter_in(e):
        key=e['REMOTE_ADDR']+':'+e['PATH_INFO']
        for regex,value in routes_in:
            if regex.match(key): 
                key=regex.sub(value,key)
        e['REMOTE_ADDR'],e['PATH_INFO']=key.split(':',1)
        return e
    def filter_out(url):
        items=url.split('?',1)
        for regex,value in routes_out:
            if regex.match(items[0]): return '?'.join([regex.sub(value,items[0])]+items[1:])
        return url
    wsgibase_new=lambda e,r: wsgibase(filter_in(e),r)
    URL_new=lambda *a,**b: filter_out(URL(*a,**b))
    return wsgibase_new, URL_new
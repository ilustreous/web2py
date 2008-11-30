from gluon.contrib.memcache.memcache import Client

"""
examle of usage:

cache.memcache=MemcacheClient(request,[127.0.0.1:11211],debug=true)
"""

import cPickle as pickle

class MemcacheClient(Client):
    def __init__(self, request, servers, debug=0, pickleProtocol=0,
                 pickler=pickle.Pickler, unpickler=pickle.Unpickler,
                 pload=None, pid=None):
        self.request=request
        Client.__init__(self,servers,debug,pickleProtocol,
                        pickler,unpickler,pload,pid)
    def __call__(self,key,f,time_expire=300):
        key='%s/%s' % (self.request.application,key)
        dt=time_expire
        value=None
        obj=self.get(key)
        if obj and obj[0]>time.time()-dt:
            value=obj[1]            
        elif f is None:
            if obj: self.delete(key)
        else:
            value=f()
            self.set((time.time(),value))
        return value
    def increment(self,key,value=1):
        key='%s/%s' % (self.request.application,key)
        obj=self.get(key)
        if obj: value=obj[1]+value
        self.set((time.time(),value))
        return value
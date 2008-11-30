"""
This file is part of web2py Web Framework (Copyrighted, 2007)
Developed by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: GPL v2
"""

import time, portalocker, shelve, thread, cPickle, os, logging
try: import dbhash
except: logging.warning("unable to import dbhash")

__all__=['Cache']

class CacheInRam(object):
    locker=thread.allocate_lock()
    storage={}
    def __init__(self,request=None):
        self.request=request
    def __call__(self,key,f,time_expire=300):
        if self.request: key='%s/%s' % (self.request.application,key)
        else: key='/%s'%key
        dt=time_expire
        self.locker.acquire()
        value=None
        if self.storage.has_key(key) and self.storage[key][0]>time.time()-dt:
            value=self.storage[key][1]            
        elif f is None:
            if self.storage.has_key(key): del self.storage[key]
        else:
            try:
                value=f()
                self.storage[key]=(time.time(),value)
            except BaseException, e:
                self.locker.release()
                raise e
        self.locker.release()
        return value
    def increment(self,key,value=1):
        key='%s/%s' % (self.request.application,key)
        self.locker.acquire()
        try:
            if self.storage.has_key(key):
                value=self.storage[key][1]+value
            self.storage[key]=(time.time(),value)
        except BaseException,e:
            self.locker.release()
            raise e
        self.locker.release()
        return value

class CacheOnDisk(object):
    def __init__(self,request):
	self.request=request
        self.locker=open(os.path.join(request.folder,'cache/cache.lock'),'a')
        self.shelve_name=os.path.join(request.folder,'cache/cache.shelve')
    def __call__(self,key,f,time_expire=300): 
        key='%s/%s' % (self.request.application,key)
        dt=time_expire
        portalocker.lock(self.locker, portalocker.LOCK_EX)
        storage=shelve.open(self.shelve_name)
        value=None
        if storage.has_key(key) and storage[key][0]>time.time()-dt:
            value=storage[key][1]
        elif f is None:
            if storage.has_key(key): del storage[key]
        else:
            try:
                value=f()
                storage[key]=(time.time(),value)
                storage.sync()
            except BaseException, e:
                portalocker.unlock(self.locker)       
                raise e
        portalocker.unlock(self.locker)
        return value
    def increment(self,key,value=1):
        key='%s/%s' % (self.request.application,key)
        portalocker.lock(self.locker, portalocker.LOCK_EX)
        storage=shelve.open(self.shelve_name)
        try:
            if storage.has_key(key):
                value=storage[key][1]+value
            storage[key]=(time.time(),value)
            storage.sync()
        except BaseException, e:
            portalocker.unlock(self.locker)       
            raise e
        portalocker.unlock(self.locker)
        return value

class Cache(object):
    def __init__(self,request):
        self.ram=CacheInRam(request)
        try: self.disk=CacheOnDisk(request)
        except IOError: logging.warning('no cache.disk')
    def __call__(self,key=None,time_expire=300,cache_model=None):
        if not cache_model: cache_model=self.ram
        def tmp(func):
             return lambda: cache_model(key,func,time_expire)
        return tmp

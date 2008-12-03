"""
This file is part of web2py Web Framework (Copyrighted, 2007)
Developed by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: GPL v2
"""

import time, portalocker, shelve, thread, cPickle, os, logging, re
try: import dbhash
except: logging.warning("unable to import dbhash")

__all__=['Cache']

class CacheInRam(object):
    locker=thread.allocate_lock()
    meta_storage={}
    def __init__(self,request=None):
        self.locker.acquire()
        self.request=request
        if request: app=request.application
        else: app=''
        if not self.meta_storage.has_key(app):
            self.storage=self.meta_storage[app]={}
        else:
            self.storage=self.meta_storage[app]
        self.locker.release()
    def clear(self,regex=None):
        self.locker.acquire()
        storage=self.storage
        if regex==None:
            storage.clear()
        else:
            r=re.compile(regex)
            for key in storage.keys():
                if r.match(key): del storage[key]
        self.locker.release()
    def __call__(self,key,f,time_expire=300):
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
    def clear(self,regex=None):
        portalocker.lock(self.locker, portalocker.LOCK_EX)
        storage=shelve.open(self.shelve_name)
        if regex==None:
            storage.clear()
        else:
            r=re.compile(regex)
            for key in storage.keys():
                if r.match(key): del storage[key]
            storage.sync()
        portalocker.unlock(self.locker)
    def __call__(self,key,f,time_expire=300): 
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

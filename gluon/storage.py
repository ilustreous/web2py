"""
This file is part of web2py Web Framework (Copyrighted, 2007)
Developed by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: GPL v2
"""

import cPickle, portalocker

__all__=['Storage','load_storage','save_storage']

class Storage(dict):
    """
    A Storage object is like a dictionary except `obj.foo` can be used
    in addition to `obj['foo']`.
    
        >>> o = Storage(a=1)
        >>> o.a
        1
        >>> o['a']
        1
        >>> o.a = 2
        >>> o['a']
        2
        >>> del o.a
        >>> o.a
        None
    
    """
    def __getattr__(self, key): 
        try: return self[key]
        except KeyError, k: return None
    def __setattr__(self, key, value): 
        self[key] = value
    def __delattr__(self, key):
        try: del self[key]
        except KeyError, k: raise AttributeError, k
    def __repr__(self):     
        return '<Storage ' + dict.__repr__(self) + '>'
    def __getstate__(self): 
        return dict(self)
    def __setstate__(self,value):
        for k,v in value.items(): self[k]=v

def load_storage(filename):
    file=open(filename,'rb')
    portalocker.lock(file, portalocker.LOCK_EX)    
    storage=cPickle.load(file)
    portalocker.unlock(file)    
    file.close()
    return Storage(storage)

def save_storage(storage,filename):    
    file=open(filename,'wb')
    portalocker.lock(file, portalocker.LOCK_EX)
    cPickle.dump(dict(storage),file)
    portalocker.unlock(file)    
    file.close()

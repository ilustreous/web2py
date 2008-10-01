import time,os,sys,logging

try:
    import google
    keys = ['APPLICATION_ID','CURRENT_VERSION_ID',
            'AUTH_DOMAIN','SERVER_SOFTWARE']
    is_gae = reduce(lambda a,k: bool(os.environ.get(k,'')) and a, keys, True)
    if is_gae:
        import cPickle,pickle
        sys.modules['cPickle'] = sys.modules['pickle']
except: pass

import wsgiref.handlers
import gluon.main

#debug = os.environ.get('SERVER_SOFTWARE','').startswith('Devel')
debug = True

def log_stats(fun):
   if debug:
       def newfun(e,r):
           t0 = time.time()
           c0 = time.clock()
           out = fun(e,r)
           c1 = time.clock()
           t1 = time.time()
           s = """**** Request: %5.0fms/%.0fms (real time/cpu time)""" % \
             ( (t1-t0) * 1000, (c1-c0) * 1000 )
           logging.info(s)
           return out
       return newfun
   else:
       return fun

@log_stats
def wsgiapp(env,res):
  return gluon.main.wsgibase(env,res)

def main():
  wsgiref.handlers.CGIHandler().run(wsgiapp)

if __name__ == '__main__':
    main() 

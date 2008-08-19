import gluon.main
import wsgiref.handlers
# import sys, os
# sys.path.insert(0,'')
# path=os.path.dirname(os.path.abspath(__file__))
# if not path in sys.path: sys.path.append(path)
# os.chdir(path)

wsgiref.handlers.CGIHandler().run(gluon.main.wsgibase)

import sys, shutil, os
sys.path.insert(0,'.')
from gluon.languages import findT

file=sys.argv[1]
apps=sys.argv[2:]
d={}
for app in apps:
    path='applications/%s/'%app
    findT(path,file)
    d.update(eval(open(os.path.join(path,'languages','%s.py' % file)).read()))
path='applications/%s/'%apps[-1]
file1=os.path.join(path,'languages','%s.py' % file)
f=open(file1,'w')
f.write('{\n')
keys=d.keys()
keys.sort()
for key in keys:
    f.write("%s:%s,\n" % (repr(key),repr(str(d[key]))))
f.write('}\n')
f.close()

oapps=apps[:-1]
oapps.reverse()
for app in oapps:
    path2='applications/%s/'%app
    file2=os.path.join(path2,'languages','%s.py' % file)
    shutil.copyfile(file1,file2)
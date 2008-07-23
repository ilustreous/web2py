SLEEP_MINUTES=5
DB_URI='sqlite://tickets.db'
ALLOW_DUPLICATES=True
import sys, os, time, stat, datetime, md5
from gluon.restricted import RestrictedError
path=os.path.join(request.folder,'errors')
hashes={}
db=SQLDB(DB_URI)
db.define_table('ticket',
    SQLField('app'),
    SQLField('name'),
    SQLField('date_saved','datetime'),
    SQLField('layer'),
    SQLField('traceback','text'),
    SQLField('code','text'))
while 1:
   for file in os.listdir(path):
      filename=os.path.join(path,file)
      if not ALLOW_DUPLICATES:
          key=md5.new(open(filename,'r').read()).hexdigest()
          if hashes.has_key(key): continue      
          hashes[key]=1
      e=RestrictedError()
      e.load(filename)
      t=datetime.datetime.fromtimestamp(os.stat(filename)[stat.ST_MTIME])
      db.ticket.insert(app=request.application,date_saved=t,name=file,layer=e.layer,traceback=e.traceback,code=e.code)
      os.unlink(filename)
   db.commit()
   time.sleep(SLEEP_MINUTES*60)
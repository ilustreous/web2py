"""
This file is part of web2py Web Framework (Copyrighted, 2007)
Developed by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: GPL v2

Thanks to Niall Sweeny<niall.sweeny@fonjax.com> for MSSQL support
Thanks to Marcel Leuthi<mluethi@mlsystems.ch> for Oracle support
"""

__all__=['SQLDB','SQLField'] 

import re, sys, os, types, cPickle, datetime, thread, cStringIO
import csv, copy, socket, logging, copy_reg, base64

table_field=re.compile('[\w_]+\.[\w_]+')

try:
    import hashlib
    def hash5(txt): return hashlib.md5(txt).hexdigest()    
except: 
    import md5
    def hash5(txt): return md5.new(txt).hexdigest()    

try: import sqlite3
except: 
    try:
        from pysqlite2 import dbapi2 as sqlite3 
        logging.warning('importing mysqlite3.dbapi2 as sqlite3')
    except: logging.warning('no sqlite3 or dbapi2 driver')
try: import MySQLdb
except: logging.warning('no MySQLdb driver')
try: import psycopg2
except: logging.warning('no psycopg2 driver')
try: import cx_Oracle
except: logging.warning('no cx_Oracle driver')
try: import pyodbc
except: logging.warning('no MSSQL driver')
try: import kinterbasdb
except: logging.warning('no kinterbasdb driver')
import portalocker
import validators

sql_locker=thread.allocate_lock()
"""
notes on concurrency....
Accessing SQLDB._folders, SQLDB._instances and SQLDB .table files
is not thread safe so they are locked with sql_locker
Moreover .table files are locked with portalocker to account for multiple
parallel processes.
"""

"""
date, time and datetime must be in ISO8601 format: yyyy-mm-dd hh:mm:ss
"""


SQL_DIALECTS={'sqlite':{'boolean':'CHAR(1)',
                      'string':'CHAR(%(length)s)',
                      'text':'TEXT',
                      'password':'CHAR(%(length)s)',
                      'blob':'BLOB',
                      'upload':'CHAR(64)',
                      'integer':'INTEGER',
                      'double':'DOUBLE',
                      'date':'DATE',
                      'time':'TIME',        
                      'datetime':'TIMESTAMP',
                      'id':'INTEGER PRIMARY KEY AUTOINCREMENT',
                      'reference':'REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
                      'lower':'LOWER(%(field)s)',
                      'upper':'UPPER(%(field)s)',
                      'is null':'IS NULL',
                      'is not null':'IS NOT NULL',
                      'extract':"web2py_extract('%(name)s',%(field)s)",
                      'left join':'LEFT JOIN',
                      'random':'Random()'},
            'mysql':{'boolean':'CHAR(1)',
                      'string':'VARCHAR(%(length)s)',
                      'text':'TEXT',
                      'password':'VARCHAR(%(length)s)',
                      'blob':'BLOB',
                      'upload':'VARCHAR(64)',
                      'integer':'INT',
                      'double':'DOUBLE',
                      'date':'DATE',
                      'time':'TIME',        
                      'datetime':'TIMESTAMP',
                      'id':'INT AUTO_INCREMENT NOT NULL',
                      'reference':'INT NOT NULL, INDEX %(field_name)s__idx (%(field_name)s), FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
                      'lower':'LOWER(%(field)s)',
                      'upper':'UPPER(%(field)s)',
                      'is null':'IS NULL',
                      'is not null':'IS NOT NULL',
                      'extract':'EXTRACT(%(name)s FROM %(field)s)',
                      'left join':'LEFT JOIN',
                      'random':'RAND()'},
            'postgres':{'boolean':'CHAR(1)',
                      'string':'VARCHAR(%(length)s)',
                      'text':'TEXT',
                      'password':'VARCHAR(%(length)s)',
                      'blob':'BYTEA',
                      'upload':'VARCHAR(64)',
                      'integer':'INTEGER',
                      'double':'FLOAT8',
                      'date':'DATE',
                      'time':'TIME',        
                      'datetime':'TIMESTAMP',
                      'id':'SERIAL PRIMARY KEY',
                      'reference':'INTEGER REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
                      'lower':'LOWER(%(field)s)',
                      'upper':'UPPER(%(field)s)',
                      'is null':'IS NULL',
                      'is not null':'IS NOT NULL',
                      'extract':'EXTRACT(%(name)s FROM %(field)s)',
                      'left join':'LEFT JOIN',
                      'random':'RANDOM()'},
            'oracle':{'boolean':'CHAR(1)',
                      'string':'VARCHAR2(%(length)s)',
                      'text':'CLOB',
                      'password':'VARCHAR2(%(length)s)',
                      'blob':'BLOB',
                      'upload':'VARCHAR2(64)',
                      'integer':'INT',
                      'double':'FLOAT',
                      'date':'DATE',
                      'time':'CHAR(8)',        
                      'datetime':'DATE',
                      'id':'NUMBER PRIMARY KEY',
                      'reference':'NUMBER, CONSTRAINT %(table_name)s_%(field_name)s__constraint FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
                      'lower':'LOWER(%(field)s)',
                      'upper':'UPPER(%(field)s)',
                      'is null':'IS NULL',
                      'is not null':'IS NOT NULL',
                      'extract':'EXTRACT(%(name)s FROM %(field)s)',
                      'left join':'LEFT OUTER JOIN',
                      'random':'dbms_random.value'},
             'mssql':{'boolean':'BIT',
                      'string':'VARCHAR(%(length)s)',
                      'text':'TEXT',
                      'password':'VARCHAR(%(length)s)',
                      'blob':'IMAGE',
                      'upload':'VARCHAR(64)',
                      'integer':'INT',
                      'double':'FLOAT',
                      'date':'DATETIME',
                      'time':'CHAR(8)',
                      'datetime':'DATETIME',
                      'id':'INT IDENTITY PRIMARY KEY',
                      'reference':'INT, CONSTRAINT %(table_name)s_%(field_name)s__constraint FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
                      'left join':'LEFT OUTER JOIN',
                      'random':'NEWID()'},
            'firebird':{'boolean':'CHAR(1)',
                      'string':'VARCHAR(%(length)s)',
                      'text':'BLOB SUB_TYPE 1',
                      'password':'VARCHAR(%(length)s)',
                      'blob':'BLOB SUB_TYPE 0',
                      'upload':'VARCHAR(64)',
                      'integer':'INTEGER',
                      'double':'FLOAT',
                      'date':'DATE',
                      'time':'TIME',        
                      'datetime':'TIMESTAMP',
                      'id':'INTEGER PRIMARY KEY',
                      'reference':'INTEGER REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
                      'lower':'LOWER(%(field)s)',
                      'upper':'UPPER(%(field)s)',
                      'is null':'IS NULL',
                      'is not null':'IS NOT NULL',
                      'extract':'EXTRACT(%(name)s FROM %(field)s)',
                      'left join':'LEFT JOIN',
                      'random':'RANDOM()'},
              }

def sqlhtml_validators(field_type,length):
    v={'boolean':[],
       'string':validators.IS_LENGTH(length),
       'text':[],
       'password':validators.IS_LENGTH(length),
       'blob':[],
       'upload':[],
       'double':validators.IS_FLOAT_IN_RANGE(-1e100,1e100),            
       'integer':validators.IS_INT_IN_RANGE(-1e100,1e100),            
       'date':validators.IS_DATE(),
       'time':validators.IS_TIME(),
       'datetime':validators.IS_DATETIME(),
       'reference':validators.IS_INT_IN_RANGE(0,1e100)}
    try: return v[field_type[:9]]
    except KeyError: return []

def sql_represent(obj,fieldtype,dbname):    
    if obj is None: return 'NULL'
    if obj=='' and fieldtype[:2] in ['id','in','re','da','ti','bo']: 
        return 'NULL'
    if fieldtype=='boolean':
        if dbname=='mssql':
            if obj and not str(obj)[0].upper()=='F': return "1"
            else: return "0"
        else:
            if obj and not str(obj)[0].upper()=='F': return "'T'"
            else: return "'F'"
    if fieldtype[0]=='i': return str(int(obj))
    elif fieldtype[0]=='r': return str(int(obj))
    elif fieldtype=='double': return str(float(obj))
    if isinstance(obj,unicode): obj=obj.encode('utf-8')
    if fieldtype=='blob':
        obj=base64.b64encode(str(obj))
    elif fieldtype=='date':
        if isinstance(obj,(datetime.date,datetime.datetime)): obj=obj.strftime('%Y-%m-%d')
        else: obj=str(obj)
        if dbname=='oracle': return "to_date('%s','yyyy-mm-dd')" % obj
    elif fieldtype=='datetime':
        if isinstance(obj,datetime.datetime): obj=obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj,datetime.date): obj=obj.strftime('%Y-%m-%d 00:00:00')
        else: obj=str(obj)
        if dbname=='oracle': return "to_date('%s','yyyy-mm-dd hh24:mi:ss')" % obj
    elif fieldtype=='time':
        if isinstance(obj,datetime.time): obj=obj.strftime('%H:%M:%S')
        else: obj=str(obj)
    else: obj=str(obj)
    return "'%s'" % obj.replace("'","''")

def cleanup(text):
    if re.compile('[^0-9a-zA-Z_]').findall(text):
        raise SyntaxError, 'only [0-9a-zA-Z_] allowed in table and field names'
    return text

def sqlite3_web2py_extract(lookup, s):
    table={'year':(0,4),'month':(5,7),'day':(8,10),
             'hour':(11,13),'minutes':(14,16),'seconds':(17,19)}
    try: 
        i,j=table[lookup]
        return int(s[i:j])
    except: return None

class SQLStorage(dict):
    """
    a dictionary that let you do d['a'] as well as d.a
    """
    def __getattr__(self, key): return self[key]
    def __setattr__(self, key, value):
        if self.has_key(key):
            raise SyntaxError, 'Object exists and cannot be redefined'
        self[key] = value
    def __repr__(self): return '<SQLStorage ' + dict.__repr__(self) + '>'

class SQLCallableList(list):
    def __call__(self): return copy.copy(self)

#class static_method:
#    """
#    now we can declare static methods in python!
#    """
#    def __init__(self, anycallable): self.__call__ = anycallable    

class SQLDB(SQLStorage):
    """
    an instance of this class represents a database connection

    Example:
    
       db=SQLDB('sqlite://test.db')
       db.define_table('tablename',SQLField('fieldname1'),
                                   SQLField('fieldname2'))

    """
    ### this allows gluon to comunite a folder for this thread
    _folders={}   
    _instances={}    
    @staticmethod
    def _set_thread_folder(folder):
        sql_locker.acquire()
        SQLDB._folders[thread.get_ident()]=folder        
        sql_locker.release()
    ### this allows gluon to commit/rollback all dbs in this thread
    @staticmethod
    def close_all_instances(action): 
        #THIS IS NOT THREAD SAFE
        """ to close cleanly databases in a multithreaded environment """
        sql_locker.acquire()
        pid=thread.get_ident()
        if SQLDB._folders.has_key(pid): 
            del SQLDB._folders[pid]
        if SQLDB._instances.has_key(pid):
            instances=SQLDB._instances[pid]
            while instances: 
                instance=instances.pop()
                action(instance)
                instance._connection.close()        
            del SQLDB._instances[pid]
        sql_locker.release()
        return
    @staticmethod
    def distributed_transaction_commit(*instances):
        if not instances: return
        instances=enumerate(instances)
        keys=[]
        thread_key='%s.%i' % (socket.gethostname(),thread.get_ident())
        for i,db in instances:
            keys.append('%s.%i'%(thread_key,i))
            if not db._dbname=='postgres':
                raise SyntaxError, "only supported by postgresql"
        try:
            for i,db in instances:
                db._execute("PREPARE TRANSACTION '%s';" % keys[i])
        except:
            for i,db in instances:
                db._execute("ROLLBACK PREPARED '%s';" % keys[i])
            raise Exception, 'failure to commit distributed transaction'
        else:
            for i,db in instances:
                db._execute("COMMIT PREPARED '%s';"  % keys[i])
        return
    def __init__(self,uri='sqlite://dummy.db'):
        self._uri=str(uri)
        self['_lastsql']=''
        self.tables=SQLCallableList()
        pid=thread.get_ident()
        ### check if there is a folder for this thread else use ''
        sql_locker.acquire()
        if self._folders.has_key(pid): self._folder=self._folders[pid]
        else: self._folder=self._folders[pid]=''
        sql_locker.release()
        ### now connect to database
        if self._uri[:9]=='sqlite://': 
            self._dbname='sqlite'
            if uri[9]!='/':
                dbpath=os.path.join(self._folder,uri[9:])
                self._connection=sqlite3.Connection(dbpath)
            else:
                self._connection=sqlite3.Connection(uri[9:])
            self._connection.create_function("web2py_extract",2,
                                             sqlite3_web2py_extract)
            self._cursor=self._connection.cursor()
            self._execute=lambda *a,**b: self._cursor.execute(*a,**b)
        elif self._uri[:8]=='mysql://':
            self._dbname='mysql'
            m=re.compile('^(?P<user>[^:@]+)(\:(?P<passwd>[^@]*))?@(?P<host>[^\:/]+)(\:(?P<port>[0-9]+))?/(?P<db>.+)$').match(self._uri[8:])
            user=m.group('user')
            if not user: raise SyntaxError, "User required"
            passwd=m.group('passwd')
            if not passwd: passwd=''
            host=m.group('host')
            if not host: raise SyntaxError, "Host name required"
            db=m.group('db')
            if not db: raise SyntaxError, "Database name required"
            port=m.group('port')
            if not port: port='3306'
            self._connection=MySQLdb.Connection(db=db,
                                                user=user,
                                                passwd=passwd,
                                                host=host,
                                                port=int(port),
                                                charset='utf8')
            self._cursor=self._connection.cursor()
            self._execute=lambda *a,**b: self._cursor.execute(*a,**b)
            self._execute('SET FOREIGN_KEY_CHECKS=0;')
        elif self._uri[:11]=='postgres://': 
            self._dbname='postgres'
            m=re.compile('^(?P<user>[^:@]+)(\:(?P<passwd>[^@]*))?@(?P<host>[^\:/]+)(\:(?P<port>[0-9]+))?/(?P<db>.+)$').match(self._uri[11:])
            user=m.group('user')
            if not user: raise SyntaxError, "User required"
            passwd=m.group('passwd')
            if not passwd: passwd=''
            host=m.group('host')
            if not host: raise SyntaxError, "Host name required"
            db=m.group('db')
            if not db: raise SyntaxError, "Database name required"
            port=m.group('port')
            if not port: port='5432'
            msg="dbname='%s' user='%s' host='%s' port=%s password='%s'" % (db,user,host,port,passwd)            
            self._connection=psycopg2.connect(msg)
            self._cursor=self._connection.cursor()
            self._execute=lambda *a,**b: self._cursor.execute(*a,**b)
            query='BEGIN;'
            self['_lastsql']=query
            self._execute(query)
            self._execute("SET CLIENT_ENCODING TO 'UNICODE';") ### not completely sure but should work
        elif self._uri[:9]=='oracle://':
            self._dbname='oracle'
            self._connection=cx_Oracle.connect(self._uri[9:])
            self._cursor=self._connection.cursor()
            self._execute=lambda a: self._cursor.execute(a[:-1])  ###
            self._execute("ALTER SESSION SET NLS_DATE_FORMAT = 'YYYY-MM-DD';")
            self._execute("ALTER SESSION SET NLS_TIMESTAMP_FORMAT = 'YYYY-MM-DD HH24:MI:SS';")
        elif self._uri[:8]=='mssql://':
            self._dbname='mssql'
            m=re.compile('^(?P<user>[^:@]+)(\:(?P<passwd>[^@]*))?@(?P<host>[^\:/]+)(\:(?P<port>[0-9]+))?/(?P<db>.+)$').match(self._uri[8:])
            user=m.group('user')
            if not user: raise SyntaxError, "User required"
            passwd=m.group('passwd')
            if not passwd: passwd=''
            host=m.group('host')
            if not host: raise SyntaxError, "Host name required"
            db=m.group('db')
            if not db: raise SyntaxError, "Database name required"
            port=m.group('port')
            if not port: port='1433'
            #Driver={SQL Server};description=web2py;server=A64X2;uid=web2py;database=web2py_test;network=DBMSLPCN
            cnxn="Driver={SQL Server};server=%s;database=%s;uid=%s;pwd=%s" % (host,db,user,passwd)
            logging.warning(cnxn)
            self._connection=pyodbc.connect(cnxn)
            self._cursor=self._connection.cursor()
            self._execute=lambda *a,**b: self._cursor.execute(*a,**b)
        elif self._uri[:11]=='firebird://': 
            self._dbname='firebird'
            m=re.compile('^(?P<user>[^:@]+)(\:(?P<passwd>[^@]*))?@(?P<host>[^\:/]+)(\:(?P<port>[0-9]+))?/(?P<db>.+)$').match(self._uri[11:])
            user=m.group('user')
            if not user: raise SyntaxError, "User required"
            passwd=m.group('passwd')
            if not passwd: passwd=''
            host=m.group('host')
            if not host: raise SyntaxError, "Host name required"
            db=m.group('db')
            if not db: raise SyntaxError, "Database name required"
            port=m.group('port')
            if not port: port='3050'
            self._connection=kinterbasdb.connect(dsn="%s:%s"%(host,db), user=user, password=passwd)
            self._cursor=self._connection.cursor()
            self._execute=lambda *a,**b: self._cursor.execute(*a,**b)
        elif self._uri=='None':
            class Dummy:
                lastrowid=1
                def __getattr__(self,value): return lambda *a,**b: ''
            self._dbname='sqlite'
            self._connection=Dummy()
            self._cursor=Dummy()
            self._execute=lambda a: []
        else:
            raise SyntaxError, 'database type not supported'
        self._translator=SQL_DIALECTS[self._dbname]
        ### register this instance of SQLDB
        sql_locker.acquire()
        if self._instances.has_key(pid): self._instances[pid].append(self)
        else: self._instances[pid]=[self]
        sql_locker.release()
        pass
    def define_table(self,tablename,*fields,**args):
        if not args.has_key('migrate'): args['migrate']=True
        if args.keys()!=['migrate']:
            raise SyntaxError, 'invalid table attribute'
        tablename=cleanup(tablename)
        if tablename in dir(self) or tablename[0]=='_':
            raise SyntaxError, 'invalid table name'
        if not tablename in self.tables: self.tables.append(tablename)
        else: raise SyntaxError, "table already defined"
        t=self[tablename]=SQLTable(self,tablename,*fields)
        if self._uri=='None':
            args['migrate']=False
            return t
        sql_locker.acquire()
        try:            
            query = t._create(migrate=args['migrate'])
        except BaseException, e:
            sql_locker.release()
            raise e
        sql_locker.release()
        return t
    def __call__(self,where=''):
        return SQLSet(self,where)
    def commit(self):
        self._connection.commit()
    def rollback(self):
        self._connection.rollback()
    def executesql(self,query):
        self['_lastsql']=query
        self._execute(query)
        return self._cursor.fetchall()
    def __getstate__(self): return dict()

def unpickle_SQLDB(state):
    logging.warning('unpickling SQLDB objects is experimental')
    db=SQLDB(state['uri'])
    for k,d in state['tables']:
        db.define_table(k,*[SQLField(**i) for i in d],**dict(migrate=False))
    return db

def pickle_SQLDB(db):
    logging.warning('pickling SQLDB objects is experimental')
    tables=[]
    for k in db.values():
        if not isinstance(k,SQLTable): continue
        fields=[]
        for f in k.values():
            if not isinstance(f,SQLField) or f.name=='id': continue
            fields.append(dict(fieldname=f.name,type=f.type,
                 length=f.length,default=f.default,required=f.required,
                 requires=f.requires,ondelete=f.ondelete,
                 notnull=f.notnull,unique=f.notnull),uploadfield=f.uploadfield)
        tables.append((k._tablename,fields))
    return unpickle_SQLDB, (dict(uri=db._uri,tables=tables),)

copy_reg.pickle(SQLDB, pickle_SQLDB)

class SQLALL(object):
    def __init__(self,table): 
        self.table=table
    def __str__(self): 
        s=['%s.%s'%(self.table._tablename,name) for name in self.table.fields]
        return ', '.join(s)

class SQLJoin(object):
    def __init__(self,table,query):
        self.table=table
        self.query=query
    def __str__(self):
        return '%s ON %s' % (self.table,self.query)

class SQLTable(SQLStorage):
    """
    an instance of this class represents a database table
    Example:
    
    db=SQLDB(...)
    db.define_table('users',SQLField('name'))
    db.users.insert(name='me') # print db.users._insert(...) to see SQL
    db.users.drop()
    """
    def __init__(self,db,tablename,*fields):
        self._db=db
        self._tablename=tablename
        self.fields=SQLCallableList()
        self._referenced_by=[]
        fields=list(fields)
        fields.insert(0,SQLField('id','id'))
        for field in fields:
            self.fields.append(field.name)
            self[field.name]=field
            field._tablename=self._tablename
            field._table=self
            field._db=self._db
        self.ALL=SQLALL(self)
    def __str__(self):
        return self._tablename
    def _create(self,migrate=True):
        fields=[]
        sql_fields={}
        for k in self.fields:
            field=self[k]
            if field.type[:9]=='reference':
                referenced=field.type[10:].strip()
                if not referenced:
                    raise SyntaxError, 'SQLTable: reference to nothing!'
                if not self._db.has_key(referenced):
                    raise SyntaxError, 'SQLTable: table does not exist'
                referee=self._db[referenced]
                ftype=self._db._translator[field.type[:9]] % dict(table_name=self._tablename,field_name=field.name,foreign_key=referenced+'(id)',on_delete_action=field.ondelete)
                if self._tablename in referee.fields:  ### THIS IS OK
                    raise SyntaxError, 'SQLField: table name has same name as a field in referenced table'
                self._db[referenced]._referenced_by.append((self._tablename,field.name))
            elif not self._db._translator.has_key(field.type):
                raise SyntaxError, 'SQLField: unkown field type'
            else:                                                      
                ftype=self._db._translator[field.type] % dict(length=field.length)            
            if not field.type[:9] in ['id','reference']:
                if field.notnull: ftype+=' NOT NULL'
                if field.unique: ftype+=' UNIQUE'
            sql_fields[field.name]=ftype
            fields.append('%s %s' % (field.name,ftype))
        other=';'
        if self._db._dbname=='mysql':
            fields.append('PRIMARY KEY(id)')
            other=' ENGINE=InnoDB CHARACTER SET utf8;'
        fields=',\n\t'.join(fields)
        query='CREATE TABLE %s(\n\t%s\n)%s' % (self._tablename,fields,other)
        if not migrate: 
            return query
        elif isinstance(migrate,str):
            self._dbt=os.path.join(self._db._folder,migrate)
        else: 
            self._dbt=os.path.join(self._db._folder,\
              '%s_%s.table' % (hash5(self._db._uri),self._tablename))        
        logfilename=os.path.join(self._db._folder,'sql.log')
        logfile=open(logfilename,'a')      
        if not os.path.exists(self._dbt):
            logfile.write('timestamp: %s\n' % \
                          datetime.datetime.today().isoformat())
            logfile.write(query+'\n')
            self._db['_lastsql']=query
            self._db._execute(query)
            if self._db._dbname=='oracle':
                t=self._tablename
                self._db._execute('CREATE SEQUENCE %s_sequence START WITH 1 INCREMENT BY 1 NOMAXVALUE;' % t)
                self._db._execute('CREATE OR REPLACE TRIGGER %s_trigger BEFORE INSERT ON %s FOR EACH ROW BEGIN SELECT %s_sequence.nextval INTO :NEW.id FROM DUAL; END;\n' % (t,t,t))
            elif self._db._dbname=='firebird':
                t=self._tablename
                self._db._execute('create generator GENID_%s;' % t)
                self._db._execute('set generator GENID_%s to 0;' % t)
                self._db._execute('create trigger trg_id_%s for %s active before insert position 0 as\nbegin\nif(new.id is null) then\nbegin\nnew.id = gen_id(GENID_%s, 1);\nend\nend;\n' % (t,t,t))  
            self._db.commit()
            file=open(self._dbt,'w')
            portalocker.lock(file, portalocker.LOCK_EX)
            cPickle.dump(sql_fields,file)
            file.close()
            logfile.write('success!\n')
        else:
            file=open(self._dbt,'r')
            portalocker.lock(file, portalocker.LOCK_SH)
            sql_fields_old=cPickle.load(file)
            file.close()
            if sql_fields!=sql_fields_old:
                self._migrate(sql_fields,sql_fields_old,logfile)        
        return query
    def _migrate(self,sql_fields,sql_fields_old,logfile):
        keys=sql_fields.keys()
        for key in sql_fields_old.keys():
            if not key in keys: keys.append(key)
        for key in keys:
            if not sql_fields_old.has_key(key):
                if self._db._dbname=='firebird':
                    query='ALTER TABLE %s ADD %s %s;' % \
                          (self._tablename, key, \
                           sql_fields[key].replace(', ',', ADD '))              
                else:
                    query='ALTER TABLE %s ADD COLUMN %s %s;' % \
                          (self._tablename, key, \
                          sql_fields[key].replace(', ',', ADD '))              
            elif self._db._dbname=='sqlite': query=None
            elif not sql_fields.has_key(key):
                query='ALTER TABLE %s DROP COLUMN %s;' % \
                      (self._tablename, key)
            elif sql_fields[key]!=sql_fields_old[key]:
                # 2
                t=self._tablename
                tt=sql_fields[key].replace(', ',', ADD ')
                query='ALTER TABLE %s ADD %s__tmp %s;\n' % (t,key,tt) +\
                      'UPDATE %s SET %s__tmp=%s;\n' % (t,key,key) +\
                      'ALTER TABLE %s DROP COLUMN %s;\n' % (t,key) +\
                      'ALTER TABLE %s ADD %s %s;\n' % (t,key,tt) +\
                      'UPDATE %s SET %s=%s__tmp;\n' % (t,key,key) +\
                      'ALTER TABLE %s DROP COLUMN %s__tmp;'%(t,key)
                # 1 and 2 may have a problem with references in MySQL and Oracle, not sure
            else: query=None
            if query:
                logfile.write('timestamp: %s\n' % \
                              datetime.datetime.today().isoformat())
                logfile.write(query+'\n')
                self._db['_lastsql']=query
                self._db._execute(query)               
                if sql_fields.has_key(key): sql_fields_old[key]=sql_fields[key]
                else: del sql_fields_old[key]
                logfile.write('success!\n')
        file=open(self._dbt,'w')
        portalocker.lock(file, portalocker.LOCK_EX)
        cPickle.dump(sql_fields_old,file)
        file.close()
    def create(self):
        # nothing to do, here for backward compatility
        pass
    def _drop(self):
        t=self._tablename
        if self._db._dbname=='oracle':
            return ['DROP TABLE %s;' % t,'DROP SEQUENCE %s_sequence;' % t]
        elif self._db._dbname=='firebird':
            return ['DROP TABLE %s;' % t,'DROP GENERATOR GENID_%s;' % t]
        return ['DROP TABLE %s;' % t]
    def drop(self):        
        logfile=open(os.path.join(self._db._folder,'sql.log'),'a')
        queries=self._drop()
        self._db['_lastsql']='\n'.join(queries)
        for query in queries: 
            logfile.write(query+'\n')
            self._db._execute(query)
        del self._db[self._tablename]
        del self._db.tables[self._db.tables.index(self._tablename)]
        self._db.commit()
        os.unlink(self._dbt)
        logfile.write('success!\n')
    def _insert(self,**fields):
        fs,vs=[],[]
        if [key for key in fields.keys() if not key in self.fields]:
            raise SyntaxError, 'invalid field name'
        for fieldname in self.fields:
            if fieldname=='id': continue
            field=self[fieldname]     
            ft,fd=field.type,field._db._dbname
            if fields.has_key(fieldname):                
                fs.append(fieldname)
                value=fields[fieldname]
                try: vs.append(sql_represent(value.id,ft,fd))
                except: vs.append(sql_represent(value,ft,fd))
            elif field.default!=None:
                fs.append(fieldname)
                vs.append(sql_represent(field.default,ft,fd))
            elif field.required is True:
                raise SyntaxError, 'SQLTable: missing required field'
        sql_f=', '.join(fs)
        sql_v=', '.join(vs)
        sql_t=self._tablename
        return 'INSERT INTO %s(%s) VALUES (%s);' % (sql_t,sql_f,sql_v)
    def insert(self,**fields):
        query=self._insert(**fields)
        self._db['_lastsql']=query
        self._db._execute(query)
        if self._db._dbname=='sqlite':
            id=self._db._cursor.lastrowid 
        elif self._db._dbname=='postgres':
            self._db._execute("select currval('%s_id_Seq')" % self._tablename)
            id=int(self._db._cursor.fetchone()[0])
        elif self._db._dbname=='mysql':
            self._db._execute("select last_insert_id();")
            id=int(self._db._cursor.fetchone()[0])
        elif self._db._dbname=='oracle':
            t=self._tablename
            self._db._execute('SELECT %s_sequence.currval FROM dual;' %t)
            id=int(self._db._cursor.fetchone()[0])
        elif self._db._dbname=='mssql':
            self._db._execute('SELECT @@IDENTITY;')
            id=int(self._db._cursor.fetchone()[0])
        elif self._db._dbname=='firebird':
            self._db._execute("SELECT gen_id(GENID_%s, 0) FROM rdb$database" % self._tablename)
            id=int(self._db._cursor.fetchone()[0])       
        else:
            id=None
        return id
    def import_from_csv_file(self,file):
        """
        import records from csv file. Column headers must have same names as
        table fields. field 'id' is ignored. If column names read 'table.file'
        the 'table.' prefix is ignored.
        """
        reader = csv.reader(file)
        colnames=None
        for line in reader:
            if not colnames:
                colnames=[x[x.find('.')+1:] for x in line]
                c=[i for i in xrange(len(line)) if colnames[i]!='id']
            else:
                items=[(colnames[i],line[i]) for i in c]
                self.insert(**dict(items))
    def on(self,query):
        return SQLJoin(self,query)
    def _truncate(self):
        t = self._tablename
        if self._db._dbname=='sqlite':
            return ['DELETE FROM %s;' % t, 
                    "DELETE FROM sqlite_sequence WHERE name='%s';" % t]
        return ['TRUNCATE TABLE %s;' % t]
    def truncate(self):
        logfile=open(os.path.join(self._db._folder,'sql.log'),'a')
        queries=self._truncate()
        self._db['_lastsql']='\n'.join(queries)
        for query in queries:
            logfile.write(query+'\n')
            self._db._execute(query)
        self._db.commit()
        logfile.write('success!\n')
    def __str__(self):
        return self._tablename
 
class SQLXorable(object):
    def __init__(self,name,type='string',db=None):
        self.name,self.type,self._db=name,type,db
    def __str__(self): 
        return self.name
    def __or__(self,other): # for use in sortby
        return SQLXorable(str(self)+', '+str(other),None,None)
    def __invert__(self):
        return SQLXorable(str(self)+' DESC',None,None)
    # for use in SQLQuery
    def __eq__(self,value): return SQLQuery(self,'=',value)
    def __ne__(self,value): return SQLQuery(self,'<>',value)
    def __lt__(self,value): return SQLQuery(self,'<',value)
    def __le__(self,value): return SQLQuery(self,'<=',value)
    def __gt__(self,value): return SQLQuery(self,'>',value)
    def __ge__(self,value): return SQLQuery(self,'>=',value)
    def like(self,value): return SQLQuery(self,' LIKE ',value)
    def belongs(self,value): return SQLQuery(self,' IN ',value)
    # for use in both SQLQuery and sortby
    def __add__(self,other): 
        return SQLXorable('%s+%s'%(self,other),'float',None)
    def __sub__(self,other):
        return SQLXorable('%s-%s'%(self,other),'float',None)
    def __mul__(self,other):
        return SQLXorable('%s*%s'%(self,other),'float',None)
    def __div__(self,other):
        return SQLXorable('%s/%s'%(self,other),'float',None)

class SQLField(SQLXorable):
    """
    an instance of this class represents a database field

    example:

    a=SQLField(name,'string',length=32,required=False,default=None,requires=IS_NOT_EMPTY(),notnull=False,unique=False,uploadfield=None)
    
    to be used as argument of SQLDB.define_table

    allowed field types:
    string, boolean, integer, double, text, blob, 
    date, time, datetime, upload, password

    strings must have a length or 32 by default.
    fields should have a default or they will be required in SQLFORMs
    the requires argument are used to validate the field input in SQLFORMs

    """
    def __init__(self,fieldname,type='string',
                 length=32,default=None,required=False,
                 requires=sqlhtml_validators,ondelete='CASCADE',
                 notnull=False,unique=False,uploadfield=True):
        self.name=cleanup(fieldname)
        if fieldname in dir(SQLTable) or fieldname[0]=='_':
            raise SyntaxError, 'SQLField: invalid field name'
        if isinstance(type,SQLTable): type='reference '+type._tablename
        if not length and type=='string': type='text'
        elif not length and type=='password': length=32
        self.type=type  # 'string', 'integer'
        if type=='upload': length=64       
        self.length=length                 # the length of the string
        self.default=default               # default value for field
        self.required=required             # is this field required
        self.ondelete=ondelete.upper()     # this is for reference fields only
        self.notnull=notnull
        self.unique=unique
        self.uploadfield=uploadfield
        if requires==sqlhtml_validators: requires=sqlhtml_validators(type,length)
        elif requires is None: requires=[]
        self.requires=requires             # list of validators
    def formatter(self,value):
        if value is None or not self.requires: return value
        if not isinstance(self.requires,(list,tuple)): requires=[self.requires]
        elif isinstance(self.requires,tuple): requires=list(self.requires)
        else: requires=copy.copy(self.requires)
        requires.reverse()
        for item in requires:
            if hasattr(item,'formatter'): value=item.formatter(value)
        return value
    def lower(self):
        s=self._db._translator["lower"] % dict(field=str(self))
        return SQLXorable(s,'string',self._db)
    def upper(self):
        s=self._db._translator["upper"] % dict(field=str(self))
        return SQLXorable(s,'string',self._db)
    def year(self): 
        s=self._db._translator["extract"] % dict(name='year',field=str(self))
        return SQLXorable(s,'integer',self._db)
    def month(self):
        s=self._db._translator["extract"] % dict(name='month',field=str(self))
        return SQLXorable(s,'integer',self._db)
    def day(self):
        s=self._db._translator["extract"] % dict(name='day',field=str(self))
        return SQLXorable(s,'integer',self._db)
    def hour(self):
        s=self._db._translator["extract"] % dict(name='hour',field=str(self))
        return SQLXorable(s,'integer',self._db)
    def minutes(self):
        s=self._db._translator["extract"] % dict(name='minutes',field=str(self))
        return SQLXorable(s,'integer',self._db)
    def seconds(self):
        s=self._db._translator["extract"] % dict(name='seconds',field=str(self))
        return SQLXorable(s,'integer',self._db)
    def count(self):
        return 'count(%s)' % str(self)
    def sum(self):
        return 'sum(%s)' % str(self)
    def __str__(self): return '%s.%s' % (self._tablename,self.name)

class SQLQuery(object):
    """
    a query object necessary to define a set.
    t can be stored or can be passed to SQLDB.__call__() to obtain a SQLSet

    Example:
    query=db.users.name=='Max'
    set=db(query)
    records=set.select()
    """
    def __init__(self,left,op=None,right=None):        
        if op is None and right is None: self.sql=left
        elif right is None:
            if op=='=': 
                self.sql='%s %s' % (left,left._db._translator['is null'])
            elif op=='<>':
                self.sql='%s %s' % (left,left._db._translator['is not null'])
            else: raise SyntaxError, 'do not know what to do'
        elif op==' IN ':
            if isinstance(right,str):
                self.sql='%s%s(%s)'%(left,op,right[:-1])
            elif hasattr(right,'__iter__'):
                r=','.join([sql_represent(i,left.type,left._db) for i in right])
                self.sql='%s%s(%s)'%(left,op,r)
            else: raise SyntaxError, 'do not know what to do'
        elif isinstance(right,(SQLField,SQLXorable)):
            self.sql='%s%s%s' % (left,op,right)
        else:
            right=sql_represent(right,left.type,left._db._dbname)
            self.sql='%s%s%s' % (left,op,right)
    def __and__(self,other): return SQLQuery('(%s AND %s)'%(self,other))
    def __or__(self,other): return SQLQuery('(%s OR %s)'%(self,other))
    def __invert__(self): return SQLQuery('(NOT %s)'%self)
    def __str__(self): return self.sql

regex_tables=re.compile('(?P<table>[a-zA-Z]\w*)\.')
regex_quotes=re.compile("'[^']*'")

def parse_tablenames(text):
    text=regex_quotes.sub('',text)
    while 1:
        i=text.find('IN (SELECT ')
        if i==-1: break
        k,j,n=1,i+11,len(text)
        while k and j<n:
            c=text[j]
            if c=='(': k+=1
            elif c==')': k-=1
            j+=1
        text=text[:i]+text[j+1:]
    items=regex_tables.findall(text)
    tables={}
    for item in items: tables[item]=True
    return tables.keys()        

class SQLSet(object):
    """
    sn SQLSet represents a set of records in the database,
    the records are identified by the where=SQLQuery(...) object.
    normally the SQLSet is generated by SQLDB.__call__(SQLQuery(...))

    given a set, for example
       set=db(db.users.name=='Max')
    you can:
       set.update(db.users.name='Massimo')
       set.delete() # all elements in the set
       set.select(orderby=db.users.id,groupby=db.users.name,limitby=(0,10))
    and take subsets:
       subset=set(db.users.id<5)
    """
    def __init__(self,db,where=''):
        self._db=db
        self._tables=[]
        # find out wchich tables are involved
        self.sql_w=str(where)
        #print self.sql_w
        self._tables=parse_tablenames(self.sql_w)
        #print self._tables
    def __call__(self,where):
        if self.sql_w: return SQLSet(self._db,SQLQuery(self.sql_w)&where)
        else: return SQLSet(self._db,where)
    def _select(self,*fields,**attributes):
        valid_attributes=['orderby','groupby','limitby','required',
                          'default','requires','left']
        if [key for key in attributes.keys() if not key in valid_attributes]:
            raise SyntaxError, 'invalid select attribute'
        ### if not fields specified take them all from the requested tables
        if not fields: fields=[self._db[table].ALL for table in self._tables]
        sql_f=', '.join([str(f) for f in fields])
        tablenames=parse_tablenames(self.sql_w+' '+sql_f)
        if len(tablenames)<1: raise SyntaxError, 'SQLSet: no tables selected'
        self.colnames=[c.strip() for c in sql_f.split(', ')]
        if self.sql_w: sql_w=' WHERE '+self.sql_w
        else: sql_w=''
        sql_o=''
        if attributes.has_key('left') and attributes['left']: 
            join=attributes['left']
            command=self._db._translator['left join']           
            if not isinstance(join,(tuple,list)): join=[join]
            joint=[str(t) for t in join if not isinstance(t,SQLJoin)]
            joinon=[t for t in join if isinstance(t,SQLJoin)]
            joinont=[str(t.table) for t in joinon]
            excluded=[t for t in tablenames if not t in joint+joinont]
            sql_t=', '.join(excluded)
            if joint:
                sql_t+=' %s %s' %(command,', '.join(joint))            
            for t in joinon:
                sql_t+=' %s %s' %(command,str(t))
        else:
            sql_t=', '.join(tablenames)
        if attributes.has_key('groupby') and attributes['groupby']: 
            sql_o+=' GROUP BY %s'% attributes['groupby']
        if attributes.has_key('orderby') and attributes['orderby']: 
            if str(attributes.get('orderby',''))=='<random>':
                sql_o+=' ORDER BY %s' % self._db._translator['random']
            else:
                sql_o+=' ORDER BY %s' % attributes['orderby']
        if attributes.has_key('limitby') and attributes['limitby']: 
            ### oracle does not support limitby
            lmin,lmax=attributes['limitby']
            if self._db._dbname=='oracle':
                if not attributes.has_key('orderby') or not attributes['orderby']:
                    sql_o+=' ORDER BY %s'%', '.join([t+'.id' for t in tablenames])
                return "SELECT %s FROM (SELECT _tmp.*, ROWNUM _row FROM (SELECT %s FROM %s%s%s) _tmp WHERE ROWNUM<%i ) WHERE _row>=%i;" %(sql_f,sql_f,sql_t,sql_w,sql_o,lmax,lmin)
            elif self._db._dbname=='mssql':
                if lmin>0: raise SyntaxError, "Not Supported"
                if not attributes.has_key('orderby') or not attributes['orderby']:
                    sql_o+=' ORDER BY %s'%', '.join([t+'.id' for t in tablenames])
                return "SELECT TOP %i %s FROM %s%s%s;" %(lmax+lmin,sql_f,sql_t,sql_w,sql_o)
            elif self._db._dbname=='firebird':
                if not attributes.has_key('orderby') or not attributes['orderby']:
                    sql_o+=' ORDER BY %s'%', '.join([t+'.id' for t in tablenames])
                return "SELECT FIRST %i SKIP %i %s FROM %s %s %s;"%(lmax-lmin,lmin,sql_f,sql_t,sql_w,sql_o)
            sql_o+=' LIMIT %i OFFSET %i' % (lmax-lmin,lmin)
        return 'SELECT %s FROM %s%s%s;'%(sql_f,sql_t,sql_w,sql_o) 
    def select(self,*fields,**attributes):
        """
        Always returns a SQLRows object, even if it may be empty
        """
        def response(query):
            self._db['_lastsql']=query
            self._db._execute(query)
            return self._db._cursor.fetchall()
        if not attributes.has_key('cache'):
            query=self._select(*fields,**attributes)
            r=response(query)
        else:
            cache_model,time_expire=attributes['cache']
            del attributes['cache']
            query=self._select(*fields,**attributes)       
            key=self._db._uri+'/'+query
            r=cache_model(key,lambda:response(query),time_expire)
        return SQLRows(self._db,r,*self.colnames)      
    def _count(self):
        return self._select('count(*)')
    def count(self):
        return self.select('count(*)').response[0][0]
    def _delete(self):
        if len(self._tables)!=1:
            raise SyntaxError, 'SQLSet: unable to determine what to delete'
        tablename=self._tables[0]
        if self.sql_w: sql_w=' WHERE '+self.sql_w
        else: sql_w=''
        return 'DELETE FROM %s%s;' % (tablename,sql_w)
    def delete(self):
        query=self._delete()
        self._db['_lastsql']=query
        self._db._execute(query)
    def _update(self,**fields):
        tablenames=self._tables
        if len(tablenames)!=1: 
            raise SyntaxError, 'SQLSet: unable to determine what to do'
        tt,fd=self._db[tablenames[0]],self._db._dbname
        sql_v='SET '+', '.join(['%s=%s' % (field,sql_represent(value,tt[field].type,fd)) for field,value in fields.items()])
        sql_t=tablenames[0]
        if self.sql_w: sql_w=' WHERE '+self.sql_w
        else: sql_w=''
        return 'UPDATE %s %s%s;' % (sql_t,sql_v,sql_w)
    def update(self,**fields):
        query=self._update(**fields)
        self._db['_lastsql']=query
        self._db._execute(query)

def update_record(t,s,a):
    s.update(**a)
    for key,value in a.items(): t[str(key)]=value

class SQLRows(object):
    ### this class still needs some work to care for ID/OID
    """
    A wrapper for the retun value of a select. It basically represents a table.
    It has an iterator and each row is represented as a dictionary.
    """
    def __init__(self,db,response,*colnames):
        self._db=db
        self.colnames=colnames
        self.response=response
    def __len__(self):
        return len(self.response)
    def __getitem__(self,i):        
        if i>=len(self.response) or i<0:
            raise SyntaxError, 'SQLRows: no such row'
        if len(self.response[0])!=len(self.colnames):
            raise SyntaxError, 'SQLRows: internal error'
        row=SQLStorage()       
        for j in xrange(len(self.colnames)):            
            value=self.response[i][j]
            if isinstance(value,unicode): value=value.encode('utf-8')
            if not table_field.match(self.colnames[j]):
                 if not row.has_key('_extra'): row['_extra']=SQLStorage()
                 row['_extra'][self.colnames[j]]=value
                 continue            
            tablename,fieldname=self.colnames[j].split('.')
            table=self._db[tablename]
            field=table[fieldname]
            if not row.has_key(tablename):
                row[tablename]=SQLStorage()
            if field.type[:9]=='reference':
                referee=field.type[10:].strip()
                rid=value
                row[tablename][fieldname]=rid
                #row[tablename][fieldname]=SQLSet(self._db[referee].id==rid)
            elif field.type=='blob' and value!=None:
                row[tablename][fieldname]=base64.b64decode(value)
            elif field.type=='boolean' and value!=None:
                if value==True or value=='T' or value=='t':
                    row[tablename][fieldname]=True
                else: row[tablename][fieldname]=False
            elif field.type=='date' and value!=None and not isinstance(value,datetime.date):
                y,m,d=[int(x) for x in str(value).strip().split('-')]
                row[tablename][fieldname]=datetime.date(y,m,d)
            elif field.type=='time' and value!=None and not isinstance(value,datetime.time):
                time_items=[int(x) for x in str(value).strip().split(':')[:3]]
                if len(time_items)==3: h,mi,s=time_items
                else: h,mi,s=time_items+[0]
                row[tablename][fieldname]=datetime.time(h,mi,s)
            elif field.type=='datetime' and value!=None and not isinstance(value,datetime.datetime):
                y,m,d=[int(x) for x in str(value)[:10].strip().split('-')]
                time_items=[int(x) for x in str(value)[11:].strip().split(':')[:3]]
                if len(time_items)==3: h,mi,s=time_items
                else: h,mi,s=time_items+[0]
                row[tablename][fieldname]=datetime.datetime(y,m,d,h,mi,s)
            else:
                row[tablename][fieldname]=value
            if fieldname=='id':
                id=row[tablename].id
                row[tablename].update_record=lambda t=row[tablename], \
                    s=self._db(table.id==id),**a: update_record(t,s,a)
                for referee_table,referee_name in table._referenced_by:
                    s=self._db[referee_table][referee_name]
                    row[tablename][referee_table]=SQLSet(self._db,s==id)
        keys=row.keys()
        if len(keys)==1 and keys[0]!='_extra': return row[row.keys()[0]]
        return row
    def __iter__(self):
        """
        iterator over records
        """
        for i in xrange(len(self)):
            yield self[i]
    def __str__(self):
        """
        serializes the table into a csv file
        """
        s=cStringIO.StringIO()
        writer = csv.writer(s)
        writer.writerow(self.colnames)
        c=len(self.colnames)
        for i in xrange(len(self)):
            row=[self.response[i][j] for j in xrange(c)]
            for k in xrange(c):
                if isinstance(row[k],unicode): row[k]=row[k].encode('utf-8')
            writer.writerow(row)
        return s.getvalue()
    def xml(self):
        """
        serializes the table using sqlhtml.SQLTABLE (if present)
        """
        import sqlhtml
        return sqlhtml.SQLTABLE(self).xml() 
        
def test_all():
    """    

    Create a table with all possible field types
    'sqlite://test.db'
    'mysql://root:none@localhost/test'
    'postgres://mdipierro:none@localhost/test'
    'mssql://web2py:none@A64X2/web2py_test'
    'firebase://user:password@server:3050/database'

    >>> if len(sys.argv)<2: db=SQLDB("sqlite://test.db")
    >>> if len(sys.argv)>1: db=SQLDB(sys.argv[1])
    >>> tmp=db.define_table('users',\
              SQLField('stringf','string',length=32,required=True),\
              SQLField('booleanf','boolean',default=False),\
              SQLField('passwordf','password',notnull=True),\
              SQLField('blobf','blob'),\
              SQLField('uploadf','upload'),\
              SQLField('integerf','integer',unique=True),\
              SQLField('doublef','double',unique=True,notnull=True),\
              SQLField('datef','date',default=datetime.date.today()),\
              SQLField('timef','time'),\
              SQLField('datetimef','datetime'),\
              migrate='test_user.table')

   Insert a field

    >>> db.users.insert(stringf='a',booleanf=True,passwordf='p',blobf='0A',\
                       uploadf=None, integerf=5,doublef=3.14,\
                       datef=datetime.date(2001,1,1),\
                       timef=datetime.time(12,30,15),\
                       datetimef=datetime.datetime(2002,2,2,12,30,15))
    1

    Drop the table   

    >>> db.users.drop()

    Examples of insert, select, update, delete

    >>> tmp=db.define_table('person',\
              SQLField('name'), \
              SQLField('birth','date'),\
              migrate='test_person.table')
    >>> person_id=db.person.insert(name="Marco",birth='2005-06-22')
    >>> person_id=db.person.insert(name="Massimo",birth='1971-12-21')
    >>> len(db().select(db.person.ALL))
    2
    >>> me=db(db.person.id==person_id).select()[0] # test select
    >>> me.name
    'Massimo'
    >>> db(db.person.name=='Massimo').update(name='massimo') # test update
    >>> db(db.person.name=='Marco').delete() # test delete

    Update a single record

    >>> me.update_record(name="Max")
    >>> me.name
    'Max'

    Examples of complex search conditions

    >>> len(db((db.person.name=='Max')&(db.person.birth<'2003-01-01')).select())
    1
    >>> len(db((db.person.name=='Max')&(db.person.birth<datetime.date(2003,01,01))).select())
    1
    >>> len(db((db.person.name=='Max')|(db.person.birth<'2003-01-01')).select())
    1
    >>> me=db(db.person.id==person_id).select(db.person.name)[0] 
    >>> me.name
    'Max'
  
    Examples of search conditions using extract from date/datetime/time      

    >>> len(db(db.person.birth.month()==12).select())
    1
    >>> len(db(db.person.birth.year()>1900).select())
    1

    Example of usage of NULL

    >>> len(db(db.person.birth==None).select()) ### test NULL
    0
    >>> len(db(db.person.birth!=None).select()) ### test NULL
    1

    Examples of search consitions using lower, upper, and like

    >>> len(db(db.person.name.upper()=='MAX').select())
    1
    >>> len(db(db.person.name.like('%ax')).select())
    1
    >>> len(db(db.person.name.upper().like('%AX')).select())
    1
    >>> len(db(~db.person.name.upper().like('%AX')).select())
    0

    orderby, groupby and limitby 

    >>> people=db().select(db.person.name,orderby=db.person.name)
    >>> order=db.person.name|~db.person.birth
    >>> people=db().select(db.person.name,orderby=order)
    
    >>> people=db().select(db.person.name,orderby=db.person.name,groupby=db.person.name)
    
    >>> people=db().select(db.person.name,orderby=order,limitby=(0,100))

    Example of one 2 many relation

    >>> tmp=db.define_table('dog', \
              SQLField('name'), \
              SQLField('birth','date'), \
              SQLField('owner',db.person),\
              migrate='test_dog.table')
    >>> db.dog.insert(name='Snoopy',birth=None,owner=person_id)
    1

    A simple JOIN

    >>> len(db(db.dog.owner==db.person.id).select())
    1

    >>> len(db().select(db.person.ALL,db.dog.name,left=db.dog.on(db.dog.owner==db.person.id)))
    1

    Drop tables

    >>> db.dog.drop()
    >>> db.person.drop()

    Example of many 2 many relation and SQLSet
 
    >>> tmp=db.define_table('author',SQLField('name'),\
                            migrate='test_author.table')
    >>> tmp=db.define_table('paper',SQLField('title'),\
                            migrate='test_paper.table')
    >>> tmp=db.define_table('authorship',\
            SQLField('author_id',db.author),\
            SQLField('paper_id',db.paper),\
            migrate='test_authorship.table')
    >>> aid=db.author.insert(name='Massimo')
    >>> pid=db.paper.insert(title='QCD')
    >>> tmp=db.authorship.insert(author_id=aid,paper_id=pid)

    Define a SQLSet

    >>> authored_papers=db((db.author.id==db.authorship.author_id)&\
                           (db.paper.id==db.authorship.paper_id))
    >>> rows=authored_papers.select(db.author.name,db.paper.title)
    >>> for row in rows: print row.author.name, row.paper.title
    Massimo QCD

    Example of search condition using  belongs

    >>> set=(1,2,3)
    >>> rows=db(db.paper.id.belongs(set)).select(db.paper.ALL)
    >>> print rows[0].title
    QCD

    Example of search condition using nested select

    >>> nested_select=db()._select(db.authorship.paper_id)
    >>> rows=db(db.paper.id.belongs(nested_select)).select(db.paper.ALL)
    >>> print rows[0].title
    QCD

    Output in csv

    >>> str(authored_papers.select(db.author.name,db.paper.title))
    'author.name,paper.title\\r\\nMassimo,QCD\\r\\n'

    Delete all leftover tables

    # >>> SQLDB.distributed_transaction_commit(db)

    >>> db.authorship.drop()
    >>> db.author.drop()
    >>> db.paper.drop()
    """

if __name__=='__main__':
    import doctest
    doctest.testmod()



"""
This file is part of web2py Web Framework (Copyrighted, 2007)
Developed by Massimo Di Pierro <mdipierro@cs.depaul.edu> and Robin B <robi123@gmail.com>
License: GPL v2
"""

__all__=['GQLDB','SQLField'] 

import re, sys, os, types, cPickle, datetime, thread, cStringIO, csv, copy, socket, logging
import gluon.validators as validators
import gluon.sqlhtml as sqlhtml
from new import classobj
from google.appengine.ext import db as google_db

table_field=re.compile('[\w_]+\.[\w_]+')

SQL_DIALECTS={'google':{'boolean':google_db.BooleanProperty,
                        'string':google_db.StringProperty,
                        'text':google_db.TextProperty,
                        'password':google_db.StringProperty,
                        'blob':google_db.BlobProperty,
                        'upload':google_db.StringProperty,
                        'integer':google_db.IntegerProperty,
                        'double':google_db.FloatProperty,
                        'date':google_db.DateProperty,
                        'time':google_db.TimeProperty,        
                        'datetime':google_db.DateTimeProperty,
                        'id':None,
                        'reference':google_db.IntegerProperty,
                        'lower':None,
                        'upper':None,
                        'is null':'IS NULL',
                        'is not null':'IS NOT NULL',
                        'extract':None,
                        'left join':None}}

def cleanup(text):
    if re.compile('[^0-9a-zA-Z_]').findall(text):
        raise SyntaxError, 'only [0-9a-zA-Z_] allowed in table and field names'
    return text   

def assert_filter_fields(*fields):
    for field in fields:
        if isinstance(field,(SQLField,SQLXorable)) and field.type in ['text', 'blob']:
            raise SyntaxError, 'AppEngine does not index by: %s' % (field.type) 

def dateobj_to_datetime(object):                         
    # convert dates,times to datetimes for AppEngine
    if isinstance(object, datetime.date):
        object = datetime.datetime(object.year, object.month, object.day) 
    if isinstance(object, datetime.time):
        object = datetime.datetime(1970, 1, 1, object.hour, object.minute, object.second, object.microsecond)
    return object    

def sqlhtml_validators(field_type,length):
    v={'boolean':[],
       'string':validators.IS_LENGTH(length),
       'text':validators.IS_LENGTH(2**32),
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

class GQLDB(SQLStorage):
    """
    an instance of this class represents a database connection

    Example:
    
       db=GQLDB()
       db.define_table('tablename',SQLField('fieldname1'),
                                   SQLField('fieldname2'))
    """
    def __init__(self):
        self._dbname='gql'
        self['_lastsql']=''
        self.tables=SQLCallableList()
        self._translator=SQL_DIALECTS['google']
    def define_table(self,tablename,*fields,**args):
        tablename=cleanup(tablename)
        if tablename in dir(self) or tablename[0]=='_':
            raise SyntaxError, 'invalid table name'
        if not tablename in self.tables: self.tables.append(tablename)
        else: raise SyntaxError, "table already defined"
        t=self[tablename]=SQLTable(self,tablename,*fields)
        t._create()
        return t
    def __call__(self,where=''):
        return SQLSet(self,where)

class SQLALL(object):
    def __init__(self,table):
        self.table=table

class SQLTable(SQLStorage):
    """
    an instance of this class represents a database table
    Example:
    
    db=GQLDB()
    db.define_table('users',SQLField('name'))
    db.users.insert(name='me') # print db.users._insert(...) to see SQL
    db.users.drop()
    """
    def __init__(self,db,tablename,*fields):
        new_fields=[]
        for field in fields:
            if isinstance(field,SQLField):
                new_fields.append(field)
            elif isinstance(field,SQLTable):
                new_fields+=[copy.copy(field[f]) for f in field.fields if f!='id']
            else:
                raise SyntaxError, "define_table argument is not a SQLField"
        fields=new_fields
        self._db=db
        self._tablename=tablename
        self.fields=SQLCallableList()
        self._referenced_by=[]
        fields=list(fields)
        fields.insert(0,SQLField('id','id'))
        ### GAE Only, make sure uplodaded files go in datastore
        for field in fields:
            if isinstance(field,SQLField) and field.type=='upload' and field.uploadfield==True:
                tmp=field.uploadfield='%s_blob'%field.name
                fields.append(self._db.Field(tmp,'blob',default=''))
        for field in fields:
            self.fields.append(field.name)
            self[field.name]=field
            field._tablename=self._tablename
            field._table=self
            field._db=self._db
        self.ALL=SQLALL(self)
    def _create(self):
        fields=[]
        myfields={}
        for k in self.fields:
            field=self[k]
            attr={}
            if not field.type[:9] in ['id','reference']:
                if field.notnull: attr=dict(required=True)
            if field.type[:2]=='id': continue
            if field.type[:9]=='reference':
                referenced=field.type[10:].strip()
                if not referenced:
                    raise SyntaxError, 'SQLTable: reference to nothing!'
                if not self._db.has_key(referenced):
                    raise SyntaxError, 'SQLTable: table does not exist'
                referee=self._db[referenced]
                ftype=self._db._translator[field.type[:9]](self._db[referenced]._tableobj)
                if self._tablename in referee.fields:  ### THIS IS OK
                    raise SyntaxError, 'SQLField: table name has same name as a field in referenced table'
                self._db[referenced]._referenced_by.append((self._tablename,field.name))
            elif not self._db._translator.has_key(field.type) or \
                 not self._db._translator[field.type]:
                raise SyntaxError, 'SQLField: unkown field type'
            else:                                                      
                ftype=self._db._translator[field.type](**attr)
            myfields[field.name]=ftype
        self._tableobj=classobj(self._tablename,(google_db.Model,),myfields)
        return None
    def create(self):
        # nothing to do, here for backward compatility
        pass
    def drop(self): 
        # nothing to do, here for backward compatility     
        self._db(self.id>0).delete()
    def insert(self,**fields):  
        for field in self.fields:
            if not fields.has_key(field) and self[field].default!=None:
                fields[field]=self[field].default       
            if fields.has_key(field):
                fields[field] = obj_represent(fields[field], self[field].type, self._db)
        tmp=self._tableobj(**fields)
        tmp.put()
        return tmp.key().id()
    def import_from_csv_file(self,csvfile,id_map=None):
        """
        import records from csv file. Column headers must have same names as
        table fields. field 'id' is ignored. If column names read 'table.file'
        the 'table.' prefix is ignored.
        """
        reader = csv.reader(csvfile)
        colnames=None
        if isinstance(id_map,dict) and not id_map.has_key(self._tablename):
           id_map_self=id_map[self._tablename]={}
        def fix(col,value,id_map):
           if value=='<NULL>': return (col,None)
           if id_map and self[col].type[:9]=='reference':
              try: return (col,id_map[self[col].type[9:].strip()][value])
              except KeyError: pass
           return (col,value)
        for line in reader:
            if not colnames:
                colnames=[x[x.find('.')+1:] for x in line]
                c=[i for i in xrange(len(line)) if colnames[i]!='id']
                cid=[i for i in xrange(len(line)) if colnames[i]=='id']
                if cid: cid=cid[0]
            else:
                items=[fix(colnames[i],line[i],id_map) for i in c]
                new_id=self.insert(**dict(items))
                if id_map and cid!=[]: id_map_self[line[cid]]=new_id
    def __str__(self):
        return self._tablename

class SQLXorable(object):
    def __init__(self,name,type='string',db=None):
        self.name,self.type,self._db=name,type,db
    def __str__(self):
        return self.name
    def __or__(self,other): # for use in sortby    
        assert_filter_fields(self,other)
        return SQLXorable(self.name+'|'+other.name,None,None)    
    def __invert__(self):
        assert_filter_fields(self)   
        return SQLXorable('-'+self.name,self.type,None)
    # for use in SQLQuery
    def __eq__(self,value): return SQLQuery(self,'=',value)
    def __ne__(self,value): return SQLQuery(self,'!=',value)
    def __lt__(self,value): return SQLQuery(self,'<',value)
    def __le__(self,value): return SQLQuery(self,'<=',value)
    def __gt__(self,value): return SQLQuery(self,'>',value)
    def __ge__(self,value): return SQLQuery(self,'>=',value)
    #def like(self,value): return SQLQuery(self,' LIKE ',value)
    # def belongs(self,value): return SQLQuery(self,' IN ',value)
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

    a=SQLField(name,'string',length=32,required=False,default=None,requires=IS_NOT_EMPTY(),notnull=False,unique=False,uploadfield=True,widget=None,label=None)
    
    to be used as argument of GQLDB.define_table

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
                 notnull=False,unique=False,uploadfield=True,
                 widget=None,label=None):
        self.name=fieldname=cleanup(fieldname)
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
        self.widget=widget
        self.label=label
        if self.label==None:
            self.label=' '.join([x.capitalize() for x in fieldname.split('_')])
        if requires==sqlhtml_validators: requires=sqlhtml_validators(type,length)
        elif requires is None: requires=[]
        self.requires=requires             # list of validators
    def formatter(self,value):
        if value is None or not self.requires: return value
        if not isinstance(self.requires,(list,tuple)): requires=[self.requires]
        else: requires=copy.copy(self.requires)
        requires.reverse()
        for item in requires:
            if hasattr(item,'formatter'): value=item.formatter(value)
        return value
    def __str__(self): return '%s.%s' % (self._tablename,self.name)

GQLDB.Field=SQLField ### needed in gluon/globals.py session.connect

def obj_represent(obj,fieldtype,db):  
	if obj!=None:
	    if fieldtype=='date' and not isinstance(obj,datetime.date):
	        y,m,d=[int(x) for x in str(obj).strip().split('-')]
	        obj=datetime.date(y,m,d)
	    elif fieldtype=='time' and not isinstance(obj,datetime.time):
	        time_items=[int(x) for x in str(obj).strip().split(':')[:3]]
	        if len(time_items)==3: h,mi,s=time_items
	        else: h,mi,s=time_items+[0]
	        obj=datetime.time(h,mi,s)
	    elif fieldtype=='datetime' and not isinstance(obj,datetime.datetime):
	        y,m,d=[int(x) for x in str(obj)[:10].strip().split('-')]
	        time_items=[int(x) for x in str(obj)[11:].strip().split(':')[:3]]
	        if len(time_items)==3: h,mi,s=time_items
	        else: h,mi,s=time_items+[0]
	        obj=datetime.datetime(y,m,d,h,mi,s)
	    elif fieldtype=='integer' and not isinstance(obj,long):
	        obj = long(obj)
            elif fieldtype=='blob': pass
            elif fieldtype=='boolean':
                if obj and not str(obj)[0].upper()=='F': obj=True
                else: obj=False
            elif isinstance(obj,str): obj=obj.decode('utf8')
	return obj

class QueryException:
    def __init__(self,**a): self.__dict__=a

class SQLQuery(object):
    """
    A query object necessary to define a set.
    It can be stored or can be passed to GQLDB.__call__() to obtain a SQLSet

    Example:
    query=db.users.name=='Max'
    set=db(query)
    records=set.select()
    """
    def __init__(self,left,op=None,right=None):
        if op is None and right is None and isinstance(left,list): 
            self.left = left
            return
        if isinstance(right,(SQLField,SQLXorable)):
            raise SyntaxError, 'SQLQuery: right side of filter must be a value or entity'
        if isinstance(left,SQLField) and left.name=='id':
            if op=='=': 
                self.get_one=QueryException(tablename=left._tablename,id=long(right))
                return
            if op=='>' and long(right)==0L:
                self.get_all=left._tablename 
                return
            else:
                raise SyntaxError, 'not supported'
        if isinstance(left,SQLField):
            # normal filter: field op value
            assert_filter_fields(left)
            right=obj_represent(right,left.type,left._db)  
            # filter dates/times need to be datetimes for GAE
            right=dateobj_to_datetime(right)
            self.left = [(left,op,right)]
            return
        raise SyntaxError, 'not supported'

    def __and__(self,other):  
        # concatenate list of filters
        return SQLQuery(self.left + other.left)
    # def __or__(self,other): return SQLQuery('(%s) OR (%s)'%(self,other))
    # def __invert__(self): return SQLQuery('(NOT %s)'%self)
    def __str__(self): return str(self.left)
    


class SQLSet(object):
    """
    As SQLSet represents a set of records in the database,
    the records are identified by the where=SQLQuery(...) object.
    normally the SQLSet is generated by GQLDB.__call__(SQLQuery(...))

    given a set, for example
       set=db(db.users.name=='Max')
    you can:
       set.update(db.users.name='Massimo')
       set.delete() # all elements in the set
       set.select(orderby=db.users.id,groupby=db.users.name,limitby=(0,10))
    and take subsets:
       subset=set(db.users.id<5)
    """
    def __init__(self,db,where=None):
        self._db=db
        self._tables=[] 
        self.filters=[]    
        if hasattr(where,'get_all'):
           self.where=where
           self._tables.insert(0, where.get_all) 
        elif hasattr(where,'get_one') and isinstance(where.get_one,QueryException):
            self.where=where.get_one
        else:
            # find out which tables are involved 
            if isinstance(where,SQLQuery):
                self.filters=where.left
            self.where=where
            self._tables = [field._tablename for field,op,val in self.filters]  
    def __call__(self,where):
        if isinstance(self.where,QueryException) or\
           isinstance(where,QueryException): raise SyntaxError
        if self.where: return SQLSet(self._db,self.where&where)
        else: return SQLSet(self._db,where)  
    def _get_table_or_raise(self):
        tablenames = list(set(self._tables))   #unique
        if len(tablenames)<1: raise SyntaxError, 'SQLSet: no tables selected'
        if len(tablenames)>1: raise SyntaxError, 'SQLSet: no join in appengine'        
        return self._db[tablenames[0]]._tableobj
    def _select(self,*fields,**attributes):
        valid_attributes=['orderby','groupby','limitby','required',
                          'default','requires','left']  
        if [key for key in attributes.keys() if not key in valid_attributes]:
            raise SyntaxError, 'invalid select attribute'
        if fields and isinstance(fields[0],SQLALL):
            self._tables.insert(0,fields[0].table._tablename)
        table = self._get_table_or_raise()
        tablename = table.kind()       
        items = google_db.Query(table)  
        for filter in self.filters:
            left,op,val = filter
            cond = "%s %s" % (left.name,op)
            items=items.filter(cond,val)  
        if attributes.get('left',None):
            raise SyntaxError, "SQLSet: no left join in appengine"
        if attributes.get('groupby',None):
            raise SyntaxError, "SQLSet: no groupby in appengine"
        if attributes.get('orderby',None):
            assert_filter_fields(attributes['orderby'])
            orders = attributes['orderby'].name.split("|")   
            for order in orders:
                items = items.order(order)
        if attributes.get('limitby',None):
            lmin,lmax=attributes['limitby']   
            limit,offset=(lmax-lmin,lmin)  
            items = items.fetch(limit,offset=offset)     
        return items,tablename,self._db[tablename].fields
    def _getitem_exception(self):
        tablename,id=self.where.tablename,self.where.id
        fields=self._db[tablename].fields
        self.colnames=['%s.%s'%(tablename,t) for t in fields]
        item=self._db[tablename]._tableobj.get_by_id(long(id))
        return item,tablename,fields
    def _select_except(self):
        if not self.where.id: return SQLRows(self._db,[])
        item,tablename,fields=self._getitem_exception()
        if not item: return []
        new_item=[]
        for t in fields:
            if t=='id': new_item.append(int(item.key().id()))
            else: new_item.append(getattr(item,t))
        r=[new_item]
        return SQLRows(self._db,r,*self.colnames)
    def select(self,*fields,**attributes):
        """
        Always returns a SQLRows object, even if it may be empty
        """
        if isinstance(self.where,QueryException): return self._select_except()
        items,tablename,fields=self._select(*fields,**attributes)
        self.colnames=['%s.%s'%(tablename,t) for t in fields]
        self._db['_lastsql']=items
        r=[]

        for item in items:
            new_item=[]
            for t in fields:
                if t=='id': new_item.append(int(item.key().id()))
                else: new_item.append(getattr(item,t))
            r.append(new_item)
        return SQLRows(self._db,r,*self.colnames)      
    def count(self):
        return len(self.select())
    def delete(self):
        if isinstance(self.where,QueryException):
            item,tablename,fields=self._getitem_exception()
            if not item: return 0
            item.delete()
            return 1
        else:
            items,tablename,fields=self._select()
            tableobj=self._db[tablename]._tableobj 
            counter=0
            for item in items:
                tableobj.get(item.key()).delete()
                counter+=1
            return counter
    def update(self,**update_fields):
        db=self._db
        if isinstance(self.where,QueryException):
            item,tablename,fields=self._getitem_exception()
            table=db[tablename]
            if not item: return 0
            for field,value in update_fields.items():
                value=obj_represent(update_fields[field],table[field].type,db) 
                setattr(item,field,value)
            item.put()
            return 1
        else:
            items,tablename,fields=self._select()
            table=db[tablename]
            tableobj=table._tableobj
            counter=0
            for item in items:
                for field,value in update_fields.items():
                    value=obj_represent(update_fields[field],table[field].type,db)
                    setattr(item,field,value)
                item.put()
                counter+=1
            return counter

def update_record(t,s,id,a):
    item=s._tableobj.get_by_id(long(id))
    for key,value in a.items():
       t[key]=value
       setattr(item,key,value)
    item.put()

class SQLRows(object):
    ### this class still needs some work to care for ID/OID
    """
    A wrapper for the return value of a select. It basically represents a table.
    It has an iterator and each row is represented as a dictionary.
    """
    def __init__(self,db,response,*colnames):
        self._db=db
        self.colnames=colnames
        self.response=response
    def __nonzero__(self):
        if len(self.response): return 1
        return 0
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
            packed=self.colnames[j].split('.')
            try: tablename,fieldname=packed
            except:
                 if not row.has_key('_extra'): row['_extra']=SQLStorage()
                 row['_extra'][self.colnames[j]]=value
                 continue
            table=self._db[tablename]
            field=table[fieldname]
            if not row.has_key(tablename):
                row[tablename]=SQLStorage()
            if field.type[:9]=='reference':
                referee=field.type[10:].strip()
                rid=value
                row[tablename][fieldname]=rid
                #row[tablename][fieldname]=SQLSet(self._db[referee].id==rid)
            elif field.type=='boolean' and value!=None:
                if value==True or value=='T': row[tablename][fieldname]=True
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
                row[tablename].update_record=lambda t=row[tablename],\
                    s=self._db[tablename],id=id,**a: update_record(t,s,id,a)
                for referee_table,referee_name in table._referenced_by:
                    s=self._db[referee_table][referee_name]
                    row[tablename][referee_table]=SQLSet(self._db,s==id)
        if len(row.keys())==1: return row[row.keys()[0]]
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
        def none_exception(value):
            if isinstance(value,unicode): return value.encode('utf8')
            if value==None: return '<NULL>'
            return value
        for record in self:
            row=[]
            for col in self.colnames:
                if not table_field.match(col):
                    row.append(record._extra[col])
                else:
                    t,f=col.split('.')
                    if isinstance(record.get(t,None),SQLStorage):
                        row.append(none_exception(record[t][f]))
                    else: row.append(none_exception(record[f]))
            writer.writerow(row)
        return s.getvalue()
    def xml(self):
        """
        serializes the table using sqlhtml.SQLTABLE (if present)
        """
        return sqlhtml.SQLTABLE(self).xml()
        
def test_all():
    """
    How to run from web2py dir:
     export PYTHONPATH=.:YOUR_PLATFORMS_APPENGINE_PATH
     eg. on OSX:
       echo $PYTHONPATH 
       .:/Applications/GoogleAppEngineLauncher.app/Contents/Resources/GoogleAppEngine-default.bundle/Contents/Resources/google_appengine
    python gluon/contrib/gql.py 

    Setup the UTC timezone and database stubs       

    >>> import os
    >>> os.environ['TZ'] = 'UTC'
    >>> # dev_server sets APPLICATION_ID, but we are not using dev_server, so manually set it to something
    >>> os.environ['APPLICATION_ID'] = 'test' 
    >>> import time
    >>> if hasattr(time, 'tzset'):
    ...   time.tzset()
    >>>
    >>> from google.appengine.api import apiproxy_stub_map 
    >>> from google.appengine.api import datastore_file_stub
    >>> apiproxy_stub_map.apiproxy = apiproxy_stub_map.APIProxyStubMap()       
    >>> apiproxy_stub_map.apiproxy.RegisterStub('datastore_v3',\
            datastore_file_stub.DatastoreFileStub('doctests_your_app_id', '/dev/null', '/dev/null'))

        Create a table with all possible field types  

    >>> db=GQLDB()
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

    Select all

    # >>> all = db().select(db.users.ALL)

    Drop the table   

    >>> db.users.drop() 

    Select many entities

    >>> tmp = db.define_table("posts",\
              SQLField('body','text'),\
              SQLField('total','integer'),\
              SQLField('created_at','datetime'))
    >>> many = 20   #2010 # more than 1000 single fetch limit (it can be slow) 
    >>> few = 5
    >>> most = many - few
    >>> 0 < few < most < many
    True
    >>> for i in range(many):
    ...     f=db.posts.insert(body='',\
                total=i,created_at=datetime.datetime(2008, 7, 6, 14, 15, 42, i))
    >>> 
    >>> len(db().select(db.posts.ALL)) == many
    True
    >>> len(db().select(db.posts.ALL,limitby=(0,most))) == most
    True
    >>> len(db().select(db.posts.ALL,limitby=(few,most))) == most - few 
    True
    >>> order = ~db.posts.total|db.posts.created_at
    >>> results = db().select(db.posts.ALL,limitby=(most,most+few),orderby=order)
    >>> len(results) == few
    True
    >>> results[0].total == few - 1
    True
    >>> results = db().select(db.posts.ALL,orderby=~db.posts.created_at)
    >>> results[0].created_at > results[1].created_at
    True
    >>> results = db().select(db.posts.ALL,orderby=db.posts.created_at)
    >>> results[0].created_at < results[1].created_at
    True

    >>> db(db.posts.total==few).count()
    1

    >>> db(db.posts.id==2*many).count()
    0

    >>> db(db.posts.id==few).count()
    1

    >>> db(db.posts.id==str(few)).count()
    1
    >>> len(db(db.posts.id>0).select()) == many
    True

    >>> db(db.posts.id>0).count() == many
    True
    
    >>> set=db(db.posts.total>=few)
    >>> len(set.select())==most
    True

    >>> len(set(db.posts.total<=few).select())
    1

    # test timezones
    >>> class TZOffset(datetime.tzinfo):
    ...   def __init__(self,offset=0):
    ...     self.offset = offset
    ...   def utcoffset(self, dt): return datetime.timedelta(hours=self.offset)
    ...   def dst(self, dt): return datetime.timedelta(0)
    ...   def tzname(self, dt): return 'UTC' + str(self.offset)
    ... 
    >>> SERVER_OFFSET = -8
    >>> 
    >>> stamp = datetime.datetime(2008, 7, 6, 14, 15, 42, 828201)
    >>> post_id = db.posts.insert(created_at=stamp)
    >>> naive_stamp = db(db.posts.id==post_id).select()[0].created_at
    >>> utc_stamp=naive_stamp.replace(tzinfo=TZOffset()) 
    >>> server_stamp = utc_stamp.astimezone(TZOffset(SERVER_OFFSET))
    >>> stamp == naive_stamp
    True
    >>> utc_stamp == server_stamp
    True
    >>> db(db.posts.id>0).count() == many + 1
    True
    >>> db(db.posts.id==post_id).delete()
    >>> db(db.posts.id>0).count() == many
    True

    >>> id = db.posts.insert(total='0')   # coerce str to integer 
    >>> db(db.posts.id==id).delete() 
    >>> db(db.posts.id > 0).count() == many 
    True
    >>> set=db(db.posts.id>0)  
    >>> set.update(total=0)                # update entire set
    >>> db(db.posts.total == 0).count() == many 
    True

    >>> db.posts.drop()
    >>> db(db.posts.id>0).count()
    0

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
    >>> me = db(db.person.id==person_id).select()[0]
    >>> me.name
    'massimo'
    >>> str(me.birth)
    '1971-12-21'

    # resave date to ensure it comes back the same
    >>> me=db(db.person.name=='Massimo').update(birth=me.birth) # test update
    >>> me = db(db.person.id==person_id).select()[0]
    >>> me.birth
    datetime.date(1971, 12, 21)
    >>> db(db.person.name=='Marco').delete() # test delete
    >>> len(db().select(db.person.ALL))
    1

    Update a single record

    >>> me.update_record(name="Max")
    >>> me.name
    'Max'

    Examples of complex search conditions

    >>> len(db((db.person.name=='Max')&(db.person.birth<'2003-01-01')).select())
    1
    >>> len(db((db.person.name=='Max')&(db.person.birth<datetime.date(2003,01,01))).select())
    1

    # >>> len(db((db.person.name=='Max')|(db.person.birth<'2003-01-01')).select())
    # 1       
    >>> me=db(db.person.id==person_id).select(db.person.name)[0] 
    >>> me.name
    'Max'
  
    Examples of search conditions using extract from date/datetime/time

    # >>> len(db(db.person.birth.month()==12).select())
    # 1
    # >>> len(db(db.person.birth.year()>1900).select())
    # 1       

    Example of usage of NULL

    >>> len(db(db.person.birth==None).select()) ### test NULL
    0

    # filter api does not support != yet
    # >>> len(db(db.person.birth!=None).select()) ### test NULL
    # 1      

    Examples of search consitions using lower, upper, and like

    # >>> len(db(db.person.name.upper()=='MAX').select())
    # 1  
    # >>> len(db(db.person.name.like('%ax')).select())
    # 1  
    # >>> len(db(db.person.name.upper().like('%AX')).select())
    # 1  
    # >>> len(db(~db.person.name.upper().like('%AX')).select())
    # 0   

    orderby, groupby and limitby 

    >>> people=db().select(db.person.ALL,orderby=db.person.name)
    >>> order=db.person.name|~db.person.birth
    >>> people=db().select(db.person.ALL,orderby=order)
     
    # no groupby in appengine
    # >>> people=db().select(db.person.ALL,orderby=db.person.name,groupby=db.person.name)
    
    >>> people=db().select(db.person.ALL,orderby=order,limitby=(0,100))

    Example of one 2 many relation

    >>> tmp=db.define_table('dog', \
              SQLField('name'), \
              SQLField('birth','date'), \
              SQLField('owner',db.person),\
              migrate='test_dog.table')
    >>> dog_id=db.dog.insert(name='Snoopy',birth=None,owner=person_id)

    A simple JOIN

    >>> len(db(db.dog.owner==person_id).select())
    1
    
    >>> len(db(db.dog.owner==me.id).select())
    1

    # test a table relation 

    >>> dog = db(db.dog.id==dog_id).select()[0]
    >>> me = db(db.person.id==dog.owner).select()[0]
    >>> me.dog.select()[0].name
    'Snoopy'

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

    >>> authorships=db(db.authorship.author_id==aid).select()
    >>> for authorship in authorships: 
    ...     papers=db(db.paper.id==authorship.paper_id).select() 
    ...     for paper in papers: print paper.title
    QCD
     

    Example of search condition using  belongs

    # >>> set=(1,2,3)
    # >>> rows=db(db.paper.id.belongs(set)).select(db.paper.ALL)
    # >>> print rows[0].title
    # QCD   

    Example of search condition using nested select

    # >>> nested_select=db()._select(db.authorship.paper_id)
    # >>> rows=db(db.paper.id.belongs(nested_select)).select(db.paper.ALL)
    # >>> print rows[0].title
    # QCD       

    Output in csv

    # >>> str(authored_papers.select(db.author.name,db.paper.title))
    # 'author.name,paper.title\\r\\nMassimo,QCD\\r\\n'    

    Delete all leftover tables

    # >>> GQLDB.distributed_transaction_commit(db)

    >>> db.authorship.drop()
    >>> db.author.drop()
    >>> db.paper.drop()
    """

if __name__=='__main__':
    import doctest
    doctest.testmod()



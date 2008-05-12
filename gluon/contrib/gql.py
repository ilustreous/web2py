"""
This file is part of web2py Web Framework (Copyrighted, 2007)
Developed by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: GPL v2
"""

__all__=['GQLDB','SQLField'] 

import re, sys, os, types, cPickle, datetime, thread, cStringIO, csv, copy, socket, logging
import gluon.validators as validators
import gluon.sqlhtml as sqlhtml
from new import classobj
from google.appengine.ext import db as google_db

SQL_DIALECTS={'google':{'boolean':google_db.StringProperty,
                        'string':google_db.StringProperty,
                        'text':google_db.TextProperty,
                        'password':google_db.StringProperty,
                        'blob':google_db.BlobProperty,
                        'upload':google_db.BlobProperty,
                        'integer':google_db.IntegerProperty,
                        'double':google_db.FloatProperty,
                        'date':google_db.DateProperty,
                        'time':google_db.TimeProperty,        
                        'datetime':google_db.DateTimeProperty,
                        'id':None,
                        'reference':google_db.ReferenceProperty,
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
    
       db=SQLDB()
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
        t=self[tablename]=GQLTable(self,tablename,*fields)
        t._create()
    def __call__(self,where=''):
        return SQLSet(self,where)

class SQLALL(object):
    def __init__(self,table):
        self.table=table
    def __str__(self):
        s=['%s.%s'%(self.table._tablename,name) for name in self.table.fields]
        return ', '.join(s)

class GQLTable(SQLStorage):
    """
    an instance of this class represents a database table
    Example:
    
    db=GQLDB()
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
                    raise SyntaxError, 'GQLTable: reference to nothing!'
                if not self._db.has_key(referenced):
                    raise SyntaxError, 'GQLTable: table does not exist'
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
        pass
    def insert(self,**fields):
        tmp=self._tableobj(**fields)
        tmp.put()
        return tmp.key().id()
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
    #def like(self,value): return SQLQuery(self,' LIKE ',value)
    #def belongs(self,value): return SQLQuery(self,' IN ',value)
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

    a=SQLField(name,'string',length=32,required=False,default=None,requires=IS_NOT_EMPTY(),notnull=False,unique=False)
    
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
                 notnull=False,unique=False):
        self.name=cleanup(fieldname)
        if fieldname in dir(GQLTable) or fieldname[0]=='_':
            raise SyntaxError, 'SQLField: invalid field name'
        if isinstance(type,GQLTable): type='reference '+type._tablename
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

def sql_represent(object,fieldtype,dbname):    
    if object is None: return ''
    if fieldtype=='boolean':
         if object and not str(object)[0].upper()=='F': return "'T'"
         else: return "'F'"
    if fieldtype[0]=='i': return str(int(object))
    elif fieldtype[0]=='r': return str(int(object))
    elif fieldtype=='double': return str(float(object))
    if isinstance(object,unicode): object=object.encode('utf-8')
    if fieldtype=='date':
         if isinstance(object,(datetime.date,datetime.datetime)): object=object.strftime('%Y-%m-%d')
         else: object=str(object)
         if dbname=='oracle': return "to_date('%s','yyyy-mm-dd')" % object
    elif fieldtype=='datetime':
         if isinstance(object,datetime.datetime): object=object.strftime('%Y-%m-%d %H:%M:%S')
         elif isinstance(object,datetime.date): object=object.strftime('%Y-%m-%d 00:00:00')
         else: object=str(object)
         if dbname=='oracle': return "to_date('%s','yyyy-mm-dd hh24:mi:ss')" % object
    elif fieldtype=='time':
         if isinstance(object,datetime.time): object=object.strftime('%H:%M:%S')
         else: object=str(object)
    else: object=str(object)
    return "'%s'" % object.replace("'","''")  ### escape

class QueryException:
    def __init__(self,**a): self.__dict__=a

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
        if left.name=='id':
            if op=='=':
                self.sql=QueryException(tablename=left._tablename,id=int(right))
                return
            else: raise SyntaxError, 'not supported'
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
    def __and__(self,other): return SQLQuery('%s AND %s'%(self,other))
    # def __or__(self,other): return SQLQuery('(%s) OR (%s)'%(self,other))
    # def __invert__(self): return SQLQuery('(NOT %s)'%self)
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
        if hasattr(where,'sql') and isinstance(where.sql,QueryException):
            self.sql_w=where.sql
            return
        # find out wchich tables are involved
        self.sql_w=str(where)
        self._tables=parse_tablenames(self.sql_w)
    def __call__(self,where):
        if isinstance(self.sql_w,QueryException) or\
           isinstance(where,QueryException): raise SyntaxeError
        return SQLSet(self._db,SQLQuery(self.sql_w)&where)
    def _select(self,*fields,**attributes):
        valid_attributes=['orderby','groupby','limitby','required',
                          'default','requires','left']
        if [key for key in attributes.keys() if not key in valid_attributes]:
            raise SyntaxError, 'invalid select attribute'
        ### if not fields specified take them all from the requested tables
        if not fields or not isinstance(fields[0],SQLALL):
            fields=[self._db[table].ALL for table in self._tables]
        sql_f=', '.join([str(f) for f in fields])
        tablenames=parse_tablenames(self.sql_w+' '+sql_f)
        if len(tablenames)<1: raise SyntaxError, 'SQLSet: no tables selected'
        if len(tablenames)>1: raise SyntaxError, 'SQLSet: no join in appengine'
        self.colnames=[c.strip() for c in sql_f.split(', ')]
        if self.sql_w: sql_w=' WHERE '+self.sql_w
        else: sql_w=''
        sql_o=''
        if attributes.has_key('left') and attributes['left']: 
            join=attributes['left']
            if not isinstance(join,(tuple,list)): join=[join]
            join=[str(t) for t in join]
            excluded=[t for t in tablenames if not t in join]
            command=self._db._translator['left join']           
            sql_t='%s %s %s' %(', '.join(excluded),command,', '.join(join))
        else:
            sql_t=', '.join(tablenames)
        if attributes.has_key('groupby') and attributes['groupby']: 
            sql_o+=' GROUP BY %s'% attributes['groupby']
        if attributes.has_key('orderby') and attributes['orderby']: 
            sql_o+=' ORDER BY %s'% attributes['orderby']
        if attributes.has_key('limitby') and attributes['limitby']: 
            lmin,lmax=attributes['limitby']
        tablename=tablenames[0]
        q='SELECT * FROM %s%s%s;'%(sql_t,sql_w,sql_o) 
        p=None
        regex_undot=re.compile("^(?P<a>(([^']*'){2})*[^']*)(?P<b>%s\.)(?P<c>.*)$"%tablename)
        while p!=q:
           p=q
           q=regex_undot.sub('\g<a>\g<c>',p)
        return q,tablename,self._db[tablename].fields
    def _select_except(self):
        tablename,id=self.sql_w.tablename,self.sql_w.id
        fields=self._db[tablename].fields
        self.colnames=['%s.%s'%(tablename,t) for t in fields]
        item=self._db[tablename]._tableobj.get_by_id(id)
        new_item=[]
        for t in fields:
            if t=='id': new_item.append(id)
            else: new_item.append(getattr(item,t))
        r=[new_item]
        return SQLRows(self._db,r,*self.colnames)
    def select(self,*fields,**attributes):
        """
        Always returns a SQLRows object, even if it may be empty
        """
        logging.warning(self.sql_w)
        if isinstance(self.sql_w,QueryException): return self._select_except()
        query,tablename,fields=self._select(*fields,**attributes)
        self.colnames=['%s.%s'%(tablename,t) for t in fields]
        self._db['_lastsql']=query
        r=[]
        for item in google_db.GqlQuery(query[:-1]):
            new_item=[]
            for t in fields:
                if t=='id': new_item.append(int(item.key().id()))
                else: new_item.append(getattr(item,t))
            r.append(new_item)
        return SQLRows(self._db,r,*self.colnames)      
    def delete(self):
        query,tablename,fields=self._select()
        tableobj=self._db[tablename]._tableobj
        for item in google_db.GqlQuery(query[:-1]):
            tableobj.get_by_id(int(item.key().id())).delete()
    def update(self,**update_fields):
        query,tablename,fields=self._select()
        tableobj=self._db[tablename]._tableobj
        for item in google_db.GqlQuery(query[:-1]):
            for key,value in update_fields.items():
                setattr(item,key,value)
            item.put()

def update_record(t,s,id,a):
    item=s._tableobj.get_by_id(int(id))
    for key,value in a.items():
       t[key]=value
       setattr(item,key,value)
    item.put()

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
                if value=='T': row[tablename][fieldname]=True
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
        return sqlhtml.SQLTABLE(self).xml() 
        
def test_all():
    """    

    Create a table with all possible field types
    'sqlite://test.db'
    'mysql://root:none@localhost/test'
    'postgres://mdipierro:none@localhost/test'

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

    >>> len(db(db.dog.owner==db.person.id).select(left=db.dog))
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



"""
This file is part of web2py Web Framework (Copyrighted, 2007)
Developed by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: GPL v2
"""

import re, random, copy, sys, types, datetime, time, cgi, hmac
import gluon.sql 
try: 
    import hashlib
    have_hashlib=True
except:
    import sha, md5
    have_hashlib=False
from storage import Storage

__all__=['IS_ALPHANUMERIC', 'IS_DATE', 'IS_DATETIME', 'IS_EMAIL', 'IS_EXPR','IS_FLOAT_IN_RANGE', 'IS_INT_IN_RANGE', 'IS_IN_SET', 'IS_LENGTH', 'IS_LOWER', 'IS_MATCH', 'IS_NOT_EMPTY', 'IS_TIME', 'IS_URL', 'CLEANUP', 'CRYPT', 'IS_IN_DB', 'IS_NOT_IN_DB', 'IS_UPPER', 'IS_NULL_OR']

class IS_MATCH:
    """
    example:

    INPUT(_type='text',_name='name',requires=IS_MATCH('.+'))
    
    the argument of IS_MATCH is a regular expression.

    IS_MATCH('.+')('hello') returns ('hello',None)
    IS_MATCH('.+')('') returns ('','invalid!')   
    """
    def __init__(self,expression,error_message='invalid expression!'):
        self.regex=re.compile(expression)
        self.error_message=error_message
    def __call__(self,value):
        match=self.regex.match(value)        
        if match: return (match.group(),None)
        return (value,self.error_message)

class IS_EXPR:
    """
    example:

    INPUT(_type='text',_name='name',requires=IS_EXPR('5<int(value)<10'))
    
    the argument of IS_EXPR must be python condition

    IS_EXPR('int(value)<2')('1') returns (1,None)
    IS_EXPR('int(value)<2')('2') returns ('2','invalid expression!')   
    """
    def __init__(self,expression,error_message='invalid expression!'):
        self.expression=expression
        self.error_message=error_message
    def __call__(self,value):        
        environment={'value':value}
        exec('__ret__='+self.expression) in environment
        if environment['__ret__']: return (value,None)        
        return (value,self.error_message)

class IS_LENGTH:
    """
    example:

    INPUT(_type='text',_name='name',requires=IS_LENGTH(32))
    
    the argument of IS_LENGTH is the man number of characters
    """
    def __init__(self,size,error_message='too long!'):
        self.size=size
        self.error_message=error_message
    def __call__(self,value):
        if isinstance(value,cgi.FieldStorage):
            if len(value.value)<=self.size: return (value,None) # for uploads
        elif isinstance(value,(str,unicode)): 
            if len(value)<=self.size: return (value,None)      
        elif len(str(value))<=self.size: return (value,None)      
        return (value,self.error_message)

class IS_IN_SET:
    """
    example:

    INPUT(_type='text',_name='name',requires=IS_IN_SET(['max','john']))
    
    the argument of IS_IN_SET must be a list or set
    """
    def __init__(self,theset,labels=None,error_message='value not allowed!'):
        self.theset=[str(item) for item in theset]
        self.labels=labels
        self.error_message=error_message
    def __call__(self,value):
        if value in self.theset: return (value,None)
        return (value,self.error_message)

def IS_IN_DB(dbset,field,label=None,error_message='value not in database!'):
    """
    example:

    INPUT(_type='text',_name='name',requires=IS_IN_DB(db,db.table))
 
    used for reference fields, rendered as a dropbox
    """
    try: dbset=dbset() # dbset is a db
    except TypeError: pass # else dbset is a SQLSet as should be 
    ktable=str(field).split('.')[0]
    kfield=str(field).split('.')[-1]
    if not label: label='%%(%s)s' % kfield    
    elif str(label).find('%')<0: label='%%(%s)s' % str(label).split('.')[-1]
    ks=re.compile('%\((?P<name>[^\)]+)\)s').findall(label)    
    if not kfield in ks: ks+=[kfield]
    fields=['%s.%s'%(ktable,k) for k in ks]    
    records=dbset.select(*fields,**dict(orderby=', '.join(fields)))
    theset=[r[kfield] for r in records]    
    labels=[label % dict(r) for r in records]
    return IS_IN_SET(theset,labels,error_message)

class IS_NOT_IN_DB:
    """
    example:

    INPUT(_type='text',_name='name',requires=IS_NOT_IN_DB(db,db.table))
 
    makes the field unique
    """
    def __init__(self,dbset,field,error_message='value already in database!'):
        self.dbset=dbset
        self.field=field
        self.error_message=error_message
        self.record_id=0
    def __call__(self,value):        
        fieldname=str(self.field)
        id_field='%s.id' % fieldname[:fieldname.find('.')]
        value_field=gluon.sql.sql_represent(value,'string',None)
        if not self.record_id: value_id='0'
        else: value_id=gluon.sql.sql_represent(self.record_id,'integer',None)
        fetched=self.dbset("%s=%s AND %s<>%s" % (fieldname,value_field,id_field,value_id)).select('count(*)')
        if fetched[0]['count(*)']==0: return (value,None)
        return (value,self.error_message)

class IS_INT_IN_RANGE:
    """
    example:

    INPUT(_type='text',_name='name',requires=IS_INT_IN_RANGE(0,10))
    """
    def __init__(self,minimum,maximum,error_message='too small or too large!'):
        self.minimum=minimum
        self.maximum=maximum
        self.error_message=error_message
    def __call__(self,value):
        try:
            fvalue=float(value)
            value=int(value)
            if value==fvalue and self.minimum<=value<self.maximum: 
                return (value,None)
        except ValueError: pass
        return (value,self.error_message)

class IS_FLOAT_IN_RANGE:
    """
    example:

    INPUT(_type='text',_name='name',requires=IS_FLOAT_IN_RANGE(0,10))
    """
    def __init__(self,minimum,maximum,error_message='too small or too large!'):
        self.minimum=minimum
        self.maximum=maximum
        self.error_message=error_message
    def __call__(self,value):        
        try:
            value=float(value)
            if self.minimum<=value<=self.maximum: return (value,None)
        except ValueError: pass
        return (value,self.error_message)

class IS_NOT_EMPTY:
    """
    example:

    INPUT(_type='text',_name='name',requires=IS_NOT_EMPTY())
    """
    def __init__(self,error_message='cannot be empty!'):
        self.error_message=error_message
    def __call__(self,value):
        if value==None or value=='': return (value,self.error_message)
        return (value,None)

class IS_ALPHANUMERIC(IS_MATCH): 
    """
    example:

    INPUT(_type='text',_name='name',requires=IS_ALPHANUMERIC())
    """
    def __init__(self,error_message='must be alphanumeric!'):
        IS_MATCH.__init__(self,'^[\w]*$',error_message)

class IS_EMAIL(IS_MATCH):
    """
    example:

    INPUT(_type='text',_name='name',requires=IS_EMAIL())
    """
    def __init__(self,error_message='invalid email!'):
        IS_MATCH.__init__(self,'^\w+(.\w+)*@(\w+.)+(\w+)$',error_message)

class IS_URL(IS_MATCH):
    """
    example:

    INPUT(_type='text',_name='name',requires=IS_URL())
    """
    def __init__(self,error_message='invalid url!'):
        IS_MATCH.__init__(self,'^http\://(\w+.)*(\w+)$',error_message)

class IS_TIME:
    """
    example:

    INPUT(_type='text',_name='name',requires=IS_TIME())

    understands the follwing formats
    hh:mm:ss [am/pm]
    hh:mm [am/pm]
    hh [am/pm]

    [am/pm] is options, ':' can be replaced by any other non-digit
    """
    def __init__(self,error_message='must be HH:MM:SS!'):
        self.error_message=error_message
    def __call__(self,value):
        try:
            ivalue=value
            value=re.compile('((?P<h>[0-9]+))([^0-9 ]+(?P<m>[0-9 ]+))?([^0-9ap ]+(?P<s>[0-9]*))?((?P<d>[ap]m))?').match(value.lower())
            h,m,s=int(value.group('h')),0,0
            if value.group('m')!=None: m=int(value.group('m'))
            if value.group('s')!=None: s=int(value.group('s'))
            if value.group('d')=='pm' and 0<h<12: h=h+12
            if not (h in range(24) and m in range(60) and s in range(60)):
                raise ValueError
            value='%.2i:%.2i:%.2i' % (h,m,s)
            return (value,None)
        except AttributeError: pass
        except ValueError: pass
        return (ivalue,self.error_message)

class IS_DATE:
    """
    example:

    INPUT(_type='text',_name='name',requires=IS_DATE())

    date has to be in the ISO8960 format YYYY-MM-DD
    """
    def __init__(self,format='%Y-%m-%d',error_message='must be YYYY-MM-DD!'):
        self.format=format
        self.error_message=error_message
    def __call__(self,value):
        try:
            y, m, d, hh, mm, ss, t0, t1, t2=time.strptime(value,self.format)
            value=datetime.date(y,m,d).isoformat()            
            return (value,None)
        except:
            return (value,self.error_message)
    def formatter(self,value):
        return value.strftime(self.format)

class IS_DATETIME:
    """
    example:

    INPUT(_type='text',_name='name',requires=IS_DATETIME())

    datetime has to be in the ISO8960 format YYYY-MM-DD hh:mm:ss
    """
    isodatetime='%Y-%m-%d %H:%M:%S'
    def __init__(self,format='%Y-%m-%d %H:%M:%S',error_message='must be YYYY-MM-DD HH:MM:SS!'):
        self.format=format
        self.error_message=error_message        
    def __call__(self,value):
        try:
            y, m, d, hh, mm, ss, t0, t1, t2=time.strptime(value,self.format)
            value=datetime.datetime(y,m,d,hh,mm,ss).strftime(self.isodatetime)
            return (value,None)
        except:
            return (value,self.error_message)
    def formatter(self,value):
        return value.strftime(self.format)

class IS_LOWER:
    def __call__(self,value): return (value.lower(),None)

class IS_UPPER:
    def __call__(self,value): return (value.upper(),None)

class IS_NULL_OR:
    def __init__(self,other,null=None):
        self.other,self.null=other,null
    def __call__(self,value):
        if not value: return (self.null,None)
        return self.other(value)
    def formatter(self,value):
        if hasattr(self.other,'formatter'):
            return self.other.formatter(value)
        return value

class CLEANUP:
    """
    example:

    INPUT(_type='text',_name='name',requires=CLEANUP())

    removes special characters on validation
    """   
    def __init__(self): pass
    def __call__(self,value):
        v=''
        for c in str(value).strip():
            if ord(c) in [10,13]+range(32,127): v+=c
        return (v,None)

class CRYPT:
    """
    example:

    INPUT(_type='text',_name='name',requires=CRYPT())

    encodes the value on validation with md5 checkshum
    """   
    def __init__(self,key=None):
        self.key=key
    def __call__(self,value):        
        if self.key: 
            if have_hashlib: return (hmac.new(self.key,value,hashlib.sha512).hexdigest(),None)
            else: return (hmac.new(self.key,value,sha).hexdigest(),None)
        if have_hashlib: return (hashlib.md5(value).hexdigest(),None)
        else: return (md5.new(value).hexdigest(),None)


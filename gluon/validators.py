"""
This file is part of web2py Web Framework (Copyrighted, 2007)
Developed by Massimo Di Pierro <mdipierro@cs.depaul.edu>
Thanks to ga2arch for help with IS_IN_DB and IS_NOT_IN_DB on GAE
License: GPL v2
"""

import os, re, copy, sys, types, datetime, time, cgi, hmac
try: 
    import hashlib
    have_hashlib=True
except:
    import sha, md5
    have_hashlib=False
from storage import Storage

__all__=['IS_ALPHANUMERIC', 'IS_DATE', 'IS_DATETIME', 'IS_EMAIL', 'IS_EXPR','IS_FLOAT_IN_RANGE', 'IS_INT_IN_RANGE', 'IS_IN_SET', 'IS_LENGTH', 'IS_LIST_OF', 'IS_LOWER', 'IS_MATCH', 'IS_NOT_EMPTY', 'IS_TIME', 'IS_URL', 'CLEANUP', 'CRYPT', 'IS_IN_DB', 'IS_NOT_IN_DB', 'IS_UPPER', 'IS_NULL_OR']

class IS_MATCH(object):
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

class IS_EXPR(object):
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

class IS_LENGTH(object):
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
            if value.file:
                value.file.seek(0,os.SEEK_END)
                length=value.file.tell()
                value.file.seek(0,os.SEEK_SET)
            else:
                val=value.value
                if val: length=len(val)
                else: length=0
            if length<=self.size: return (value,None) # for uploads
        elif isinstance(value,(str,unicode,list)): 
            if len(value)<=self.size: return (value,None)      
        elif len(str(value))<=self.size: return (value,None)
        return (value,self.error_message)

class IS_IN_SET(object):
    """
    example:

    INPUT(_type='text',_name='name',requires=IS_IN_SET(['max','john']))
    
    the argument of IS_IN_SET must be a list or set
    """
    def __init__(self,theset,labels=None,error_message='value not allowed!'):
        self.theset=[str(item) for item in theset]
        self.labels=labels
        self.error_message=error_message
    def options(self):
        if self.labels:
             return [(k,self.labels[i]) for i,k in enumerate(self.theset)]
        else:
             return [(k,k) for k in self.theset]
    def __call__(self,value):
        if value in self.theset: return (value,None)
        return (value,self.error_message)

regex1=re.compile('[\w_]+\.[\w_]+')
regex2=re.compile('%\((?P<name>[^\)]+)\)s')

class IS_IN_DB(object):
    """
    example:

    INPUT(_type='text',_name='name',requires=IS_IN_DB(db,db.table))

    used for reference fields, rendered as a dropbox
    """
    def __init__(self,dbset,field,label=None,error_message='value not in database!'):
        if hasattr(dbset,'define_table'): self.dbset=dbset()
        else: self.dbset=dbset
        ktable,kfield=str(field).split('.')
        if not label:
            label='%%(%s)s' % kfield
        elif regex1.match(str(label)):
            label='%%(%s)s' % str(label).split('.')[-1]
        ks=regex2.findall(label)
        if not kfield in ks: ks+=[kfield]
        fields=['%s.%s'%(ktable,k) for k in ks]
        self.fields=fields
        self.field=field
        self.label=label
        self.ktable=ktable
        self.kfield=kfield
        self.ks=ks
        self.error_message=error_message
        self.theset=None
    def build_set(self):
        if self.dbset._db._dbname!='gql':
           dd=dict(orderby=', '.join(self.fields))
           records=self.dbset.select(*self.fields,**dd)
        else:
           dd=dict(orderby=', '.join([k for k in self.ks if k!='id']))
           if not dd: dd=None
           records=self.dbset.select(self.dbset._db[self.ktable].ALL,**dd)
        self.theset=[str(r[self.kfield]) for r in records]
        self.labels=[self.label % dict(r) for r in records]        
    def options(self):
        self.build_set()
        if self.labels:
             return [(k,self.labels[i]) for i,k in enumerate(self.theset)]
        else:
             return [(k,k) for k in self.theset]
    def __call__(self,value):
        if self.theset: 
            if value in self.theset:
                return (value,None)
        else:
            field=self.dbset._db[self.ktable][self.kfield]
            if len(self.dbset(field==value).select(limitby=(0,1))):
                 return (value,None)
        return (value,self.error_message)         

class IS_NOT_IN_DB(object):
    """
    example:

    INPUT(_type='text',_name='name',requires=IS_NOT_IN_DB(db,db.table))
 
    makes the field unique
    """
    def __init__(self,dbset,field,error_message='value already in database!'):
        if hasattr(dbset,'define_table'): self.dbset=dbset()
        else: self.dbset=dbset
        self.field=field
        self.error_message=error_message
        self.record_id=0
    def set_self_id(self,id): self.record_id=id
    def __call__(self,value):        
        tablename,fieldname=str(self.field).split('.')
        db=self.dbset._db        
        rows=self.dbset(db[tablename][fieldname]==value).select(limitby=(0,1))
        if len(rows)>0 and str(rows[0].id)!=str(self.record_id): 
            return (value,self.error_message)
        return (value,None)

class IS_INT_IN_RANGE(object):
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

class IS_FLOAT_IN_RANGE(object):
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

class IS_NOT_EMPTY(object):
    """
    example:

    INPUT(_type='text',_name='name',requires=IS_NOT_EMPTY())
    """
    def __init__(self,error_message='cannot be empty!'):
        self.error_message=error_message
    def __call__(self,value):
        if value==None or value=='' or value==[]: 
            return (value,self.error_message)
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
        IS_MATCH.__init__(self,'^(http|HTTP|https|HTTPS|ftp|FTP|file|FILE|rstp|RSTP)\://[\w/=&\?\.]+$',error_message)

regex_time=re.compile('((?P<h>[0-9]+))([^0-9 ]+(?P<m>[0-9 ]+))?([^0-9ap ]+(?P<s>[0-9]*))?((?P<d>[ap]m))?')

class IS_TIME(object):
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
            value=regex_time.match(value.lower())
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

class IS_DATE(object):
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
            y, m, d, hh, mm, ss, t0, t1, t2=time.strptime(value,str(self.format))
            value=datetime.date(y,m,d)
            return (value,None)
        except:
            return (value,self.error_message)
    def formatter(self,value):
        return value.strftime(str(self.format))

class IS_DATETIME(object):
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
            y, m, d, hh, mm, ss, t0, t1, t2=time.strptime(value,str(self.format))
            value=datetime.datetime(y,m,d,hh,mm,ss)
            return (value,None)
        except:
            return (value,self.error_message)
    def formatter(self,value):
        return value.strftime(str(self.format))

class IS_LIST_OF(object):
    def __init__(self,other):
        self.other=other
    def __call__(self,value):
        ivalue=value
        if not isinstance(value,list): ivalue=[ivalue]
        new_value=[]
        for item in ivalue:
            v,e=self.other(item)
            if e: return (value,e)
            else: new_value.append(v)
        return (new_value,None)

class IS_LOWER(object):
    def __call__(self,value): return (value.lower(),None)

class IS_UPPER(object):
    def __call__(self,value): return (value.upper(),None)

class IS_NULL_OR(object):
    def __init__(self,other,null=None):
        self.other,self.null=other,null
    def set_self_id(self,id):
        if hasattr(self.other,'set_self_id'):
            self.other.set_self_id(id)
    def __call__(self,value):
        if not value: return (self.null,None)
        return self.other(value)
    def formatter(self,value):
        if hasattr(self.other,'formatter'):
            return self.other.formatter(value)
        return value

class CLEANUP(object):
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

class CRYPT(object):
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


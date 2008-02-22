"""
This file is part of web2py Web Framework (Copyrighted, 2007)
Developed by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: GPL v2
"""

import types, urllib, random, re, sys, os, shutil, cStringIO
from html import FORM,INPUT,TEXTAREA,SELECT,OPTION,TABLE,TR,TD,TH,A,B,DIV,LABEL
from validators import IS_IN_SET, IS_NOT_IN_DB, CRYPT
from sql import SQLStorage

class SQLFORM(FORM):
    """
    SQLFORM is used to map a table (and a current record) into an HTML form
   
    given a SQLTable stored in db.table

    SQLFORM(db.table) generates an insert form
    record=db(db.table.id==some_id).select()[0]
    SQLFORM(db.table,record) generates an update form
    SQLFORM(db.table,record,deletable=True) generates an update 
                                            with a delete button
    
    optional arguments:
    
    fields: a list of fields that should be placed in the form, default is all.
    labels: a dictionary with labels for each field. keys are field names.
    linkto: the URL of a controller/function to access referencedby records
            see controller appadmin.py for examples
    upload: the URL of a controller/function to download an uploaded file
            see controller appadmin.py for examples
    any named optional attribute is passed to the <form> tag
            for example _class, _id, _style, _action,_method, etc.

    """
    def __init__(self,table,record=None,deletable=False,linkto=None,upload=None,fields=None,labels=None,submit_button='Submit',showid=True,**attributes):
        """
        SQLFORM(db.table,
               record=None,
               fields=['name'],
               labels={'name':'Your name'},
               linkto=ULR(r=request,f='table/db/')
        """
        self.table=table
        FORM.__init__(self,*[],**attributes)            
        xfields=[]
        self.fields=fields
        if not self.fields: self.fields=self.table.fields        
        if not 'id' in self.fields: self.fields.insert(0,'id')
        self.record=record
        self.record_id=None
        for fieldname in self.fields:
            field_id='%s_%s' % (table._tablename,fieldname)
            if fieldname=='id':                
                if record: 
                    if showid:
                        xfields.append(TR(TD('Record id:'),TD(B(record['id']))))
                    self.record_id=str(record['id'])
                continue
            field=self.table[fieldname]            
            if record: default=record[fieldname]
            else: default=field.default
            if default: default=field.formatter(default)
            if labels!=None: 
                label=labels[fieldname]
            else: 
                label=fieldname.replace('_',' ').capitalize()+': '
            label=LABEL(label,_for=fieldname,_id='%s:label'%field_id)
            if field.type=='blob' or field.type=='text':
                inp=TEXTAREA(_type='text',_id=field_id,
                    _name=fieldname,value=default, requires=field.requires)
            elif field.type=='upload':
                inp=INPUT(_type='file',_id=field_id,
                          _name=fieldname, requires=field.requires)
                if upload and default:
                    inp=DIV(inp,'[',A('file',_href=upload+'/'+default),'|',
                        INPUT(_type='checkbox',_name=fieldname+'__delete'),'delete]')
            elif field.type=='boolean':
                if default==True: default='ON'
                else: default=''
                inp=INPUT(_type='checkbox',_id=field_id,
                    _name=fieldname,value=default, requires=field.requires)
            elif isinstance(field.requires,IS_IN_SET):
                 if field.requires.labels:
                    opts,k=[],0
                    for v in field.requires.theset:
                        opts.append(OPTION(field.requires.labels[k],_value=v))
                        k+=1
                 else: opts=field.requires.theset
                 inp=SELECT(*opts,**dict(_id=field_id,
                     _name=fieldname,value=default,requires=field.requires))
            elif field.type=='password':
                 if self.record: v='********'
                 else: v=''
                 inp=INPUT(_type='password', _id=field_id,
                      _name=fieldname,_value=v,
                      requires=field.requires)
            else:
                 if default==None: default=''
                 inp=INPUT(_type='text', _id=field_id,
                      _name=fieldname,value=str(default),
                      requires=field.requires)
            xfields.append(TR(TD(label),TD(inp)))
        if record and linkto:
            if linkto:
                for rtable,rfield in table._referenced_by:
                    query=urllib.quote(str(table._db[rtable][rfield]==record.id))
                    xfields.append(TR(' ',A('%s.%s' % (rtable,rfield),
                           _href='%s/%s?query=%s'%(linkto,rtable,query))))
        if record and deletable:
            label='Check to delete: '
            xfields.append(TR(label,INPUT(_type='checkbox',
                          _name='delete_this_record')))            
        xfields.append(TR(' ',INPUT(_type='submit',_value=submit_button)))
        if record:
            self.components=[TABLE(*xfields),
                        INPUT(_type='hidden',_name='id',_value=record['id'])]
        else: self.components=[TABLE(*xfields)]
    def accepts(self,vars,session=None,formname=None,keepvalues=False):
        """
        same as FORM.accepts but also does insert, update or delete in SQLDB
        """
        if not formname: formname=str(self.table)
        raw_vars=dict(vars.items())
        if vars.has_key('delete_this_record') and \
           vars['delete_this_record']=='on' and \
           vars.has_key('id'):
            if vars['id']!=self.record_id:
                raise SyntaxError, "user is tampering with form"
            self.table._db(self.table.id==int(vars['id'])).delete()
            return True
        else:
            ### THIS IS FOR UNIQUE RECORDS, read IS_NOT_IN_DB            
            for fieldname in self.fields:
                field=self.table[fieldname]
                if field.requires: 
                    try: field.requires=list(field.requires)
                    except TypeError: field.requires=[field.requires]
                for item in field.requires:                    
                    if isinstance(item,IS_NOT_IN_DB):
                        item.record_id=self.record_id
            ### END
            fields={}
            for key in self.vars.keys(): fields[key]=self.vars[key]            
            ret=FORM.accepts(self,vars,session,formname,keepvalues)
            if not ret: return ret
            vars=self.vars
            for fieldname in self.fields:
                #if not vars.has_key(fieldname): continue
                if fieldname=='id': continue
                field=self.table[fieldname]
                if field.type=='boolean':
                    if vars.has_key(fieldname) and vars[fieldname]=='on': 
                        fields[fieldname]=True
                    else: fields[fieldname]=False
                elif field.type=='password' and self.record and \
                    raw_vars.has_key(fieldname) and \
                    raw_vars[fieldname]=='********':
                    continue # do not update if password was not changed
                elif field.type=='upload':
                    f=vars[fieldname]
                    if type(f)!=types.StringType:
                        try: e=re.compile('\.\w+$').findall(f.filename.strip())[0]
                        except IndexError: e='.txt'
                        source_file=f.file
                    else: 
                        e='.txt' ### DO NOT KNOW WHY THIS HAPPENS!
                        source_file=cStringIO.StringIO(f)
                    if f!='':
                        newfilename='%s.%s.%s%s'%(self.table._tablename, \
                                    fieldname,str(random.random())[2:],e)
                        pathfilename=os.path.join(self.table._db._folder,\
                                    '../uploads/',newfilename)
                        dest_file=open(pathfilename,'wb')
                        shutil.copyfileobj(source_file,dest_file)
                        dest_file.close()
                        fields[fieldname]=newfilename
                    else:
                        fd=fieldname+'__delete'
                        if (vars.has_key(fd) and vars[fd]=='on') or not self.record:  
                            fields[fieldname]=''
                        else: 
                            fields[fieldname]=self.record[fieldname]
                        continue
                elif vars.has_key(fieldname): fields[fieldname]=vars[fieldname]
                elif field.default==None: return False                
                if field.type[:9] in ['integer', 'reference']:
                    fields[fieldname]=int(fields[fieldname])
                elif field.type=='double':
                    fields[fieldname]=float(fields[fieldname])
            if vars.has_key('id'):                
                if vars['id']!=self.record_id:
                    raise SyntaxError, "user is tampering with form"
                id=int(vars['id'])
                self.table._db(self.table.id==id).update(**fields)
            else: 
                self.vars.id=self.table.insert(**fields)                
        return ret   


class SQLTABLE(TABLE):
    """
    given a SQLRows object, as returned by a db().select(), generates
    and html table with the rows.

    optional arguments:
    linkto: URL to edit individual records
    uplaod: URL to download uploaded files
    optional names attributes for passed to the <table> tag
    """
    def __init__(self,sqlrows,linkto=None,upload=None,**attributes):
        TABLE.__init__(self,**attributes)
        self.components=[]
        self.attributes=attributes
        self.sqlrows=sqlrows        
        rows,row=self.components,[]
        for colname in sqlrows.colnames: row.append(TH('[%s]'%colname))
        rows.append(TR(*row))
        for record in sqlrows:
            row=[]
            for colname in sqlrows.colnames:
                tablename,fieldname=colname.split('.')
                field=sqlrows._db[tablename][fieldname]
                if record.has_key(tablename) and isinstance(record,SQLStorage):
                    r=record[tablename][fieldname]
                elif record.has_key(fieldname):
                    r=record[fieldname]
                else: raise SyntaxError, "something wrong in SQLRows object"
                r=str(field.formatter(r))
                if upload and field.type=='upload' and r!='None':
                    if r: row.append(TD(A('file',_href='%s/%s' % (upload,r))))
                    else: row.append(TD())
                    continue
                if len(r)>16: r=r[:13]+'...'                
                if linkto and field.type=='id':
                    row.append(TD(A(r,_href='%s/%s/%s' % \
                                    (linkto,tablename,r))))
                elif linkto and field.type[:9]=='reference':
                        row.append(TD(A(r,_href='%s/%s/%s' % \
                                       (linkto,field.type[10:],r))))
                else: row.append(TD(r))
            rows.append(TR(*row))

        

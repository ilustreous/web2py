"""
This file is part of web2py Web Framework (Copyrighted, 2007)
Developed by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: GPL v2
"""

import urllib, re, sys, os, uuid, shutil, cStringIO
from html import FORM,INPUT,TEXTAREA,SELECT,OPTION,TABLE,TR,TD,TH,A,B,DIV,LABEL,ON,TAG,THEAD,TBODY,B
from validators import IS_IN_SET, IS_NOT_IN_DB, CRYPT, IS_NULL_OR
from sql import SQLStorage, SQLDB

table_field=re.compile('[\w_]+\.[\w_]+')
re_extension=re.compile('\.\w+$')

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
    col3  : a dictionary with content for an optional third column (right of each field). keys are field names.
    linkto: the URL of a controller/function to access referencedby records
            see controller appadmin.py for examples
    upload: the URL of a controller/function to download an uploaded file
            see controller appadmin.py for examples
    any named optional attribute is passed to the <form> tag
            for example _class, _id, _style, _action,_method, etc.

    """
    # usability improvements proposal by fpp - 4 May 2008 :
    # - correct labels (for points to filed id, not field name)
    # - add label for delete checkbox
    # - add translatable label for record ID
    # - add third column to right of fields, populated from the col3 dict
    
    def __init__(self,table,record=None,deletable=False,
                 linkto=None,upload=None,fields=None,labels=None,col3={},
                 submit_button='Submit', delete_label='Check to delete:', 
                 id_label='Record id: ', showid=True,**attributes):
        """
        SQLFORM(db.table,
               record=None,
               fields=['name'],
               labels={'name':'Your name'},
               linkto=ULR(r=request,f='table/db/')
        """
        self.table=table
        self.trows={}
        FORM.__init__(self,*[],**attributes)            
        xfields=[]
        self.fields=fields
        if not self.fields: self.fields=self.table.fields        
        if not 'id' in self.fields: self.fields.insert(0,'id')
        self.record=record
        self.record_id=None
        for fieldname in self.fields:
            if fieldname.find('.')>=0: continue
            field_id='%s_%s' % (table._tablename,fieldname)
            if fieldname=='id':                
                if record: 
                    if showid:
                        xfields.append(TR(LABEL(id_label,_for='id',_id='id__label'),\
                                          B(record['id']),col3.get('id',''),\
                                          _id='id__row'))
                    self.record_id=str(record['id'])
                continue
            field=self.table[fieldname]
            if record: default=record[fieldname]
            else: default=field.default
            if default: default=field.formatter(default)
            if labels!=None and labels.has_key(fieldname):
                label=labels[fieldname]
            else:
                label=str(field.label)+': '
            label=LABEL(label,_for=field_id,_id='%s__label'%field_id)
            comment=col3.get(fieldname,'')
            row_id=field_id+'__row'
            if hasattr(field,'widget') and field.widget:
                inp=field.widget(field,default)
            elif field.type=='text':
                inp=TEXTAREA(_type='text',_id=field_id,_class=field.type,
                    _name=fieldname,value=default, requires=field.requires)
            elif field.type=='blob':
                continue
            elif field.type=='upload':
                inp=INPUT(_type='file',_id=field_id,_class=field.type,
                          _name=fieldname, requires=field.requires)
                if upload and default:
                    inp=DIV(inp,'[',A('file',_href=upload+'/'+default),'|',
                        INPUT(_type='checkbox',_name=fieldname+'__delete'),'delete]')
            elif field.type=='boolean':
                if default==True: default='ON'
                else: default=''
                inp=INPUT(_type='checkbox',_id=field_id,_class=field.type,
                    _name=fieldname,value=default, requires=field.requires)
            elif hasattr(field.requires,'options'):
                opts=[]
                for k,v in field.requires.options():
                    opts.append(OPTION(v,_value=k))
                inp=SELECT(*opts,**dict(_id=field_id,_class=field.type,
                     _name=fieldname,value=default,requires=field.requires))
            elif isinstance(field.requires,IS_NULL_OR) and \
                 hasattr(field.requires.other,'options'):
                opts=[OPTION(_value="")]
                for k,v in field.requires.other.options():
                    opts.append(OPTION(v,_value=k))
                inp=SELECT(*opts,**dict(_id=field_id,_class=field.type,
                     _name=fieldname,value=default,requires=field.requires))
            elif field.type=='password':
                if self.record: v='********'
                else: v=''
                inp=INPUT(_type='password', _id=field_id,
                      _name=fieldname,_value=v,_class=field.type,
                      requires=field.requires)
            else:
                if default==None: default=''
                inp=INPUT(_type='text', _id=field_id,_class=field.type,
                      _name=fieldname,value=str(default),
                      requires=field.requires)
            tr=self.trows[fieldname]=TR(label,inp,comment,_id=row_id)
            xfields.append(tr)
        if record and linkto:
            if linkto:
                for rtable,rfield in table._referenced_by:
                    query=urllib.quote(str(table._db[rtable][rfield]==record.id))
                    lname=olname='%s.%s' % (rtable,rfield)
                    if fields and not olname in fields: continue
                    if labels and labels.has_key(lname): lname=labels[lname]
                    xfields.append(TR('',A(lname,
                           _class='reference',
                           _href='%s/%s?query=%s'%(linkto,rtable,query)),
                           col3.get(olname,''),
                           _id='%s__row'%olname.replace('.','__')))
        if record and deletable:
            xfields.append(TR(LABEL(delete_label, _for='delete_record',_id='delete_record__label'),INPUT(_type='checkbox', _class='delete', _id='delete_record', _name='delete_this_record'),col3.get('delete_record',''),_id='delete_record__row'))            
        xfields.append(TR('',INPUT(_type='submit',_value=submit_button),col3.get('submit_button',''),_id='submit_record__row'))
        if record:
            self.components=[TABLE(*xfields),INPUT(_type='hidden',_name='id',_value=record['id'])]
        else: self.components=[TABLE(*xfields)]
    def accepts(self,vars,session=None,formname='%(tablename)s',keepvalues=False):
        """
        same as FORM.accepts but also does insert, update or delete in SQLDB
        """
        if formname: formname=formname % dict(tablename=self.table._tablename)
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
                requires=field.requires or []
                if not isinstance(requires,(list,tuple)): requires=[requires]
                [item.set_self_id(self.record_id) for item in requires \
                 if hasattr(item,'set_self_id')]
            ### END
            fields={}
            for key in self.vars.keys(): fields[key]=self.vars[key]            
            ret=FORM.accepts(self,vars,session,formname,keepvalues)
            if not ret:
                for fieldname in self.fields:
                    field=self.table[fieldname]
                    if field.widget and vars.has_key(fieldname):
                         self.trows[fieldname][1][0]=field.widget(field,vars[fieldname])           
                return ret
            vars=self.vars
            for fieldname in self.fields:
                if fieldname=='id': continue
                if not self.table.has_key(fieldname): continue
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
                    if not isinstance(f,(str,unicode)):
                        try: e=re_extension.findall(f.filename.strip())[0]
                        except IndexError: e='.txt'
                        source_file=f.file
                    else: 
                        e='.txt' ### DO NOT KNOW WHY THIS HAPPENS!
                        source_file=cStringIO.StringIO(f)
                    if f!='':
                        newfilename='%s.%s.%s%s'%(self.table._tablename,fieldname,uuid.uuid4(),e)
                        vars['%s_newfilename'%fieldname]=newfilename
                        fields[fieldname]=newfilename
                        if field.uploadfield==True:
                            pathfilename=os.path.join(self.table._db._folder,'../uploads/',newfilename)
                            dest_file=open(pathfilename,'wb')
                            shutil.copyfileobj(source_file,dest_file)
                            dest_file.close()
                        elif field.uploadfield:
                            fields[field.uploadfield]=source_file.read()
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
                    if fields[fieldname]!=None:
                        fields[fieldname]=int(fields[fieldname])
                elif field.type=='double':
                    if fields[fieldname]!=None:
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
    orderby: Add an orderby link to column headers.
    headers: dictionary of headers to headers redefinions
    truncate: length at which to truncate text in table cells.
              Defaults to 16 characters.
    optional names attributes for passed to the <table> tag
    """
    def __init__(self,sqlrows,linkto=None,upload=None,orderby=None,headers={},truncate=16,**attributes):
        TABLE.__init__(self,**attributes)
        self.components=[]
        self.attributes=attributes
        self.sqlrows=sqlrows        
        components,row=self.components,[]
        if not orderby:
           for c in sqlrows.colnames: row.append(TH(headers.get(c,c)))
        else:
           for c in sqlrows.colnames: row.append(TH(A(headers.get(c,c),_href='?orderby='+c)))
        components.append(THEAD(TR(*row)))
        tbody=[]
        for rc,record in enumerate(sqlrows):
            row=[]
            if rc%2==0: _class='even'
            else: _class='odd'
            for colname in sqlrows.colnames:
                if not table_field.match(colname):
                    r=record._extra[colname]
                    row.append(TD(r))
                    continue
                tablename,fieldname=colname.split('.')
                field=sqlrows._db[tablename][fieldname]
                if record.has_key(tablename) and isinstance(record,SQLStorage)\
                   and isinstance(record[tablename],SQLStorage):
                    r=record[tablename][fieldname]
                elif record.has_key(fieldname):
                    r=record[fieldname]
                else: raise SyntaxError, "something wrong in SQLRows object"
                r=str(field.formatter(r))
                if upload and field.type=='upload' and r!='None':
                    if r: row.append(TD(A('file',_href='%s/%s' % (upload,r))))
                    else: row.append(TD())
                    continue
                ur=unicode(r,'utf8')
                if len(ur)>truncate: r=ur[:truncate-3].encode('utf8') + '...' 
                if linkto and field.type=='id':
                    row.append(TD(A(r,_href='%s/%s/%s' % \
                                    (linkto,tablename,r))))
                elif linkto and field.type[:9]=='reference':
                        row.append(TD(A(r,_href='%s/%s/%s' % \
                                       (linkto,field.type[10:],r))))
                else: row.append(TD(r))
            tbody.append(TR(_class=_class,*row))
        components.append(TBODY(*tbody))
        
def form_factory(*fields,**attributes):    
    return SQLFORM(SQLDB(None).define_table('no_table',*fields),**attributes)

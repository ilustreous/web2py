import re, os
from yapo import Yapo

def parse_field(f):
    re.compile('(\w*)')
    fields=['string','integer','text','double','boolean','upload',
            'date','datetime','time']
    class A(): pass
    a=A()
    f2,a.field_type,a.unique,a.notnull,a.private=[],'string',False,False,False
    for x in f.split(): 
        if x in fields: a.field_type=x
        elif x=='unique': a.unique=True
        elif x=='notnull': a.notnull=True
        elif x=='private': a.private=True
        else: f2.append(x) 
    a.name='_'.join(f2)
    a.label=a.name.replace('_',' ').capitalize()
    return a
            
def build_model(yapo,path='./',dbname='db'):
    #for dbfile,db in yapo.models.items():
    if 1:
        db=yapo.models
        text="import datetime\n"
        text+="now_date=datetime.date.today()\n"
        text+="now_datetime=datetime.datetime.today()\n"
        text+="now_time=now_datetime.strftime('%H:%M:%S')\n\n"
        text+="db=SQLDB('%s')\n\n" % yapo.uri
        for t in db.keys():
            exposed=[]
            labels=[]
            text+="db.define_table('table_%s',\n" % (t)
            for f in db[t].values():
                f=parse_field(f)
                if f.name in yapo.model.keys(): f.field_type='reference '+f.name
                s="    SQLField('field_%s','%s'" % (f.name,f.field_type)
                if f.field_type=='string':
                    s+=',length=128'
                elif f.field_type[:9]=='reference':            
                    s+=",\n         requires=IS_IN_DB(db,'table_%s.id','%%(%s)s')"% (f.name,parse_field(yapo.model[f.name][0]).name)
                elif f.unique:
                    s+=",\n         requires=IS_NOT_IN_DB(db,'table_%s.field_%s')"%(f.name,f.name)
                if f.field_type=='date':
                    s+=",default=now_date"
                elif f.field_type=='datetime':
                    s+=",default=now_datetime"
                elif f.field_type=='time':
                    s+=",default=now_time"
                elif f.field_type=='integer':
                    s+=",default=0"
                elif f.field_type=='double':
                    s+=",default=0.0"
                s+='),\n'
                if not f.private: exposed.append('field_'+f.name)
                labels.append("'field_%s:T('%s')" % (f.name,f.label))
                text+=s
            text+="    migrate='%s.table')\n\n" % t
            text+="db.table_%s.exposed=%s\n" % (t,repr(exposed))
            text+="db.table_%s.labels=[%s]\n\n" % (t,', '.join(labels))
        if not os.path.exists(os.path.join(path,'models')):
            os.mkdir(os.path.join(path,'models'))
        open(os.path.join(path,'models',dbname+'.py'),'w').write(text)

CRUD_LIST="""
def list_%(name)s():
   a=request.vars.start or 0
   b=request.vars.stop or a+25
   orderby=request.vars.oderby or db.table_%(name)s.fields[0] ### UNSAFE FIX
   items=db(db.table_%(name)s.id>0).select(orderby=orderby,limitby=(a,b+1))
   return dict(items=items)
"""

CRUD_LIST_VIEW="""{{extend 'layout.html'}}
<h1>Table %(name)s</h1>
[{{=A('create new %(name)s',_href=URL(r=request,f='create_%(name)s'))}}]
{{if not len(items):}}
<h2>No %(name)s in database yet</h2>
{{else:}}
<h2>%(name)ss in database</h2>
<table>
   <tr>
     <td><b>id</b></td>
     {{for field in db.table_%(name)s.exposed:}}
          <td><b>{{=db.table_%(name)s.labels[field]}}</b></td>
     {{pass}}
     <td></td>
   </tr>
{{for item in items:}}
   <tr>
     <td>[{{=item.id}}]</td>
     {{for field in db.table_%(name)s.exposed:}}
          <td>{{=item[field]}}</td>
     {{pass}}
     <td>[{{=A('read',_href=URL(r=request,f='read_%(name)s',args=[item.id]))}}]
[{{=A('edit',_href=URL(r=request,f='edit_%(name)s',args=[item.id]))}}]
[{{=A('delete',_href=URL(r=request,f='delete_%(name)s',args=[item.id]))}}]</td>
   </tr>
{{pass}}
</table>
{{pass}}
"""

CRUD_CREATE="""
def create_%(name)s():
   form=SQLFORM(db.table_%(name)s,
                fields=db.table_%(name)s.exposed,
                lables=db.table_%(name)s.labels,
                upload=URL(r=request,f='download'))
   if form.accepts(request.vars,session):
       session.flash=T("new record inserted")
       redirect(URL(r=request,f='list_%(name)s'))
   return dict(form=form)
"""

CRUD_CREATE_VIEW="""{{extend 'layout.html'}}
<h1>Create new %(name)s</h1>
{{=form}}
"""

CRUD_READ="""
def read_%(name)s():
   if not len(request.args): raise HTTP(400)
   rows=db(db.table_%(name)s.id==request.args[0]).select()
   if not len(rows):
        session.flash=T('record not found')
        redirect(URL(r=request,f='list_%(name)s'))
   return dict(item=rows[0])
"""

CRUD_READ_VIEW="""{{extend 'layout.html'}}
<h1>Read %(name)s</h1>
<table>
{{for field in db.table_%(name)s.exposed:}}
  <tr>
  <td>{{=db.table_%(name)s.labels[field]}}:</td>
  <td><b>{{=item[field]}}</b></td>
  </tr>
{{pass}}
</table>
"""

CRUD_EDIT="""
def edit_%(name)s():
   if not len(request.args): raise HTTP(400)
   rows=db(db.table_%(name)s.id==request.args[0]).select()
   if not len(rows):
        session.flash=T('record not found')
        redirect(URL(r=request,f='list_%(name)s'))
   form=SQLFORM(db.table_%(name)s,rows[0],
                fields=db.table_%(name)s.exposed,
                lables=db.table_%(name)s.labels,
                upload=URL(r=request,f='download'),
                showid=False,deletable=True)
   if form.accepts(request.vars,session):
       session.flash=T("new record updated")
       redirect(URL(r=request,f='list_%(name)s'))
   return dict(form=form)
"""

CRUD_EDIT_VIEW="""{{extend 'layout.html'}}
<h1>Update %(name)s</h1>
{{=form}}
"""


CRUD_DELETE="""
def delete_%(name)s():
   if not len(request.args): raise HTTP(400)
   rows=db(db.table_%(name)s.id==request.args[0]).select()
   if not len(rows):
        session.flash=T('record not found')
        redirect(URL(r=request,f='list_%(name)s'))
   if request.vars.confirm=='yes':
        db(db.table_%(name)s.id==request.args[0]).delete()
        session.flash=T('record deleted')
        redirect(URL(r=request,f='list_%(name)s'))
   elif request.vars.confirm=='no':
        redirect(URL(r=request,f='list_%(name)s'))
   return dict(item=rows[0])
"""

CRUD_DELETE_VIEW="""{{extend 'layout.html'}}
<h1>Delete %(name)s</h1>
are you sure you want to delete this record?
{{=A('yes',_href=URL(r=request,args=request.args,vars=dict(confirm='yes')))}} or
{{=A('no',_href=URL(r=request,args=request.args,vars=dict(confirm='no')))}}
"""


def build_crud(yapo,path='./'):
    app_name=yapo.name
    controller='import os\n\n'
    controller+="response.title='''%s'''\n" % yapo.name or 'My Applicaiton'
    controller+="response.author='''%s'''\n" % yapo.author or ''
    controller+="response.slogan='''%s'''\n" % yapo.slogan or ''
    controller+="response.keywords='''%s'''\n" % yapo.keywords or ''
    controller+="response.description='''%s'''\n" % yapo.description or ''
    controller+="response.menu=[%s]\n" % ''.join(["['%s',False,URL(r=request,f='list_%s')],"%(k,k) for k in yapo.model.keys()]) 
    controller+="def download(): response.stream(os.path.join(request.folder,'uploads',request.args[0]))\n\n"
    if not os.path.exists(os.path.join(path,'views')):
         os.mkdir(os.path.join(path,'views'))
    if not os.path.exists(os.path.join(path,'views','crud')):
         os.mkdir(os.path.join(path,'views','crud'))
    for t in yapo.model.keys():
             controller+=CRUD_LIST % dict(name=t)
             open(os.path.join(path,'views','crud','list_%s.html'%t),'w')\
                 .write(CRUD_LIST_VIEW % dict(name=t))         
             controller+=CRUD_CREATE % dict(name=t)
             open(os.path.join(path,'views','crud','create_%s.html'%t),'w')\
                 .write(CRUD_CREATE_VIEW % dict(name=t))         
             controller+=CRUD_READ % dict(name=t)
             open(os.path.join(path,'views','crud','read_%s.html'%t),'w')\
                 .write(CRUD_READ_VIEW % dict(name=t))         
             controller+=CRUD_EDIT % dict(name=t)
             open(os.path.join(path,'views','crud','edit_%s.html'%t),'w')\
                 .write(CRUD_EDIT_VIEW % dict(name=t))         
             controller+=CRUD_DELETE % dict(name=t)
             open(os.path.join(path,'views','crud','delete_%s.html'%t),'w')\
                 .write(CRUD_DELETE_VIEW % dict(name=t))         
    open(os.path.join(path,'crud.py'),'w').write(controller)

TEST="""
uri:    sqlite://test.db
name:   test
author: Massimo Di Pierro
tables:
    client:
        name unique
        email
    product:
        name unique
        description text
        image upload

menu:
    welcome
    products:
        software
        consulting
        service
    about us:
        today
        history
    contact us       
"""

def build_app(text,path='./'):
    """
    >> build_app(TEST)
    """
    yapo=Yapo(text)
    build_model(Yapo(TEST))
    build_crud(Yapo(TEST))

if __name__=='__main__':
    import doctest
    doctest.testmod()


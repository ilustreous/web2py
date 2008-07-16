import re, os, sys
from yapo import Yapo

def parse_field(f):
    re.compile('(\w*)')
    fields=['string','integer','text','double','boolean','upload',
            'date','datetime','time']
    class A(): pass
    a=A()
    f2,a.field_type,a.unique,a.notnull,a.private,a.nocolumn=[],'string',False,False,False,False
    for x in f.split(): 
        if x in fields: a.field_type=x
        elif x=='unique': a.unique=True
        elif x=='notnull': a.notnull=True
        elif x=='private': a.private=True
        elif x=='nocolumn': a.nocolumn=True
        else: f2.append(x) 
    a.name='_'.join(f2)
    a.label=a.name.replace('_',' ').capitalize()
    return a

CRUD="""

def render(view,**a):
   import cStringIO
   obody,oview=response.body,response.view
   response.body,response.view=cStringIO.StringIO(),view
   page=response.render(**a)
   response.body,response.view=obody,oview
   return page

def list(table):
   a=request.vars.start or 0
   b=request.vars.stop or a+25
   orderby=request.vars.oderby or db.table_person.fields[0] ### UNSAFE FIX
   items=db(db[table].id>0).select(orderby=orderby,limitby=(a,b+1))
   return render('crud/list_%s.html'%table,items=items)

def create(table,target=None):
   form=SQLFORM(db[table],
                fields=db[table].exposed,
                lables=db[table].labels,
                upload=URL(r=request,f='download'))
   if form.accepts(request.vars,session):
       session.flash=T("new record inserted")
       if target: redirect(target)
       else: redirect(URL(r=request,f='list_'+table))
   return render('crud/create_%s.html'%table,form=form)

def read(table,id,target=None):
   rows=db(db[table].id==id).select()
   if not len(rows):
       session.flash=T('record not found')
       if target: redirect(target)
       else: redirect(URL(r=request,f='list_'+table))
   return render('crud/read_%s.html'%table,item=rows[0])

def edit(table,id,target=None):
   rows=db(db[table].id==id).select()
   if not len(rows):
       session.flash=T('record not found')
       if target: redirect(target)
       else: redirect(URL(r=request,f='list_'+table))
   form=SQLFORM(db[table],rows[0],
                fields=db[table].exposed,
                lables=db[table].labels,
                upload=URL(r=request,f='download'),
                showid=False,deletable=True)
   if form.accepts(request.vars,session):
       session.flash=T("new record updated")
       if target: redirect(target)
       else: redirect(URL(r=request,f='list_'+table))
   return render('crud/edit_%s.html'%table,form=form)

def delete(table,id,target=None):
   rows=db(db[table].id==id).select()
   if not len(rows):
       session.flash=T('record not found')
       if target: redirect(target)
       else: redirect(URL(r=request,f='list_'+table))
   if request.vars.confirm=='yes':
       db(db[table].id==request.args[0]).delete()
       session.flash=T('record deleted')
       if target: redirect(target)
       else: redirect(URL(r=request,f='list_'+table))
   elif request.vars.confirm=='no':
       if target: redirect(target)
       else: redirect(URL(r=request,f='list_'+table))
   return render('crud/delete_%s.html'%table,item=rows[0])
"""


def build_model(yapo,path='./',dbname='db'):
    path2=os.path.join(path,'models','db_crud.py')
    open(path2,'w').write(CRUD)
    if 1:
        db=yapo.model
        text="import datetime\n"
        text+="now_date=datetime.date.today()\n"
        text+="now_datetime=datetime.datetime.today()\n"
        text+="now_time=now_datetime.strftime('%H:%M:%S')\n\n"
        text+="db=SQLDB('%s')\n\n" % yapo.uri
        for t in db.keys():
            exposed=[]
            labels=[]
            columns=[]
            text+="db.define_table('table_%s',\n" % (t)
            for f in db[t].values():
                f=parse_field(f)
                if f.name in yapo.model.keys(): f.field_type='reference table_'+f.name
                s="    SQLField('field_%s','%s'" % (f.name,f.field_type)
                if f.field_type=='string':
                    s+=',length=128'
                if f.field_type[:9]=='reference':            
                    s+=",\n         requires=IS_IN_DB(db,'table_%s.id','%%(field_%s)s')"% (f.name,parse_field(yapo.model[f.name][0]).name)
                elif f.unique:
                    s+=",\n         requires=[IS_NOT_EMPTY(T('cannot be empty')),IS_NOT_IN_DB(db,'table_%s.field_%s')]"%(f.name,f.name)
                elif f.notnull and f.field_type in ['text','string','integer','double']:
                    s+=',\n      requires=IS_NOT_EMPTY(T("cannot be empty"))' 
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
                labels.append("'field_%s':T('%s')" % (f.name,f.label))
                if not f.nocolumn: columns.append('field_'+f.name)
                text+=s
            text+="    migrate='%s.table')\n\n" % t
            text+="db.table_%s.exposed=%s\n" % (t,repr(exposed))
            text+="db.table_%s.columns=%s\n" % (t,repr(columns))
            text+="db.table_%s.labels={%s}\n\n" % (t,', '.join(labels))
        if not os.path.exists(os.path.join(path,'models')):
            os.mkdir(os.path.join(path,'models'))
        open(os.path.join(path,'models',dbname+'.py'),'w').write(text)

MAIN_LIST_VIEW="""{{extend 'layout.html'}}{{=XML(list('table_%(name)s'))}}"""

CRUD_LIST_VIEW="""
<h1>Table %(name)s</h1>
[{{=A('create new %(name)s',_href=URL(r=request,f='create_table_%(name)s'))}}]
[[[ add pagination ]]]
{{if not len(items):}}
<h2>No %(name)s in database yet</h2>
{{else:}}
<h2>%(name)ss in database</h2>
<table>
   <tr>
     <td></td><td><b>id</b></td>
     {{for field in db.table_%(name)s.columns:}}
          <td><b>{{=db.table_%(name)s.labels[field]}}</b></td>
     {{pass}}
     <td></td>
   </tr>
{{for i,item in enumerate(items):}}
   {{if i==25: break}}
   <tr>
     <td><input type="checkbox" name="{{='table_%(name)s_record_'+str(item.id)}}" />
     <td>[{{=item.id}}]</td>
     {{for field in db.table_%(name)s.columns:}}
          <td>{{=item[field]}}</td>
     {{pass}}
     <td>[{{=A('read',_href=URL(r=request,f='read_table_%(name)s',args=[item.id]))}}]
[{{=A('edit',_href=URL(r=request,f='edit_table_%(name)s',args=[item.id]))}}]
[{{=A('delete',_href=URL(r=request,f='delete_table_%(name)s',args=[item.id]))}}]</td>
   </tr>
{{pass}}
</table>
{{pass}}
"""

MAIN_CREATE_VIEW="""{{extend 'layout.html'}}{{=XML(create('table_%(name)s'))}}"""

CRUD_CREATE_VIEW="""
<h1>Create new %(name)s</h1>
{{=form}}
"""

MAIN_READ_VIEW="""{{extend 'layout.html'}}{{=XML(read('table_%(name)s',request.args[0]))}}"""

CRUD_READ_VIEW="""
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

MAIN_EDIT_VIEW="""{{extend 'layout.html'}}{{=XML(edit('table_%(name)s',request.args[0]))}}"""

CRUD_EDIT_VIEW="""<h1>Update %(name)s</h1>{{=form}}"""

MAIN_DELETE_VIEW="""{{extend 'layout.html'}}{{=XML(delete('table_%(name)s',request.args[0]))}}"""

CRUD_DELETE_VIEW="""
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
    controller+="response.menu=[%s]\n" % ''.join(["['%s',False,URL(r=request,f='list_table_%s')],"%(k,k) for k in yapo.model.keys()]) 
    controller+="def download(): response.stream(os.path.join(request.folder,'uploads',request.args[0]))\n\n"
    if not os.path.exists(os.path.join(path,'views','main')):
         os.mkdir(os.path.join(path,'views','main'))
    if not os.path.exists(os.path.join(path,'views','crud')):
         os.mkdir(os.path.join(path,'views','crud'))
    for t in yapo.model.keys():
             controller+='def list_table_%(name)s(): return dict()\n' % dict(name=t)
             open(os.path.join(path,'views','crud','list_table_%s.html'%t),'w')\
                 .write(CRUD_LIST_VIEW % dict(name=t))
             open(os.path.join(path,'views','main','list_table_%s.html'%t),'w')\
                 .write(MAIN_LIST_VIEW % dict(name=t))         
             controller+='def create_table_%(name)s(): return dict()\n' % dict(name=t)
             open(os.path.join(path,'views','crud','create_table_%s.html'%t),'w')\
                 .write(CRUD_CREATE_VIEW % dict(name=t))         
             open(os.path.join(path,'views','main','create_table_%s.html'%t),'w')\
                 .write(MAIN_CREATE_VIEW % dict(name=t))         
             controller+='def read_table_%(name)s(): return dict()\n' % dict(name=t)
             open(os.path.join(path,'views','crud','read_table_%s.html'%t),'w')\
                 .write(CRUD_READ_VIEW % dict(name=t))         
             open(os.path.join(path,'views','main','read_table_%s.html'%t),'w')\
                 .write(MAIN_READ_VIEW % dict(name=t))         
             controller+='def edit_table_%(name)s(): return dict()\n' % dict(name=t)
             open(os.path.join(path,'views','crud','edit_table_%s.html'%t),'w')\
                 .write(CRUD_EDIT_VIEW % dict(name=t))         
             open(os.path.join(path,'views','main','edit_table_%s.html'%t),'w')\
                 .write(MAIN_EDIT_VIEW % dict(name=t))         
             controller+='def delete_table_%(name)s(): return dict()\n' % dict(name=t)
             open(os.path.join(path,'views','crud','delete_table_%s.html'%t),'w')\
                 .write(CRUD_DELETE_VIEW % dict(name=t))         
             open(os.path.join(path,'views','main','delete_table_%s.html'%t),\
                 'w').write(MAIN_DELETE_VIEW % dict(name=t))         
    open(os.path.join(path,'controllers','main.py'),'w').write(controller)

TEST="""
uri:    sqlite://test.db
name:   test
author: Massimo Di Pierro
model:
    client:
        name unique
        email
    product:
        name unique
        description text
        image upload
pages:
    welcome:
        content: Test me
    products:
        content: Test me
    about us:
        content: Test me
    contact us:
        content: Test me
"""

def build_main(yapo,path='./'):
    ### FIX THIS!
    controller='\n'
    for key,value in yapo.pages.items():
        controller+='def %s(): return dict()\n' % key
        if isinstance(value,str): html=value
        else: html=''
        open(os.path.join(path,'views','main','%s.html' % key),'w').write(html)
    open(os.path.join(path,'controllers','main.py'),'a').write(controller)
        

def build_app(name):
    """
    >> build_app(TEST)
    """    
    path=os.path.join('applications',name)
    yapo=Yapo(open(os.path.join(path,'app.yapo'),'r').read())
    build_model(yapo,path)
    build_crud(yapo,path)
    build_main(yapo,path)

if __name__=='__main__':
    name=sys.argv[1]
    build_app(name)


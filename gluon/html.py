"""
This file is part of web2py Web Framework (Copyrighted, 2007)
Developed by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: GPL v2
"""

import cgi, re, random, copy, sys, types, urllib, tokenize, keyword, base64, uuid
from storage import Storage
from validators import *
from highlight import highlight
import sanitizer

__all__=['A', 'B', 'BEAUTIFY', 'BODY', 'BR', 'CENTER', 'CODE', 'DIV', 'EM', 'EMBED', 'FIELDSET', 'FORM', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'HEAD', 'HR', 'HTML', 'IFRAME', 'IMG', 'INPUT', 'LABEL', 'LI', 'LINK', 'OL', 'UL', 'META', 'OBJECT', 'ON', 'OPTION', 'P', 'PRE', 'SCRIPT', 'SELECT', 'SPAN', 'STYLE', 'TABLE', 'TAG', 'TD', 'TEXTAREA', 'TH', 'THEAD', 'TBODY', 'TFOOT', 'TITLE', 'TR', 'TT', 'URL', 'XML', 'xmlescape', 'embed64']

def xmlescape(data,quote=False):
    try: 
        return data.xml()         
    except AttributeError: pass
    except TypeError: pass
    if not isinstance(data,(str,unicode)): data=str(data) 
    elif isinstance(data,unicode): data=data.encode("utf8","xmlcharrefreplace")
    data=cgi.escape(data,quote)
    return data

def URL(a=None,c=None,f=None,r=None,args=[],vars={}):
    """
    example:

    >>> URL(a='a',c='c',f='f',args=['x','y','z'],vars={'p':1, 'q':2})
    '/a/c/f/x/y/z?q=2&p=1'

    generates a url "/a/c/f" corresponding to application a, controller c 
    and function f. If r=request is passed, a,c,f are set, respectively,
    to r.applicaiton, r.controller, r.function. 

    The more typical usage is:
    
    URL(r=request,f='index') that generates a url for the index function 
    within the present application and controller.
    """
    application=controller=function=None
    if r:
        application=r.application
        controller=r.controller
        function=r.function
    if a: application=a    
    if c: controller=c
    if f:
         if isinstance(f,str): function=f
         else: function=f.__name__
    if not (application and controller and function):
        raise SyntaxError, 'not enough information to build the url'
    other=''
    if args: other='/'+'/'.join([str(x) for x in args])
    if vars: other=other+'?'+urllib.urlencode(vars)
    url='/%s/%s/%s%s' % (application, controller, function, other)
    return url

ON=True

class XML(object):
    """
    example:
   
    >>> XML('<h1>Hello</h1>').xml()
    '<h1>Hello</h1>'

    use it to wrap a string that contains XML/HTML so that it will not be 
    escaped by the template
    """
    def __init__(self,text,sanitize=False,permitted_tags=['a','b','blockquote','br/','i', 'li', 'ol','ul', 'p', 'cite','code','pre','img/'],allowed_attributes={'a':['href','title'],'img':['src','alt'],'blockquote':['type']}):        
        if sanitize: text=sanitizer.sanitize(text,permitted_tags,allowed_attributes)
        if isinstance(text,unicode):
            text=text.encode("utf8","xmlcharrefreplace")
        elif not isinstance(text,str):
            text=str(text)
        self.text=text
    def xml(self):
        return self.text
    def __str__(self):
        return self.xml()

class DIV(object):
    """
    example:
    
    >>> DIV('hello','world',_style='color:red;').xml() 
    '<div style="color:red;">helloworld</div>'

    all other HTML helpers are derived from DIV.
    _something="value" attributes are transparently translated into
    something="value" HTML attributes
    """
    tag='div'
    def __init__(self,*components,**attributes):
        if self.tag[-1:]=='/' and components:
            raise SyntaxError, '<%s> tags cannot have components' % self.tag
        if len(components)==1 and isinstance(components[0],(list,tuple)):
            self.components=list(components[0])
        else:
            self.components=list(components)
        self.attributes=attributes
        self.fixup()
        self.postprocessing()  ### converts special attributes in components attributes
    def append(self,value):
        return self.components.append(value)
    def insert(self,i,value):
        return self.components.insert(i,value)
    def __getitem__(self,i):
        if isinstance(i,str):
            try: return self.attributes[i]
            except KeyError: return None
        else: return self.components[i]
    def __setitem__(self,i,value):
        if isinstance(i,str): self.attributes[i]=value
        else: self.components[i]=value
    def __delitem__(self,i):
        if isinstance(i,str): del self.attributes[i]
        else: del self.components[i]
    def __len__(self):
        return len(self.components)
    def fixup(self):
        return
    def postprocessing(self):
        return
    def traverse(self,status):
        # if this tag is a form and we are in accepting mode (status=True) check formname and formkey
        if status and self.tag=='form':
            if self.session and self.session.get('_formkey[%s]'%self.formname,None)!=self.request_vars._formkey: status=False
            if self.formname!=self.request_vars._formname: status=False
        # if we are still in accepting mode 
        newstatus=status
        for c in self.components:
            if hasattr(c,'traverse'): 
                c.vars=self.vars
                c.request_vars=self.request_vars
                c.errors=self.errors
                c.values=self.values
                c.session=self.session
                c.formname=self.formname
                newstatus=c.traverse(status) and newstatus
        # for input, textarea, select, option, deal with 'value' and 'validation'
        if newstatus:
            newstatus=self.validate()
            self.postprocessing()
        return newstatus
    def validate(self): return True
    def _xml(self):
        items=self.attributes.items()
        fa=''
        for key,value in items:
             if key[:1]!='_': continue
             name=key[1:].lower()
             if value is True: value=name
             elif value is False or value is None: continue 
             fa+=' %s="%s"'%(name,xmlescape(value,True))
        co=''.join([xmlescape(component) for component in self.components])
        return fa,co
    def xml(self):
        fa,co=self._xml()
        if not self.tag: return co
        if self.tag[-1:]=='/': return '<%s%s />' % (self.tag[:-1],fa)
        return '<%s%s>%s</%s>' % (self.tag,fa,co,self.tag)
    def __str__(self):
        return self.xml()

class __TAG__(object):
    """
    TAG factory example:
    >>> print TAG.first(TAG.second('test'),_key=3)
    <first key="3"><second>test</second></first>
    """
    def __getitem__(self,name):
        return self.__getattr__(name)
    def __getattr__(self,name):
        if name[-1:]=='_': name=name[:-1]+'/'
        class __tag__(DIV): tag=name
        return lambda *a,**b: __tag__(*a,**b)
TAG=__TAG__()

class HTML(DIV):
    tag='html'
    def xml(self):
        fa,co=self._xml()
        return '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">\n<%s%s>%s</%s>' % (self.tag,fa,co,self.tag)

class HEAD(DIV): tag='head'

class TITLE(DIV): tag='title'

class META(DIV): tag='meta/'

class LINK(DIV): tag='link/'

class SCRIPT(DIV):
    """
    """
    tag='script'
    def xml(self):
        fa,co=self._xml()
        if co: return '<%s%s><!--\n%s\n//--></%s>' % (self.tag,fa,co,self.tag)
        else: return DIV.xml(self)

class STYLE(SCRIPT):
    """
    """
    tag='style'

class IMG(DIV): tag='img/'

class SPAN(DIV): tag='span'

class BODY(DIV): tag='body'

class H1(DIV): tag='h1'

class H2(DIV): tag='h2'

class H3(DIV): tag='h3'

class H4(DIV): tag='h4'

class H5(DIV): tag='h5'

class H6(DIV): tag='h6'

class P(DIV):
    tag='p'
    def xml(self):
        text=DIV.xml(self)
        if self['cr2br']:
             text=text.replace('\n','<br />')
        return text

class B(DIV): tag='b'

class BR(DIV): tag='br/'

class HR(DIV): tag='hr/'

class A(DIV): tag='a'

class EM(DIV): tag='em'

class EMBED(DIV): tag='embed/'

class TT(DIV): tag='tt'

class PRE(DIV): tag='pre'

class CENTER(DIV): tag='center'

class CODE(DIV):
    """
    displays code in HTML with syntax highlighting. Exmaple:
   
    {{=CODE("print 'hello world'",language='python',link=None,counter=1,styles={})}}
    
    supported languages are "python", "html_plain", "c", "cpp", "web2py", "html". 
    The "html" language interprets {{ and }} tags as "web2py" code, "html_plain" doesn't.
    
    if a link='/exmaples/global/vars/' is provided web2py keywords are linked to the online docs.
    the counter is used for line numbering, counter can be None or a prompt string.
    """
    def xml(self):
        language=self['language'] or 'PYTHON'
        link=self['link']
        counter=self['counter'] or 1
        styles=self['styles'] or {}
        return highlight(''.join(self.components),language=language,link=link,counter=counter,styles=styles,attributes=self.attributes)

class LABEL(DIV): tag='label'

class LI(DIV): tag='li'

class UL(DIV): 
    tag='ul'
    def fixup(self):        
        components=[]
        for c in self.components:
            if isinstance(c,LI):
                components.append(c)
            else:
                components.append(LI(c))
        self.components=components

class OL(UL):  tag='ol'

class TD(DIV): tag='td'

class TH(DIV): tag='th'

class TR(DIV):
    tag='tr'
    def fixup(self):
        components=[]
        for c in self.components:
            if isinstance(c, (TD, TH)):
                components.append(c)
            else:
                components.append(TD(c))
        self.components=components

class THEAD(DIV): tag='thead'

class TBODY(DIV): tag='tbody'

class TFOOT(DIV): tag='tfoot'

class TABLE(DIV): 
    tag='table'
    def fixup(self):
        components=[]
        for c in self.components:
            if isinstance(c,(TR,TBODY,THEAD,TFOOT)):
                components.append(c)
            else:
                components.append(TR(*c))
        self.components=components

class IFRAME(DIV): tag='iframe'

class INPUT(DIV):
    """ 
        examples:

        >>> INPUT(_type='text',_name='name',value='Max').xml()
        '<input value="Max" type="text" name="name" />'
        >>> INPUT(_type='checkbox',_name='checkbox',value='on').xml()
        '<input type="checkbox" checked="checked" name="checkbox" />'
        >>> INPUT(_type='radio',_name='radio',_value='yes',value='yes').xml()
        '<input value="yes" type="radio" checked="checked" name="radio" />'
        >>> INPUT(_type='radio',_name='radio',_value='no',value='yes').xml()
        '<input value="no" type="radio" name="radio" />'

        the input helper takes two special attributes value= and requires=.

        value is used to pass the initial value for the input field.
        value differs from _value because it works for checkboxes, radio,
        textarea and select/option too. 
        for a checkbox value should be '' or 'on'.
        for a radio or select/option value should be the _value 
        of the checked/selected item.

        requres should be None, or a validator or a list of validators for the
        value of the field.        
        """
    tag='input/'
    def validate(self):
        ## this only changes value, not _value
        name=self['_name']
        if not name: return True
        value=self.request_vars.get(name,self['value'] or '')
        if not isinstance(value,cgi.FieldStorage): value=str(value)
        self.values[name]=self['value']=value
        requires=self['requires']
        if requires: 
            if not isinstance(requires,(list,tuple)): requires=[requires]
            for validator in requires:
                value,errors=validator(value)                
                if errors!=None:
                    self.vars[name]=value
                    self.errors[name]=errors
                    break
        if not self.errors.has_key(name):
             self.vars[name]=value
             return True
        return False
    def postprocessing(self):       
        t=self['_type']
        if not t: t=self['type']='text'
        t=t.lower()
        if t=='checkbox':
            if self['value']: self['_checked']='checked'
            else: self['_checked']=None
        elif t=='radio':
            if str(self['value'])==str(self['_value']): self['_checked']='checked'
            else: self['_checked']=None
        elif t=='text':
            self['_value']=self['value']
    def xml(self):
        name=self.attributes.get('_name',None)
        if name and hasattr(self,'errors') and self.errors.get(name,None):
            return DIV.xml(self)+DIV(self.errors[name],_class='error',errors=None).xml()
        else: return DIV.xml(self)
        
class TEXTAREA(INPUT): 
    """
    TEXTAREA(_name='sometext',value='bla '*100,requires=IS_NOT_EMPTY())
    'bla bla bla ...' will be the content of the textarea field.
    """
    tag='textarea'
    def postprocessing(self):
        if not self.attributes.has_key('_rows'): self['_rows']=10
        if not self.attributes.has_key('_cols'): self['_cols']=40
        if self.attributes.has_key('value'):
            if self['value']!=None:
                self.components=[self['value']]
            else:
                self.components=[]

class OPTION(DIV): tag='option'

class OBJECT(DIV): tag='object'

class SELECT(INPUT): 
    """
    example:

    >>> SELECT('yes','no',_name='selector',value='yes',requires=IS_IN_SET(['yes','no'])).xml()
    '<select name="selector"><option value="yes" selected="selected">yes</option><option value="no">no</option></select>'
    """
    tag='select'
    def fixup(self):
        components=[]
        for c in self.components:
            if isinstance(c,OPTION):
                components.append(c)
            else:
                components.append(OPTION(c,_value=str(c)))
        self.components=components
    def postprocessing(self):
        for c in self.components:
            if c['_value']==self['value']: c['_selected']='selected'
            else: c['_selected']=None

class FIELDSET(DIV): tag='fieldset'

class FORM(DIV): 
    """
    example:
   
    >>> form=FORM(INPUT(_name="test",requires=IS_NOT_EMPTY()))
    >>> form.xml()
    '<form enctype="multipart/form-data" action="" method="post"><input name="test" /></form>'

    a FORM is container for INPUT, TEXTAREA, SELECT and other helpers
       
    form has one important method:

        form.accepts(request.vars, session)

    if form is accepted (and all validators pass) form.vars containes the
    accepted vars, otherwise form.errors contains the errors. 
    in case of errors the form is modified to present the errors to the user.
    """
    tag='form'
    def __init__(self,*components,**attributes):
        if self.tag[-1:]=='/' and components:
            raise SyntaxError, '<%s> tags cannot have components' % self.tag
        if len(components)==1 and isinstance(components[0],(list,tuple)):
            self.components=list(components[0])
        else:
            self.components=list(components)
        self.attributes=attributes
        self.fixup()
        self.postprocessing()  ### converts special attributes in components attributes
        self.vars=Storage()
        self.errors=Storage()
        self.values=Storage()
    def accepts(self,vars,session=None,formname='default',keepvalues=False):
        self.errors.clear()
        self.request_vars=Storage()
        self.request_vars.update(vars)
        self.session=session
        self.formname=formname
        self.keepvalues=keepvalues
        status=self.traverse(True)        
        if session!=None: self.formkey=session['_formkey[%s]'%formname]=str(uuid.uuid4())
        return status
    def postprocessing(self):
        if not self.attributes.has_key('_action'): self['_action']=""
        if not self.attributes.has_key('_method'): self['_method']="post"
        if not self.attributes.has_key('_enctype'): self['_enctype']="multipart/form-data"
    def hidden_fields(self):
        c=[]
        if self.attributes.has_key('hidden'):
           for key,value in self.attributes.get('hidden',{}).items():
               c.append(INPUT(_type='hidden',_name=key,_value=value))
        if hasattr(self,'formkey') and self.formkey:
           c.append(INPUT(_type='hidden',_name='_formkey',_value=self.formkey))
        if hasattr(self,'formname') and self.formname:
           c.append(INPUT(_type='hidden',_name='_formname',_value=self.formname))
        return TAG[''](c)
    def xml(self):
        newform=FORM(*self.components,**self.attributes)
        newform.append(self.hidden_fields())
        return DIV.xml(newform)

class BEAUTIFY(DIV):
    """
    example:

    >>> BEAUTIFY(['a','b',{'hello':'world'}]).xml()
    '<div><table><tr><td><div>a</div></td></tr><tr><td><div>b</div></td></tr><tr><td><div><table><tr><td><b><div>hello</div></b></td><td align="top">:</td><td><div>world</div></td></tr></table></div></td></tr></table></div>'

    turns any list, dictionarie, etc into decent looking html.
    """
    tag='div'
    def __init__(self,component,**attributes):
        self.components=[component]
        self.attributes=attributes
        components=[]
        attributes=copy.copy(self.attributes)
        if attributes.has_key('_class'): attributes['_class']+='i'
        for c in self.components:
            t=type(c)
            s=dir(c) # this really has to be fixed!!!!
            if 'xml' in s: # assume c has a .xml()
                components.append(c)
                continue
            elif 'keys' in s:
                rows=[]
                try: 
                    keys=c.keys()
                    keys.sort()
                    for key in keys:
                        if str(key)[:1]=='_': continue
                        value=c[key]
                        if type(value)==types.LambdaType: continue 
                        rows.append(TR(TD(B(BEAUTIFY(key,**attributes))),
                                       TD(':',_align="top"),
                                       TD(BEAUTIFY(value,**attributes))))
                    components.append(TABLE(*rows,**attributes))
                    continue
                except: pass
            if isinstance(c,(list,tuple)):
                items=[TR(TD(BEAUTIFY(item,**attributes))) for item in c]
                components.append(TABLE(*items,**attributes))
                continue
            elif isinstance(c,str): components.append(str(c))
            elif isinstance(c,unicode): components.append(c.encode('utf8'))
            else: components.append(repr(c))
        self.components=components

def embed64(filename=None,file=None,data=None,extension='image/gif'):
    if filename: file=open(filename,'rb')
    if file: data=file.read()
    data=base64.b64encode(data)
    return 'data:%s;base64,%s'%(extension,data)

def test():
    """
    Example:
   
    >>> from validators import *
    >>> print DIV(A('click me',_href=URL(a='a',c='b',f='c')),BR(),HR(),DIV(SPAN("World"),_class='unkown')).xml()
    <div><a href="/a/b/c">click me</a><br /><hr /><div class="unkown"><span>World</span></div></div>
    >>> print DIV(UL("doc","cat","mouse")).xml()
    <div><ul><li>doc</li><li>cat</li><li>mouse</li></ul></div>
    >>> print DIV(UL("doc",LI("cat", _class='felin'),18)).xml()
    <div><ul><li>doc</li><li class="felin">cat</li><li>18</li></ul></div>
    >>> print TABLE(['a','b','c'],TR('d','e','f'),TR(TD(1),TD(2),TD(3))).xml()
    <table><tr><td>a</td><td>b</td><td>c</td></tr><tr><td>d</td><td>e</td><td>f</td></tr><tr><td>1</td><td>2</td><td>3</td></tr></table>
    >>> form=FORM(INPUT(_type='text',_name='myvar',requires=IS_EXPR('int(value)<10')))
    >>> print form.xml()
    <form enctype="multipart/form-data" action="" method="post"><input type="text" name="myvar" /></form>
    >>> print form.accepts({'myvar':'34'},formname=None)
    False
    >>> print form.xml()
    <form enctype="multipart/form-data" action="" method="post"><input value="34" type="text" name="myvar" /><div class="error">invalid expression!</div></form>
    >>> print form.accepts({'myvar':'4'},formname=None,keepvalues=True)
    True
    >>> print form.xml()
    <form enctype="multipart/form-data" action="" method="post"><input value="4" type="text" name="myvar" /></form>
    >>> form=FORM(SELECT('cat','dog',_name='myvar'))
    >>> print form.accepts({'myvar':'dog'},formname=None)
    True
    >>> print form.xml()
    <form enctype="multipart/form-data" action="" method="post"><select name="myvar"><option value="cat">cat</option><option value="dog" selected="selected">dog</option></select></form>
    >>> form=FORM(INPUT(_type='text',_name='myvar',requires=IS_MATCH('^\w+$','only alphanumeric!')))
    >>> print form.accepts({'myvar':'as df'},formname=None)
    False
    >>> print form.xml()
    <form enctype="multipart/form-data" action="" method="post"><input value="as df" type="text" name="myvar" /><div class="error">only alphanumeric!</div></form>

    >>> session={}
    >>> form=FORM(INPUT(value="Hello World",_name="var",requires=IS_MATCH('^\w+$')))
    >>> if form.accepts({},session,formname=None): print 'passed'
    >>> if form.accepts({'var':'test ','_formkey':session['_formkey[None]']},session,formname=None): print 'passed'
    """
    pass


if __name__=='__main__':
    import doctest
    doctest.testmod()

'''
form=FORM(TABLE(TR('Name:',INPUT(_type='text',_name='name'),BR()),
                TR('Password:',INPUT(_type='password',_name='password'))))
vars={}
session={}
if form.accepts(vars,session):
    print 'accepted'
print 'not accepted'
print form.xml()
print form.session
vars['_formkey']=form.session['_formkey']
vars['name']='Massimo'
vars['password']='Dip'
if form.accepts(vars,session):
   print 'accepted'
'''


"""
This file is part of web2py Web Framework (Copyrighted, 2007)
Developed by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: GPL v2
"""

import cgi, re, random, copy, sys, types, urllib, tokenize, keyword
from storage import Storage
from validators import *
from highlight import highlight
import sanitizer

__all__=['A', 'B', 'BEAUTIFY', 'BODY', 'BR', 'CENTER', 'CODE', 'DIV', 'EM', 'EMBED', 'FIELDSET', 'FORM', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'HEAD', 'HR', 'HTML', 'IFRAME', 'IMG', 'INPUT', 'LABEL', 'LI', 'LINK', 'OL', 'UL', 'META', 'OBJECT', 'ON', 'OPTION', 'P', 'PRE', 'SCRIPT', 'SELECT', 'SPAN', 'STYLE', 'TABLE', 'TD', 'TEXTAREA', 'TH', 'TITLE', 'TR', 'TT', 'URL', 'XML', 'xmlescape']

def xmlescape(data,quote=False):
    try: 
        data=data.xml()
    except AttributeError:
        if not isinstance(data,(str,unicode)): data=str(data) 
        if isinstance(data,unicode): data=data.encode("utf8","xmlcharrefreplace")
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

ON=None

class XML:
    """
    example:
   
    >>> XML('<h1>Hello</h1>').xml()
    '<h1>Hello</h1>'

    use it to wrap a string that contains XML/HTML so that it will not be 
    escaped by the template
    """
    def __init__(self,text,sanitize=False,permitted_tags=['a','b','blockquote','br/','i', 'li', 'ol','ul', 'p', 'cite','code','pre','img/'],allowed_attributes={'a':['href','title'],'img':['src','alt'],'blockquote':['type']}):        
        if sanitize: text=sanitizer.sanitize(text,permitted_tags,allowed_attributes)
        self.text=text
    def xml(self):
        return self.text
    def __str__(self):
        return self.xml()

class DIV:
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
        if self.tag[-1]=='/' and components:
            raise SyntaxError, '<%s> tags cannot have components' % self.tag
        self.components=list(components)
        self.attributes=attributes
        self.postprocessing()
        self.errors=Storage()
        self.vars=Storage()
        self.session=None
        self.formname=None
    def postprocessing(self):
        return
    def rec_clear(self,clear_attributes_value=False):
        if hasattr(self,'attributes'):
            if clear_attributes_value:
                if self.attributes.has_key('default'):
                     self.attributes['value']=self.attributes['default']
                else: 
                     self.attributes['value']=''
                self.postprocessing()
            if self.attributes.has_key('value'):
                self.attributes['default']=self.attributes['value']        
        for c in self.components:
            if hasattr(c,'rec_clear'): 
                c.errors=self.errors
                c.vars=self.vars
                c.session=self.session
                c.formname=self.formname
                c.rec_clear(clear_attributes_value)
    def accepts(self,vars,session=None,formname='default',keepvalues=False):
        self.errors=Storage()
        self.session=session
        self.formname=formname
        self.rec_clear()
        form_key='_form_key[%s]' % formname
        if session!=None and session.has_key(form_key):
            form_key_value=session[form_key]
            del session[form_key]
            if not vars.has_key('_form_key') or \
               vars['_form_key']!=form_key_value:
                return False
        if formname and formname!=vars._formname: return False
        self.rec_accepts(vars)
        if not len(self.errors) and not keepvalues: self.rec_clear(True)
        return len(self.errors)==0        
    def rec_accepts(self,vars):
        for c in self.components:            
            if hasattr(c,'rec_accepts'): c.rec_accepts(vars)            
    def _xml(self):
        items=self.attributes.items()
        fa=' '.join([key[1:].lower() for key,value in items if key[:1]=='_' and value==None]+['%s="%s"' % (key[1:].lower(),xmlescape(value,True)) for key,value in self.attributes.items() if key[:1]=='_' and value])
        if fa: fa=' '+fa
        co=''.join([xmlescape(component) for component in self.components])
        return fa,co
    def xml(self):
        fa,co=self._xml()
        if self.tag[-1]=='/': return '<%s%s/>' % (self.tag[:-1],fa)
        return '<%s%s>%s</%s>' % (self.tag,fa,co,self.tag)
    def __str__(self):
        return self.xml()

class HTML(DIV):
    tag='html'
    def xml(self):
        fa,co=self._xml()
        return '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">\n<%s%s>%s</%s>' % (self.tag,fa,co,self.tag)

class HEAD(DIV): tag='head'

class TITLE(DIV): tag='title'

class META(DIV): tag='meta'

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
        if self.attributes.has_key('cr2br') and self.attributes['cr2br']:
             text=text.replace('\n','<br/>')
        return text

class B(DIV): tag='B'

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
        if not self.attributes.has_key('language'): language='PYTHON'
        else: language=self.attributes['language']
        if not self.attributes.has_key('link'): link=None
        else: link=self.attributes['link']

        if not self.attributes.has_key('counter'): counter=1
        else: counter=self.attributes['counter']
        if not self.attributes.has_key('styles'): styles={}
        else: styles=self.attributes['styles']
        return highlight(''.join(self.components),language=language,link=link,counter=counter,styles=styles,attributes=self.attributes)

class LABEL(DIV): tag='label'

class LI(DIV): tag='li'

class UL(DIV): 
    tag='ul'
    def postprocessing(self):        
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
    def postprocessing(self):
        components=[]
        for c in self.components:
            if isinstance(c, (TD, TH)):
                components.append(c)
            else:
                components.append(TD(c))
        self.components=components

class TABLE(DIV): 
    tag='table'
    def postprocessing(self):
        components=[]
        for c in self.components:
            if isinstance(c,TR):
                components.append(c)
            else:
                components.append(TR(*c))
        self.components=components

class IFRAME(DIV): tag='iframe'

class INPUT(DIV):
    """ 
        examples:

        >>> INPUT(_type='text',_name='name',value='Max').xml()
        '<input value="Max" type="text" name="name"/>'
        >>> INPUT(_type='checkbox',_name='checkbox',value='on').xml()
        '<input checked type="checkbox" name="checkbox"/>'
        >>> INPUT(_type='radio',_name='radio',_value='yes',value='yes').xml()
        '<input checked value="yes" type="radio" name="radio"/>'
        >>> INPUT(_type='radio',_name='radio',_value='no',value='yes').xml()
        '<input value="no" type="radio" name="radio"/>'

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
    def postprocessing(self):
        if self.attributes.has_key('_type') and \
           self.attributes.has_key('value') and self.attributes['value']!=None:
            if self.attributes['_type'].lower()=='checkbox':
               if self.attributes['value']: self.attributes['_checked']=ON
               elif self.attributes.has_key('_checked'): 
                   del self.attributes['_checked']
            elif self.attributes['_type'].lower()=='radio' and \
                 self.attributes.has_key('_value'):
                   if self.attributes['value']==self.attributes['_value']:
                       self.attributes['_checked']=ON
                   elif self.attributes.has_key('_checked'): 
                       del self.attributes['_checked']
            elif self.attributes['_type']=='text':
                   self.attributes['_value']=self.attributes['value']
        elif not self.attributes.has_key('_type') and \
           self.attributes.has_key('value') and self.attributes['value']!=None:
            self.attributes['_value']=self.attributes['value']
    def rec_accepts(self,vars):
        if not self.attributes.has_key('_name'): return True
        name=self.attributes['_name']
        if vars.has_key(name): value=vars[name]
        elif self.attributes.has_key('value') and \
           self.attributes['value']!=None: value=self.attributes['value']
        else: value=''
        if type(value)==types.StringType: self.attributes['value']=value
        self.postprocessing()
        if isinstance(value,cgi.FieldStorage): self.attributes['value']=value
        else: self.attributes['value']=str(value)
        if self.attributes.has_key('requires'):
            requires=self.attributes['requires']
            if type(requires)!=types.ListType and \
               type(requires)!=types.TupleType: requires=[requires]
            for validator in requires:                
                value,errors=validator(value)
                self.vars[name]=value
                if errors!=None:                    
                    self.errors[name]=errors                    
                    return False 
        self.vars[name]=value                           
        self.postprocessing()
        return True
    def xml(self):        
        try:
            name=self.attributes['_name']
            return DIV.xml(self)+DIV(self.errors[name],\
                   _class='error',errors=None).xml()
        except: return DIV.xml(self)
        
class TEXTAREA(INPUT): 
    """
    TEXTAREA(_name='sometext',value='bla '*100,requires=IS_NOT_EMPTY())
    'bla bla bla ...' will be the content of the textarea field.
    """
    tag='textarea'
    def postprocessing(self):
        if not self.attributes.has_key('_rows'): 
            self.attributes['_rows']=10
        if not self.attributes.has_key('_cols'):
            self.attributes['_cols']=40
        if self.attributes.has_key('value'):
            if self.attributes['value']!=None: 
                self.components=[self.attributes['value']]
            else:
                self.components=[]

class OPTION(DIV): tag='option'

class OBJECT(DIV): tag='object'

class SELECT(INPUT): 
    """
    example:

    >>> SELECT('yes','no',_name='selector',value='yes',requires=IS_IN_SET(['yes','no'])).xml()
    '<select name="selector"><option selected value="yes">yes</option><option value="no">no</option></select>'
    """
    tag='select'
    def postprocessing(self):
        components=[]
        for c in self.components:
            if isinstance(c,OPTION):
                components.append(c)
            else:
                components.append(OPTION(c,_value=str(c)))
            if self.attributes.has_key('value') and \
               self.attributes['value']!=None and \
               self.attributes['value']==components[-1].attributes['_value']:
                components[-1].attributes['_selected']=ON
        self.components=components

class FIELDSET(DIV): tag='fieldset'

class FORM(DIV): 
    """
    example:
   
    >>> form=FORM(INPUT(_name="test",requires=IS_NOT_EMPTY()))
    >>> form.xml()
    '<form enctype="multipart/form-data" method="post"><input name="test"/></form>'

    a FORM is container for INPUT, TEXTAREA, SELECT and other helpers
       
    form has one important method:

        form.accepts(request.vars, session)

    if form is accepted (and all validators pass) form.vars containes the
    accepted vars, otherwise form.errors contains the errors. 
    in case of errors the form is modified to present the errors to the user.
    """
    tag='form'
    def postprocessing(self):
        if not self.attributes.has_key('_action'): self.attributes['_action']=""
        if not self.attributes.has_key('_method'): self.attributes['_method']="post"
        if not self.attributes.has_key('_enctype'): self.attributes['_enctype']="multipart/form-data"
    def xml(self):        
        if self.session!=None:
           try:
               if self.components[-1].attributes['_name']=='_form_key':
                   self.components=self.components[:-1]
           except: pass
           form_key='_form_key[%s]' % self.formname
           key=self.session[form_key]=str(random.random())[2:]
           self.components.append(INPUT(_type='hidden',
                                  _name='_form_key',_value=key))
        if self.formname!=None:
           self.components.append(INPUT(_type='hidden',
                                  _name='_formname',_value=self.formname))
        if self.attributes.has_key('hidden'):
           hidden=self.attributes['hidden']
           for key,value in hidden.items():
               self.components.append(INPUT(_type='hidden',
                                      _name=key,_value=value))
        return DIV.xml(self)

class BEAUTIFY(DIV):
    """
    example:

    >>> BEAUTIFY(['a','b',{'hello':'world'}]).xml()
    '<div><table><tr><td><div>a</div></td></tr><tr><td><div>b</div></td></tr><tr><td><div><table><tr><td><B><div>hello</div></B></td><td align="top">:</td><td><div>world</div></td></tr></table></div></td></tr></table></div>'

    turns any list, dictionarie, etc into decent looking html.
    """
    tag='div'
    def postprocessing(self):
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

def test():
    """
    Example:
   
    >>> from validators import *
    >>> print DIV(A('click me',_href=URL(a='a',c='b',f='c')),BR(),HR(),DIV(SPAN("World"),_class='unkown')).xml()
    <div><a href="/a/b/c">click me</a><br/><hr/><div class="unkown"><span>World</span></div></div>
    >>> print DIV(UL("doc","cat","mouse")).xml()
    <div><lu><li>doc</li><li>cat</li><li>mouse</li></lu></div>
    >>> print DIV(UL("doc",LI("cat", _class='felin'),18)).xml()
    <div><lu><li>doc</li><li class="felin">cat</li><li>18</li></lu></div>
    >>> print TABLE(['a','b','c'],TR('d','e','f'),TR(TD(1),TD(2),TD(3))).xml()
    <table><tr><td>a</td><td>b</td><td>c</td></tr><tr><td>d</td><td>e</td><td>f</td></tr><tr><td>1</td><td>2</td><td>3</td></tr></table>
    >>> form=FORM(INPUT(_type='text',_name='myvar',requires=IS_EXPR('int(value)<10')))
    >>> print form.xml()
    <form enctype="multipart/form-data" method="post"><input type="text" name="myvar"/></form>
    >>> print form.accepts({'myvar':'34'},formname=None)
    False
    >>> print form.xml()
    <form enctype="multipart/form-data" method="post"><input value="34" type="text" name="myvar"/><div class="error">invalid expression!</div></form>
    >>> print form.accepts({'myvar':'4'},formname=None,keepvalues=True)
    True
    >>> print form.xml()
    <form enctype="multipart/form-data" method="post"><input value="4" type="text" name="myvar"/></form>
    >>> form=FORM(SELECT('cat','dog',_name='myvar'))
    >>> print form.accepts({'myvar':'dog'},formname=None)
    True
    >>> print form.xml()
    <form enctype="multipart/form-data" method="post"><select name="myvar"><option value="cat">cat</option><option selected value="dog">dog</option></select></form>
    >>> form=FORM(INPUT(_type='text',_name='myvar',requires=IS_MATCH('^\w+$','only alphanumeric!')))
    >>> print form.accepts({'myvar':'as df'},formname=None)
    False
    >>> print form.xml()
    <form enctype="multipart/form-data" method="post"><input value="as df" type="text" name="myvar"/><div class="error">only alphanumeric!</div></form>

    >>> session={}
    >>> form=FORM(INPUT(value="Hello World",_name="var",requires=IS_MATCH('^\w+$')))
    >>> if form.accepts({},session,formname=None): print 'passed'
    >>> tmp=form.xml() # form has to be generated or _form_key is not stored
    >>> if form.accepts({'var':'test ','_form_key':session['_form_key[None]']},session,formname=None): print 'passed'
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
vars['_form_key']=form.session['_form_key']
vars['name']='Massimo'
vars['password']='Dip'
if form.accepts(vars,session):
   print 'accepted'
'''


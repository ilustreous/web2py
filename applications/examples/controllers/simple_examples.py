def status():
    """ page that shows internal status"""
    return dict(request=request,session=session,response=response)

def hello1():
    """ simple page without template """
    return "Hello World"

def hello2():
    """ simple page without template but with internationalizaiton """
    return T("Hello World")

def hello3():
    """ page rendered by template simple_examples/index3.html or generic.html"""
    return dict(message=T("Hello World"))

def hello4():
    """ page rendered by template simple_examples/index3.html or generic.html"""
    response.view='simple_examples/hello3.html'
    return dict(message=T("Hello World"))

def hello5():
    """ generates full page in controller """
    return HTML(BODY(H1(T('Hello World'),_style="color: red;"))).xml() # .xml to serialize

def status():
    """ page that shows internal status"""
    return dict(request=request,session=session,response=response)

def redirectme():
    """ redirects to /{{=request.application}}/{{=request.controller}}/hello3 """
    redirect(URL(r=request,f='hello3'))

def raisehttp():
    """ returns an HTTP 400 ERROR page """
    raise HTTP(400,"internal error")

def raiseexception():
    """ generates an exeption, logs the event and returns a ticket number """
    1/0
    return 'oops'

def servejs():
    """ serves a js document """
    import gluon.contenttype
    response.headers['Content-Type']=gluon.contenttype.contenttype('.js')
    return 'alert("This is a Javascript document, it is not supposed to run!");'

def makejson():
    import gluon.contrib.simplejson as sj
    return sj.dumps(['foo', {'bar': ('baz', None, 1.0, 2)}])

def makertf():
    import gluon.contrib.pyrtf as q
    doc=q.Document()
    section=q.Section()
    doc.Sections.append(section)
    section.append('Section Title')
    section.append('web2py is great. '*100)
    response.headers['Content-Type']='text/rtf'
    return q.dumps(doc)

def makerss():
    import datetime
    import gluon.contrib.rss2 as rss2
    rss = rss2.RSS2(
       title = "web2py feed",
       link = "http://mdp.cti.depaul.edu",
       description = "About web2py",
       lastBuildDate = datetime.datetime.now(),
       items = [
          rss2.RSSItem(
            title = "web2py and PyRSS2Gen-0.0",
            link = "http://mdp.cti.depaul.edu/",
            description = "web2py can now make rss feeds!",
            guid = rss2.Guid("http://mdp.cti.depaul.edu/"),
            pubDate = datetime.datetime(2007, 11, 14, 10, 30)),
        ])
    response.headers['Content-Type']='application/rss+xml'
    return rss2.dumps(rss)

from gluon.contrib.markdown import WIKI

def ajaxwiki():
    form=FORM(TEXTAREA(_id='text'),INPUT(_type='button',_value='markdown',
              _onclick="ajax('ajaxwiki_onclick',['text'],'html')"))
    return dict(form=form,html=DIV(_id='html'))

def ajaxwiki_onclick():
    return WIKI(request.vars.text).xml()
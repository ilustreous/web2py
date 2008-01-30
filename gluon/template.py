"""
This file is part of web2py Web Framework (Copyrighted, 2007)
Developed by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: GPL v2
"""

import re, cgi, sys, os
from restricted import *

__all__=['reindent','Template']

re_write=re.compile('\{\{=(?P<value>.*?)\}\}',re.DOTALL)
re_html=re.compile('\}\}.*?\{\{',re.DOTALL)
re_multiline=re.compile('((?:""").*?(?:"""))|'+"((?:''').*?(?:'''))",re.DOTALL)
re_include_nameless=re.compile('\{\{\s*include\s*\}\}')
re_include=re.compile('\{\{\s*include\s+[\'"](?P<name>.*?)[\'"]\s*\}\}')
re_extend=re.compile('^\s*\{\{\s*extend\s+[\'"](?P<name>[^\']+)[\'"]\s*\}\}')

def reindent(text):
    lines=text.split('\n')
    new_lines=[]
    credit=k=0
    for raw_line in lines:
       line=raw_line.strip()
       if line[:5]=='elif ' or line[:5]=='else:' or    \
            line[:7]=='except:' or line[:7]=='except ' or \
            line[:7]=='finally:':
                k=k+credit-1
       if k<0: k=0
       new_lines.append('    '*k+line)
       credit=0
       if line=='pass' or line[:5]=='pass ':
            credit=0
            k-=1
       if line=='return' or line[:7]=='return ' or \
          line=='continue' or line[:9]=='continue ' or \
          line=='break' or line[:6]=='break':
            credit=1
            k-=1
       if line[-1:]==':': k+=1
    text='\n'.join(new_lines)
    return text

def replace(regex,text,f):
    i=0
    output=[]
    for item in regex.finditer(text):
        output.append(text[i:item.start()])
        output.append(f(item.group()))
        i=item.end()
    output.append(text[i:len(text)])
    return ''.join(output)

def parse_template(filename,path='views/',cache='cache/'):        
    filename=filename
    ##
    # read the template
    ##
    try: data=open(os.path.join(path,filename),'rb').read()
    except IOError: raise RestrictedError('Processing View '+filename,
                                  '','Unable to find the file')
    # check whether it extends a layout
    while 1:
        match=re_extend.search(data)
        if not match: break
        t=os.path.join(path,match.group('name'))
        try: parent=open(t,'rb').read()
        except IOError: raise RestrictedError('Processing View '+filename,data,'','Unable to open parent view file: '+t)
        data=re_include_nameless.sub(re_extend.sub('',data,1),parent)

    ##
    # check whether it includes subtemplates
    ##
    while 1:
        match=re_include.search(data)
        if not match: break
        t=os.path.join(path,match.group('name'))
        try: child=open(t,'rb').read()
        except IOError: raise RestrictedError('Processing View '+filename,data,'','Unable to open included view file: '+t)
        data=re_include.sub(child,data,1)

    ##
    # now convert to a python expression
    ##
    text='}}%s{{'%re_write.sub('{{response.write(\g<value>)}}',data)
    text=replace(re_html,text,lambda x: '\nresponse.write(%s,escape=False)\n'%repr(x[2:-2]))
    text=replace(re_multiline,text,lambda x: x.replace('\n','\\n'))
    return reindent(text)

if __name__=='__main__':
    print parse_template(sys.argv[1],path='../applications/welcome/views/')


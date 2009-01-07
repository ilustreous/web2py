"""
This file is part of web2py Web Framework (Copyrighted, 2007)
Developed by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: GPL v2
"""

import re, cgi, sys, os

__all__=['reindent','parse','parse_template']

re_open=re.compile('\'(\'{2})?|\"(\"{2})?|\}\}',re.M)
regexes={
"'": re.compile("(?<!\\\\)(\\\\\\\\)*'",re.M),
'"': re.compile('(?<!\\\\)(\\\\\\\\)*"',re.M),
"'''": re.compile("'''",re.M),
'"""': re.compile('"""',re.M),
}

re_include_nameless=re.compile('\{\{\s*include\s*\}\}')
re_include=re.compile('\{\{\s*include\s+(?P<name>.+?)\s*\}\}',re.DOTALL)
re_extend=re.compile('\{\{\s*extend\s+(?P<name>.+?)\s*\}\}',re.DOTALL)

def reindent(text):
    lines=text.split('\n')
    new_lines=[]
    credit=k=0
    for raw_line in lines:
       line=raw_line.strip()
       if line[:1]=='=': line='response.write(%s)' % line[1:]
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
       if line[-1:]==':' and line.strip()[:1]!='#': k+=1
    text='\n'.join(new_lines)
    return text

def parse(text):
    s,i,state='',0,0
    while text:
        if not state:  ### html
	     i=text.find('{{')
             if i<0: i=len(text)
             s+='response.write(%s,False)\n' % repr(text[:i])
             text=text[i+2:]
             state=1
        else:
             m=re_open.search(text)             
             if not m:
                  s+='%s\n' % text
                  break
             state,i=m.group(),m.end()
             if state=='}}':
                  s+='%s\n' % text[:i-2]
                  text=text[i:]
                  state=0
             else:
                  s+=text[:i]
                  text=text[i:]
                  m=regexes[state].search(text)
                  if not m: raise SyntaxError, "Unbalanced quotes"
                  i=m.end()
                  s+=text[:i].replace('\n','\\n')
                  text=text[i:]
    return reindent(s)

def replace(regex,text,f,count=0):
    i=0
    output=[]
    for item in regex.finditer(text):
        output.append(text[i:item.start()])
        output.append(f(item.group()))
        i=item.end()
        count -= 1
        if count==0: break
    output.append(text[i:len(text)])
    return ''.join(output)

def parse_template(filename,path='views/',cache='cache/',context=dict()):
    import restricted
    filename=filename
    ##
    # read the template
    ##
    try: text=open(os.path.join(path,filename),'rb').read()
    except IOError:
        raise restricted.RestrictedError('Processing View '+filename,
              '','Unable to find the file')
    # check whether it extends a layout
    while 1:
        match=re_extend.search(text)
        if not match: break
        t=os.path.join(path,eval(match.group('name'),context))
        try: parent=open(t,'rb').read()
        except IOError:
            raise restricted.RestrictedError('Processing View '+filename,text,
                  '','Unable to open parent view file: '+t)
        a,b=match.start(),match.end()
        text=text[0:a]+replace(re_include_nameless,parent,lambda x: text[b:])
    ##
    # check whether it includes subtemplates
    ##
    while 1:
        match=re_include.search(text)
        if not match: break
        t=os.path.join(path,eval(match.group('name'),context))
        try: child=open(t,'rb').read()
        except IOError:
            raise restricted.RestrictedError('Processing View '+filename,text,
                  '','Unable to open included view file: '+t)
        text=replace(re_include,text,lambda x: child,1)
    try: return parse(text)
    except SyntaxError:
        raise restricted.RestrictedError('Processing View '+filename,text,
              '','Unbalanced quotation')

if __name__=='__main__':
    print parse_template(sys.argv[1],path='../applications/welcome/views/')

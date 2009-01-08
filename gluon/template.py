"""
This file is part of web2py Web Framework (Copyrighted, 2007)
Developed by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: GPL v2
"""

import re, sys, os

__all__=['reindent','parse','parse_template']

### regex for indentation
re_block=re.compile('^(elif |else:|except:|except |finally:).*$',re.DOTALL)
re_unblock=re.compile('^(return|continue|break)(\s.*)?$',re.DOTALL)
re_pass=re.compile('^pass(\s.*)?$',re.DOTALL)
### regex for parsing {{...}}
re_open=re.compile('#|\'(\'{2})?|\"(\"{2})?|\}\}',re.MULTILINE)
re_nl=re.compile('\\\\\s*\\n\s*',re.MULTILINE)
regexes={
'#': re.compile('\\n|\}\}'),
"'": re.compile("(?<!\\\\)(\\\\\\\\)*'"),
'"': re.compile('(?<!\\\\)(\\\\\\\\)*"'),
"'''": re.compile("'''",re.MULTILINE),
'"""': re.compile('"""',re.MULTILINE),
}
### regex for extend and include
re_include_nameless=re.compile('\{\{\s*include\s*\}\}')
re_include=re.compile('\{\{\s*include\s+(?P<name>.+?)\s*\}\}',re.DOTALL)
re_extend=re.compile('\{\{\s*extend\s+(?P<name>.+?)\s*\}\}',re.DOTALL)

def reindent(text):
    new_lines,credit,k=[],0,0
    for raw_line in text.split('\n'):
       line=raw_line.strip()
       if not line: continue
       if line[0]=='=': line='response.write(%s)' % line[1:]
       if re_block.match(line): k=k+credit-1
       if k<0: k=0
       new_lines.append('    '*k+line)
       credit=0
       if re_pass.match(line): credit,k=0,k-1
       if re_unblock.match(line): credit,k=1,k-1
       if line[-1]==':' and line[0]!='#': k+=1
    return '\n'.join(new_lines)

def parse(text):
    otext=text
    s,i,state='',0,0
    ### state==0 -> in html (exit at {{)
    ### state==1 -> in code (exit at }})
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
                  s+='%s\n' % re_nl.sub('',text) # multiline statements
                  break
             key,i=m.group(),m.end()
             if key=='}}': # end of code
                  s+='%s\n' % re_nl.sub('',text[:i-2]) # multiline statements
                  text=text[i:]
                  state=0
             else: # found start of a comment or string
                  s+=text[:i]
                  text=text[i:]
                  m=regexes[key].search(text)
                  if m:
                      i=m.end()
                      if text[i-2:i]=='}}': i-=2 # this or newline closes a comment
                      if len(key)==1: s+=text[:i] # comments and single quotes
                      else: s+=text[:i].replace('\n','\\n') # multi-line only
                      text=text[i:]
                  else:
                      k=otext[:-len(text)].count('\n')+1
                      raise SyntaxError, "Unmatched quotation in line %s" % k
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
    ### read the template
    try: text=open(os.path.join(path,filename),'rb').read()
    except IOError:
        raise restricted.RestrictedError('Processing View '+filename,
              '','Unable to find the file')
    ### check whether it extends a layout
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
    ### check whether it includes subtemplates
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
    except SyntaxError, e:
            raise restricted.RestrictedError('Processing View '+filename,text,'',e)

if __name__=='__main__':
    print parse_template(sys.argv[1],path='../applications/welcome/views/')

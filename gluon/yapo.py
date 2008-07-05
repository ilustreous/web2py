import re

TEXT="""author: Massimo Di Pierro /
        <mdipierro@cs.depaul.edu>
models:
    dogs:
        name: massimo
        owners:
            massimo
            claudia
    people:
        massimo
        claudia
"""    

regex_spaces=re.compile('\s+')
regex_leading_spaces=re.compile('^\s*')
regex_newlines=re.compile('\s*(\r|\n|\r\n|\n\r)')
regex_continuation=re.compile('\s*/\s*\n\s*')
regex_dict=re.compile('\s*(?P<left>.*?)\s*(?<!\\\\):\s*(?P<right>.*)')

def loads(text):
    if not text.strip(): return []
    def parse_left(text):
        return text.replace('\\:',':').replace(' ','_')
    def parse_right(text):
        text=text.replace('\\:',':')
        try: text=float(text)
        except: pass
        try: text=int(text)
        except: pass
        return text
    d=[[]]
    text=regex_newlines.sub('\n',text)
    text=regex_continuation.sub(' ',text)
    for line in text.split('\n'):
        if not line.strip(): continue
        spaces=len(regex_leading_spaces.match(line).group())
        line=regex_spaces.sub(' ',line[spaces:])
        m=regex_dict.match(line)
        if spaces%4!=0: raise SyntaxError
        else: k=spaces/4
        d=d[:k+1]
        if m and m.group('right'):
             d[k].append((parse_left(m.group('left')),
                          parse_right(m.group('right'))))
        elif m:
             d2=[]
             d[k].append((parse_left(m.group('left')),d2))
             d.append(d2)
        else:
             d[k].append(parse_right(line))
    return d[0]

def dumps(obj,spaces=0,nl=False):
    text=''
    if isinstance(obj,list):
        if spaces: text+='\n'
        for k in obj:
            text+=dumps(k,spaces)
    elif isinstance(obj,tuple):
        text+=' '*spaces+obj[0].replace(':','\\:').replace('_',' ')+':'
        text+=dumps(obj[1],spaces+4,True)
    elif isinstance(obj,dict):
        text+=dumps(obj.items())
    elif nl:
        text+=' '+str(obj).strip().replace('\n',' ')+'\n'
    else:
        text+=' '*spaces+str(obj).strip().replace('\n',' ')+'\n'
    return text             

class Yapo:
    """
    >>> a=Yapo(TEXT)
    >>> a=Yapo(a.dumps())
    >>> len(a.author)
    43
    >>> a.keys()
    ['author', 'models']
    >>> a.models.dogs.owners.values()
    ['massimo', 'claudia']
    >>> a.append('test')
    >>> a.insert(1,'test')
    >>> len(a)
    4
    """
    def __init__(self,text=None):
        self.__dict__=dict(__counter__=0,__keys__=['__counter__','__keys__']) 
        if text: self.loads(text)
    def __getattr__(self,k):
        if self.__dict__.has_key(k): return self.__dict__[k]
        else: return None
    def __setattr__(self,k,v):
        self.__dict__[k]=v
        if not k in self.__keys__:
            self.__keys__.append(k)
            self.__counter__+=1
    def __delattr__(self,k):
        if isinstance(k,int):
            i=self.__keys__[k+2]
            del self.__keys__[k+2]
            del self.__dict__[i]
        else:
            for i,c in enumerate(self.__keys__):
                if c==k:
                    del self.__keys__[i]
                    del self.__dict__[k]
    def __getitem__(self,i):
        if isinstance(i,str): return self.__getattr__(i.replace(' ','_'))
        k=self.__keys__[i+2]
        return self.__dict__[k]
    def __setitem__(self,i,v):
        if isinstance(i,str): return self.__setattr__(i.replace(' ','_'),v)
        k=self.__keys__[i]
        self.__dict__[k]=v
    def __len__(self):
        return len(self.__keys__)-2
    def items(self):
        return [(c,self.__dict__[c]) for c in self.__keys__[2:]]
    def keys(self):
        return self.__keys__[2:]
    def values(self):
        return [self.__dict__[c] for c in self.__keys__[2:]]
    def __unpack__(self,obj):
        if isinstance(obj,list):
            x=Yapo()
            for i,item in enumerate(obj):
                 if isinstance(item,tuple):
                      x[item[0]]=self.__unpack__(item[1])
                 else:
                      x.append(self.__unpack__(item))
            return x
        return obj
    def __pack__(self,obj):
        d=[]
        if isinstance(obj,Yapo):
            for i,j in obj.items():
               if isinstance(i,int): d.append(self.__pack__(j))
               else: d.append((i,self.__pack__(j)))
        else:
            d=obj
        return d
    def loads(self,text):
        a=self.__unpack__(loads(text))
        self.__dict__=a.__dict__
        self.__keys__=a.__keys__
    def dumps(self):
        return dumps(self.__pack__(self))
    def __str__(self):
        return self.dumps()
    def __repr__(self):
        return repr(self.dumps())
    def append(self,v):
        u=self.__counter__
        self.__dict__[u]=v
        self.__keys__.append(u)
        self.__counter__+=1
    def insert(self,i,v):
        u=self.__counter__
        self.__dict__[u]=v
        self.__keys__.insert(i+2,u)
        self.__counter__+=1

if __name__=='__main__':
    import doctest
    doctest.testmod()
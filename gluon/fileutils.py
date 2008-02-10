"""
This file is part of web2py Web Framework (Copyrighted, 2007)
Developed by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: GPL v2
"""

import storage
import os
import re

__all__=['listdir', 'cleanpath', 'tar', 'untar', 'tar_compiled', 
         'get_session', 'check_credentials']

def listdir(path,expression='^.+$',drop=True,add_dirs=False):
    """
    like os.listdir() but you can specify a regex patter to filter filed.
    if add_dirs==True the returned items will have the full path.
    """
    if drop: n=len(path)
    else: n=0
    import re, os
    regex=re.compile(expression)
    items=[]
    for root,dirs,files in os.walk(path):
        if add_dirs: items.append(root[n:])
        for file in files:
           if regex.match(file):
                items.append(os.path.join(root,file)[n:])
    items.sort()
    return items

def cleanpath(path):
    """
    turns any expression/path into a valid filename. replaces / with _ and 
    removes special characters.
    """
    import re
    items=path.split('.')
    if len(items)>1: path=re.sub('[^\w\.]+','_','_'.join(items[:-1])+'.'+''.join(items[-1:]))
    else: path=re.sub('[^\w\.]+','_',''.join(items[-1:]))
    return path

def tar(file,dir,expression='^.+$'):
    """
    tars dir into file, only tars file that match expression
    """
    import tarfile
    tar=tarfile.TarFile(file,'w')
    for file in listdir(dir,expression,add_dirs=True):
        tar.add(dir+file,file,False)

def untar(file, dir):
    """
    untar file into dir
    """
    import tarfile
    tar = tarfile.TarFile(file,'r')
    tar.extractall(dir)

def tar_compiled(file,dir,expression='^.+$'):
    """
    used to tar a compiled application.
    the content of models, views, controllers is not stored in the tar file.
    """
    import tarfile, sys
    tar=tarfile.TarFile(file,'w')
    for file in listdir(dir,expression,add_dirs=True):
        if file[:6]=='models': continue
        if file[:5]=='views': continue
        if file[:11]=='controllers': continue
        tar.add(dir+file,file,False)

def get_session(request,other_application='admin'):
    """ checks that user is authorized to access other_application""" 
    if request.application==other_application: raise KeyError
    try:
        session_id=request.cookies['session_id_'+other_application].value
        osession=storage.load_storage('applications/%s/sessions/%s' % \
                                      (other_application,session_id))
    except IOError: osession=storage.Storage()
    return osession

def check_credentials(request,other_application='admin'):
    """ checks that user is authorized to access other_application""" 
    return get_session(request,other_application).authorized

def fix_newlines(path):
    regex=re.compile(r'(\r\n|\r|\n)')
    for filename in listdir(path,'.*\.(py|html)$',drop=False):
        data=open(filename,'rb').read()
        data=regex.sub('\n',data)
        open(filename,'wb').write(data)

def copystream(src,dest,size=None,chunk_size=1):
    """
    this is here because I think there is a bug in shutil.copyfileobj
    """
    while size:
        data=src.read(chunk_size)
        length=len(data)
        if size!=None:
            if length>size: data,length=data[:size],size
            size-=length
        if length==0: break
        dest.write(data)
        if length<chunk_size: break
    dest.seek(0)
    return
    
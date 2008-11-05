"""
This file is part of the web2py Web Framework (Copyrighted, 2007-2008)
Developed in Python by Massimo Di Pierro <mdipierro@cs.depaul.edu>
"""

import os,stat,time,re
from http import HTTP
from contenttype import contenttype

regex_start_range=re.compile('\d+(?=\-)')
regex_stop_range=re.compile('(?<=\-)\d+')

error_message='<html><body><h1>Invalid request</h1></body></html>'

def streamer(file,chunk_size=10**6,bytes=None):
    offset=0
    while bytes==None or offset<bytes:
        if bytes!=None and bytes-offset<chunk_size: chunk_size=bytes-offset
        data=file.read(chunk_size)
        length=len(data)
        if not length: break
        else: yield data
        if length<chunk_size: break
        offset+=length

def stream_file_or_304_or_206(static_file,chunk_size=10**6,request=None,headers={},error_message=error_message):
    if not os.path.exists(static_file):
         raise HTTP(404,error_message,web2py_error='invalid file')
    stat_file=os.stat(static_file)
    fsize=stat_file[stat.ST_SIZE]
    mtime=time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(stat_file[stat.ST_MTIME]))
    headers['Content-Type']=contenttype(static_file)
    headers['Last-Modified']=mtime
    headers['Pragma']="cache"
    headers['Cache-Control']="private" 
    if request and request.env.http_if_modified_since==mtime:
        raise HTTP(304)
    elif request and request.env.http_range:
        start_items=regex_start_range.findall(request.env.http_range)
        if not start_items: start_items=[0]
        stop_items=regex_stop_range.findall(request.env.http_range)
        if not stop_items or int(stop_items[0])>fsize-1: stop_items=[fsize-1]
        part=(int(start_items[0]),int(stop_items[0]),fsize)
        bytes=part[1]-part[0]+1
        try: stream=open(static_file,'rb')
        except IOError: raise HTTP(400)
        stream.seek(part[0])
        headers['Content-Range']='bytes %i-%i/%i' % part
        headers['Content-Length']='%i' % (bytes)
        raise HTTP(206,streamer(stream,chunk_size=chunk_size,bytes=bytes),**headers)
    else:
        try: stream=open(static_file,'rb')
        except IOError: raise HTTP(400)
        headers['Content-Length']=fsize
        raise HTTP(200,streamer(stream,chunk_size=chunk_size),**headers)
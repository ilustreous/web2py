"""
This file is part of the web2py Web Framework (Copyrighted, 2007-2008)
Developed in Python by Massimo Di Pierro <mdipierro@cs.depaul.edu>
"""

def streamer(file,chunk_size=10**6):
    while 1:
        data=file.read(chunk_size)
        length=len(data)
        if not length: break
        else: yield data
        if length<chunk_size: break
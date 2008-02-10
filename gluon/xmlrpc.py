"""
This file is part of the web2py Web Framework (Copyrighted, 2007-2008)
Developed in Python by Massimo Di Pierro <mdipierro@cs.depaul.edu>
"""

from SimpleXMLRPCServer import SimpleXMLRPCDispatcher

def handler(request,response,methods):
    response.session_id=None # no sessions for xmlrpc
    dispatcher = SimpleXMLRPCDispatcher(allow_none=True, encoding=None)
    for method in methods: dispatcher.register_function(method)
    dispatcher.register_introspection_functions()
    response.headers['Content-type']='text/xml'
    dispatch=getattr(dispatcher, '_dispatch', None)
    return dispatcher._marshaled_dispatch(request.body.read(), dispatch)
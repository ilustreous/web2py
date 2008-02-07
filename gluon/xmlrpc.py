from SimpleXMLRPCServer import SimpleXMLRPCDispatcher

def handler(request,response,methods):
    dispatcher = SimpleXMLRPCDispatcher(allow_none=True, encoding=None)
    for method in methods: dispatcher.register_function(method)
    dispatcher.register_introspection_functions()
    response.headers['Content-type']='text/xml'
    dispatch=getattr(dispatcher, '_dispatch', None)
    return dispatcher._marshaled_dispatch(request.body, dispatch)
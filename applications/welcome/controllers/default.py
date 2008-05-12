session.forget() # comment or remove if you want to store sessions

def index():
    response.flash=T('Welcome to web2py')
    return dict(message=T('Hello World'))
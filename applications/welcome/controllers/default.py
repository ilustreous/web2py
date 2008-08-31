# session.forget() ## uncomment if you do not need sessions

def index():
    response.flash=T('Welcome to web2py')
    return dict(message=T('Hello World'))
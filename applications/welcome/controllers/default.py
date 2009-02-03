#!/usr/bin/python
# -*- coding: utf-8 -*-

# # sample index page with internationalization (T)
def index():
    response.flash = T('Welcome to web2py')
    return dict(message=T('Hello World'))


# # uncomment the following if you have defined "auth" and "crud" in models
# def user(): return dict(form=auth())
# def data(): return dict(form=crud())
# def download(): return response.download(request,db)
# # tip: use @auth.requires_login, requires_membership, requires_permission

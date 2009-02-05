#!/usr/bin/python
# -*- coding: utf-8 -*-
response.title = 'web2py Enterprise Web Framework'
response.keywords = 'web2py, Python, Enterprise Web Framework'
response.description = 'web2py Enterprise Web Framework'

session.forget()


def index():
    return response.render(dict())


def what():
    return response.render(dict())


def who():
    return response.render(dict())


def download():
    return response.render(dict())


def docs():
    return response.render(dict())


def support():
    return response.render(dict())


def api():
    return response.render(dict())


def examples():
    return response.render(dict())


def dal():
    return response.render(dict())


def license():
    return response.render(dict())


def tools():
    return response.render(dict())

def version():
   return request.env.web2py_version

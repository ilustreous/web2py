#!/usr/bin/python
# coding: utf-8

from hashlib import md5

def md5_hash(text):
    """ Generate a md5 hash with the given text """

    return md5(text).hexdigest()

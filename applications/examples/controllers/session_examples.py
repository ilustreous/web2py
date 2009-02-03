#!/usr/bin/python
# -*- coding: utf-8 -*-


def counter():
    """ every time you reloads, it increases the session.counter """

    if not session.counter:
        session.counter = 0
    session.counter += 1
    return dict(counter=session.counter)



#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import os
import sys
import logging
import cPickle
import pickle
import wsgiref.handlers

import gluon.main
import google

sys.modules['cPickle'] = sys.modules['pickle']
debug = os.environ.get('SERVER_SOFTWARE', '').startswith('Devel')

def log_stats(fun):
    """Function that will act as a decorator to make logging"""

    if debug:

        def newfun(env, res):
            """Log the execution time of the passed function"""

            timer = lambda t: (t.time(), t.clock())
            (t0, c0) = timer(time)
            executed_function = fun(env, res)
            (ti, c1) = timer(time)
            log_info = """**** Request: %5.0fms/%.0fms (real time/cpu time)"""
            log_info = log_info % ((t1 - t0) * 1000, (c1 - c0) * 1000)
            logging.info(log_info)

            return executed_function

        return newfun
    else:
        return fun


# comment the line below and uncomment the decorator @log_stats to enable
# logging of stats on GAE
logging.basicConfig(level=35)

# @log_stats
def wsgiapp(env, res):
    """Return the wsgiapp"""

    return gluon.main.wsgibase(env, res)


def main():
    """Run the wsgi app"""

    wsgiref.handlers.CGIHandler().run(wsgiapp)


if __name__ == '__main__':
    main()

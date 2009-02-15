#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys

path = os.path.dirname(os.path.abspath(__file__))
if not path in sys.path:
    sys.path.append(path)
os.chdir(path)

import gluon.import_all

from gluon.contrib.cron import hardcron
from gluon.widget import start

# Starts cron daemon
cron = hardcron()
cron.start()

# Start Web2py !
start()

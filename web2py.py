#!/usr/bin/python
# -*- coding: utf-8 -*-

import gluon.import_all

from gluon.contrib.cron import hardcron
from gluon.widget import start

# Starts cron daemon
cron = hardcron()
cron.start()

# Start Web2py !
start()

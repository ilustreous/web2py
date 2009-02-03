#!/usr/bin/python
# -*- coding: utf-8 -*-

from gluon.contrib.cron import hardcron
cron = hardcron()
cron.start()

import gluon.import_all
from gluon.widget import start
start()


#!/usr/bin/env python2.5

from gluon.contrib.cron import hardcron
cron = hardcron()
cron.start()

import gluon.import_all
from gluon.widget import start
start()


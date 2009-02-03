#!/usr/bin/python
# -*- coding: utf-8 -*-

__name__ = 'cron'
__version__ = (0, 1, 0)
__author__ = 'Attila Csipa <web2py@csipa.in.rs>'

_generator_name = __name__ + '-' + '.'.join(map(str, __version__))

import sys
import os
import threading
import logging
import time
import sched
import re
import datetime
from subprocess import Popen, PIPE

# crontype can be 'Soft', 'Hard', None, 'External'

crontype = 'Soft'


class extcron(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.setDaemon(False)
        self.basedir = os.getcwd()

    def run(self):
        logging.debug('External cron invocation')
        crondance(apppath({'web2py_path': self.basedir}), 'ext')


class hardcron(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.basedir = os.getcwd()

    def run(self):
        global crontype
        crontype = 'Hard'
        s = sched.scheduler(time.time, time.sleep)
        logging.info('Hard cron daemon started')
        while True:
            now = time.time()
            s.enter(60 - now % 60, 1, crondance, (apppath({'web2py_path'
                    : self.basedir}), 'hard'))
            s.run()


class softcron(threading.Thread):

    def __init__(self, env):
        threading.Thread.__init__(self)
        self.env = env
        self.cronmaster = 0
        self.softwindow = 120

    def run(self):
        path = apppath(self.env)
        marker = os.path.join(path, 'admin/cron/cron.master')  # location of Chronos, Master of All Time !
        if not os.path.exists(marker):  # cron master missing, try to recreate one
            logging.warning('WEB2PY CRON: cron.master not found at %s. Trying to recreate.'
                             % marker)
            mfile = open(marker, 'wb')  # touch cron marker
            mfile.close()

        now = time.time()
        if 60 > now - self.cronmaster:  # our own thread did a cron check less than a minute ago, don't even bother checking the file
            logging.debug("Don't bother with cron.master, it's only %s s old"
                           % (now - self.cronmaster))
            return

        try:
            self.cronmaster = os.stat(marker).st_mtime  # get last_modified timestamp of cron.master file
        except Exception, e:
            self.cronmaster = 0
            logging.warning('cron.master trouble: %s' % e)

        logging.debug('Cronmaster stamp: %s, Now: %s'
                       % (self.cronmaster, now))
        if 60 <= now - self.cronmaster:  # new minute, do the cron dance
            mfile = open(marker, 'wb')  # touch cron marker
            mfile.close()
            crondance(path, 'soft')


def apppath(env=None):
    try:
        apppath = os.path.join(env.get('web2py_path'), 'applications')
    except:
        apppath = os.path.join(os.path.split(env.get('SCRIPT_FILENAME'
                               ))[0], 'applications')
    return apppath


def rangetolist(str, period='min'):
    retval = []
    if str.startswith('*'):
        if period == 'min':
            str = str.replace('*', '0-59', 1)
        elif period == 'hr':
            str = str.replace('*', '0-23', 1)
        elif period == 'dom':
            str = str.replace('*', '1-31', 1)
        elif period == 'mon':
            str = str.replace('*', '1-12', 1)
        elif period == 'dow':
            str = str.replace('*', '0-6', 1)
    m = re.compile(r'(\d+)-(\d+)/(\d+)')
    match = m.match(str)
    if match:
        for i in range(int(match.group(1)), int(match.group(2)) + 1):
            if i % int(match.group(3)) == 0:
                retval.append(i)
    return retval


def parsecronline(line):
    task = {}
    params = line.split(None, 6)
    for (str, id) in zip(params[:4], ['min', 'hr', 'dom', 'mon', 'dow'
                         ]):
        if not str in [None, '*']:
            task[id] = []
            vals = str.split(',')
            for val in vals:
                if val.find('/') > -1:
                    task[id] += rangetolist(val, id)
                elif val.isdigit():
                    task[id].append(int(val))
    if len(params) > 5:
        task['user'] = params[5]
        task['cmd'] = params[6].strip()
    return task


class cronlauncher(threading.Thread):

    def __init__(self, cmdline):
        threading.Thread.__init__(self)
        self.cmd = cmdline

    def run(self):
        try:
            if os.name == 'nt':
                proc = Popen([self.cmd], stdin=PIPE, stdout=PIPE,
                             stderr=PIPE, shell=True)
            else:
                proc = Popen(
                    [self.cmd],
                    stdin=PIPE,
                    stdout=PIPE,
                    stderr=PIPE,
                    shell=True,
                    close_fds=True,
                    )
            try:
                pipes = proc.communicate()
            except:
                pipes = ()
            proc.wait()
            logging.debug('WEB2PY CRON done')
            content = ''.join(pipes)
            if len(content):
                logging.info('WEB2PY CRON Call returned: %s' % content)
            if proc.returncode != 0:
                logging.warning('WEB2PY CRON Call returned code %s: %s'
                                 % (proc.returncode,
                                proc.stderr.read()))
        except Exception, e:
            logging.error('WEB2PY CRON: Execution error for %s: %s'
                           % (self.cmd, e))


def crondance(apppath, ctype='soft'):
    try:
        now_s = time.localtime()
        for dir in os.listdir(apppath):
            cronpath = os.path.join(apppath, dir, 'cron')
            crontab = os.path.join(cronpath, 'crontab')
            if os.path.exists(crontab):
                f = open(crontab, 'rt')
                cronlines = f.readlines()
                for cline in filter(lambda x: \
                                    not x.strip().startswith('#')\
                                     and len(x.strip()) > 0, cronlines):
                    task = parsecronline(cline)
                    go = True
                    if task.has_key('min') and not now_s.tm_min\
                         in task['min']:
                        if task['min'] > -1:
                            go = False
                    elif task.has_key('hr') and not now_s.tm_hour\
                         in task['hr']:
                        go = False
                    elif task.has_key('mon') and not now_s.tm_mon\
                         in task['mon']:
                        go = False
                    elif task.has_key('dom') and not now_s.tm_mday\
                         in task['dom']:
                        go = False
                    elif task.has_key('dow') and not now_s.tm_wday\
                         in task['dow']:
                        go = False
                    if go and task.has_key('cmd'):
                        logging.info('WEB2PY CRON (%s): Application: %s executing %s in %s at %s'
                                 % (ctype, dir, task.get('cmd'),
                                os.getcwd(), datetime.datetime.now()))
                        try:
                            if task['cmd'].startswith('*'):
                                if task['cmd'].endswith('.py'):
                                    launchstr = \
    "%s web2py.py -P -M -S %s -a 'recycle' -R %s"
                                else:
                                    launchstr = \
    "%s web2py.py -P -M -S %s/%s -a 'recycle'"

                                cronlauncher(launchstr
                                         % (sys.executable, dir,
                                        (task['cmd'])[1:])).start()
                            else:
                                cronlauncher(task.get('cmd')).start()
                        except Exception, e:

                            logging.warning('WEB2PY CRON: Execution error for %s: %s'
                                     % (task.get('cmd'), e))
    except Exception, e:

        import traceback
        logging.warning(traceback.format_exc())
        logging.warning('WEB2PY CRON: exception: %s', e)



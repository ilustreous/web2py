#!/usr/bin/python
# -*- coding: utf-8 -*-
import time
import os
import sys
import logging
import wsgiref.handlers
import gluon.main

wsgiref.handlers.CGIHandler().run(gluon.main.wsgibase)

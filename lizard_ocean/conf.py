# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-
# See https://github.com/jezdez/django-appconf for an explanation.
# This file needs to be loaded upon app loading, so it is imported
# from our models.py.
from __future__ import unicode_literals
from __future__ import print_function
import os

from django.conf import settings
from appconf import AppConf

_our_dir = os.path.dirname(os.path.abspath(__file__))


class OceanAppConf(AppConf):
    # Use it like ``settings.OCEAN_BASEDIR``.
    
    # Default settings are our own test data dirs.
    BASEDIR = os.path.join(_our_dir, 'samples')

    class Meta:
        prefix = 'OCEAN'

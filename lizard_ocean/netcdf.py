# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function
import os

from django.conf import settings


def netcdf_filepaths():
    files = [f for f in os.listdir(settings.OCEAN_NETCDF_BASEDIR)
             if f.endswith('.nc')]
    return [os.path.join(settings.OCEAN_NETCDF_BASEDIR, f) for f in files]
    

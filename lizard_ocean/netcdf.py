# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function
import os

from netCDF4 import Dataset
from django.conf import settings


def netcdf_filepaths():
    files = [f for f in os.listdir(settings.OCEAN_NETCDF_BASEDIR)
             if f.endswith('.nc')]
    return [os.path.join(settings.OCEAN_NETCDF_BASEDIR, f) for f in files]
    

class NetcdfFile(object):
    """Wrapper around a netcdf file, used to extract information."""

    def __init__(self, filename):
        self.dataset = Dataset(filename)

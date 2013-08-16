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
        self.filename = filename
        self.dataset = Dataset(filename)
        self.metadata_keys = ['x', 'y', 'id', 'name']

    @property
    def stations(self):
        """Return station metadata, i.e. everything apart from timeseries."""
        xs = [float(x) for x in self.dataset.variables['x']]
        ys = [float(y) for y in self.dataset.variables['y']]
        ids = [''.join(id.data) for id in self.dataset.variables['station_id']]
        names = [''.join(name.data) for name in self.dataset.variables['station_names']]

        keys = self.metadata_keys
        values_per_station = zip(xs, ys, ids, names)
        result = []
        for values in values_per_station:
            # values is a list of items in the order of our keys.
            result.append(dict(zip(keys, values)))
        return result

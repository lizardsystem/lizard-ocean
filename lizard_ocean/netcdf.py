# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function
import datetime
import json
import logging
import os

import pytz
from netCDF4 import Dataset
from netCDF4 import num2date
from django.conf import settings
from django.utils.functional import cached_property


logger = logging.getLogger(__name__)


def netcdf_filepaths():
    files = [f for f in os.listdir(settings.OCEAN_BASEDIR)
             if f.endswith('.nc')]
    return sorted([os.path.join(settings.OCEAN_BASEDIR, f)
                   for f in files])


class NetcdfFile(object):
    """Wrapper around a netcdf file, used to extract information."""

    def __init__(self, filename):
        self.filename = filename
        self.dataset = Dataset(filename, mode='r')
        self.metadata_keys = ['x', 'y', 'id', 'name']

    @cached_property
    def stations(self):
        """Return station metadata, i.e. everything apart from timeseries."""
        xs = [float(x) for x in self.dataset.variables['x']]
        ys = [float(y) for y in self.dataset.variables['y']]
        ids = [''.join(id.data) for id in self.dataset.variables['station_id']]
        names = [''.join(name.data) for name in self.dataset.variables['station_names']]

        keys = self.metadata_keys
        values_per_station = zip(xs, ys, ids, names)
        result = []
        for index, values in enumerate(values_per_station):
            # values is a list of items in the order of our keys.
            station = dict(zip(keys, values))
            station['station_index'] = index
            result.append(station)
        return result

    @cached_property
    def parameters(self):
        """Return id/name/unit dicts of the available parameters.

        There are a couple of known variables (x, y and so), the
        others are parameters we want to see graphs for.
        """
        result = []
        for id, variable in self.dataset.variables.items():
            is_mappable_variable = 'time' in variable.dimensions and 'stations' in variable.dimensions
            if not is_mappable_variable:
                continue
            try:
                name = variable.long_name
                unit = variable.units
            except AttributeError:
                msg = "Variable '{}' in {} misses 'long_name' or 'units'"
                msg = msg.format(id, self.filename)
                logger.exception(msg)
                continue  # Omit this parameter.
            result.append(dict(id=id, name=name, unit=unit))
        return result

    @cached_property
    def timestamps(self):
        """Return python datetime values for all times in the dataset.

        The values are in 'minutes since 1970-01-01 00:00:00.0 +0000'.
        """
        datetimes = num2date(self.dataset.variables['time'][:],
                        self.dataset.variables['time'].units)
        # NetCDF4 deliberately returns naive datetimes.
        # We have to manually attach UTC tzinfo objects to them.
        # ref: http://netcdf4-python.googlecode.com/svn/trunk/docs/netCDF4-module.html#num2date
        datetimes = [dt.replace(tzinfo=pytz.utc) for dt in datetimes]
        return datetimes

    def values(self, parameter_id, station_index):
        """Return all values for the parameter."""
        return self.dataset.variables[parameter_id][:, station_index]

    def time_value_pairs(self, parameter_id, station_index):
        """Return pairs of time/value. 

        Value should be a float instead of some numpy thingy.
        Timestamps are already OK.

        Filter out time/value pairs if the value is NotANumber.
        """
        pairs = zip(self.timestamps, self.values(parameter_id, station_index))
        return [(timestamp, float(value)) for timestamp, value in pairs if value]

    def close(self):
        self.dataset.close()

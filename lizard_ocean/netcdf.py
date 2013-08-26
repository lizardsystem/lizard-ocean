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
from lizard_map.lizard_widgets import WorkspaceAcceptable


logger = logging.getLogger(__name__)


def netcdf_filepaths():
    files = [f for f in os.listdir(settings.OCEAN_NETCDF_BASEDIR)
             if f.endswith('.nc')]
    return sorted([os.path.join(settings.OCEAN_NETCDF_BASEDIR, f) 
                   for f in files])


class NetcdfFile(object):
    """Wrapper around a netcdf file, used to extract information."""

    def __init__(self, filename):
        self.filename = filename
        self.dataset = Dataset(filename)
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
        known_variables = ['x', 'y', 'time', 'lat', 'lon',
                           'station_id', 'station_names', 'crs']
        for id, variable in self.dataset.variables.items():
            if id in known_variables:
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
    def workspace_acceptables(self):
        """Return workspace acceptables for the user interface."""
        result = []
        for parameter in self.parameters:
            adapter_layer_json = {'filename': os.path.basename(self.filename),
                                  'parameter_id': parameter['id']}
            result.append(WorkspaceAcceptable(
                name=parameter['name'],
                adapter_name='adapter_ocean',
                adapter_layer_json=json.dumps(adapter_layer_json)))
        return result

    @cached_property
    def timestamps(self):
        """Return python datetime values for all times in the dataset.

        The values are in 'minutes since 1970-01-01 00:00:00.0 +0000'.
        """

        return num2date(self.dataset.variables['time'][:],
                        'minutes since 1970-01-01 00:00:00.0 +0000')

    def values(self, parameter_id, station_index):
        """Return all values for the parameter."""
        # Note: ``slice(None)`` is the same as ``:``.
        return self.dataset.variables[parameter_id][slice(None), station_index]

    def time_value_pairs(self, parameter_id, station_index):
        """Return pairs of time/value. 

        Value should be a float instead of some numpy thingy.
        Timestamps are already OK.

        Filter out time/value pairs if the value is NotANumber.
        """
        pairs = zip(self.timestamps, self.values(parameter_id, station_index))
        return [(timestamp, float(value)) for timestamp, value in pairs if value]

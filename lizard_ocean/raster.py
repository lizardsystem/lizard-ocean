# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import
from __future__ import division

#import os
import glob
#import logging

from django.conf import settings


def get_rasters(raster_path=settings.OCEAN_RASTER_BASEDIR):
    """
    Look for georeferenced raster files in path and return dictionary with key:
    date, value: raster path ordered by date

    :param string path: root path with raster data
    :returns: dictionary with key: date, value: raster path
    """
    rasters = {}
    try:
        raster_list = glob.glob(raster_path + "/*.png")
    except IOError:
        raise StandardError("Directory {} does not exist".format(raster_path))

    rasters = dict((path[-12:-4], path) for path in raster_list)

    print(rasters)
    return rasters

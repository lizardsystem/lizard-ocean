# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import
from __future__ import division

import os
import glob
#import logging

from django.conf import settings


def rasters(raster_path=settings.OCEAN_RASTER_BASEDIR):
    """
    Returns dictionary with raster path names

    Look for georeferenced raster files in path and return dictionary with key:
    date, value: raster path ordered by date

    :param string path: root path with raster data
    :returns: dictionary with key: date, value: raster path
    """
    if os.path.exists(raster_path):
        raster_list = glob.glob(raster_path + "/*.png")
    else:
        raise StandardError("Directory {} does not exist".format(raster_path))

    #NOTE: works for now; wait for answer client for definitive filename syntax
    raster_dict = dict((path.split('_')[-1][:-4], path)
                       for path in raster_list)

    return raster_dict

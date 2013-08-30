# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import
from __future__ import division

import os
import logging

from django.conf import settings


logger = logging.getLogger(__name__)


class RasterSet(object):
    def __init__(self, dir):
        self.dir = dir
        self.name = os.path.basename(dir)
        self.png_filenames = [f for f in os.listdir(dir) if os.path.splitext(f)[1] == '.png']
        self.png_filenames = sorted(self.png_filenames)


def raster_sets(base_dir=settings.OCEAN_RASTER_BASEDIR):
    if not os.path.exists(base_dir):
        raise StandardError("Directory {} does not exist".format(base_dir))

    result = []

    for filename in os.listdir(base_dir):
        raster_set_dir = os.path.join(base_dir, filename)
        if os.path.isdir(raster_set_dir):
            result.append(RasterSet(raster_set_dir))

    return result

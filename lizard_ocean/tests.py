# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function

from django.test import TestCase
from django.conf import settings


class ConfTest(TestCase):

    def test_config_loaded(self):
        self.assertTrue(hasattr(settings, 'OCEAN_RASTER_BASEDIR'))


class RasterTest(TestCase):

    def test_get_rasters(self):
        from .raster import get_rasters

        rasters = get_rasters()
        self.assertTrue('20130806' in rasters)
        self.assertEquals(rasters['20130806'],
                          settings.OCEAN_RASTER_BASEDIR + '/test_20130806.png')

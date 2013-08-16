# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function
import os

from django.test import TestCase
from django.conf import settings

from lizard_ocean import netcdf
from lizard_ocean import views


class ConfTest(TestCase):

    def test_config_loaded(self):
        self.assertTrue(hasattr(settings, 'OCEAN_RASTER_BASEDIR'))


class RasterTest(TestCase):

    def test_rasters(self):
        from lizard_ocean.raster import rasters

        rasters = rasters()
        self.assertTrue('20130806' in rasters)
        self.assertEquals(rasters['20130806'],
                          settings.OCEAN_RASTER_BASEDIR + '/test_20130806.png')


class NetcdfTest(TestCase):

    def test_filepaths(self):
        self.assertEquals(len(netcdf.netcdf_filepaths()), 1)
    
    
class NetcdfFileTest(TestCase):

    def setUp(self):
        filename = os.path.join(settings.OCEAN_NETCDF_BASEDIR, 
                                'Phase_One_dummy.nc')
        self.netcdf_file = netcdf.NetcdfFile(filename)

    def test_smoke(self):
        # Turn it on and make sure it at least doesn't belch out smoke.
        self.assertTrue(self.netcdf_file.dataset)
    
    
class RawNetcdfViewTest(TestCase):

    def test_filepaths(self):
        view = views.RawNetcdfView()
        self.assertTrue(view.filepaths)
    

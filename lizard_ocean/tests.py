# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function
import datetime
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

    def test_minutes1970_to_datetime1(self):
        self.assertEquals(netcdf.BASE_1970_TIME, 
                          netcdf.minutes1970_to_datetime(0))

    def test_minutes1970_to_datetime2(self):
        expected = netcdf.BASE_1970_TIME + datetime.timedelta(hours=1)
        self.assertEquals(expected, 
                          netcdf.minutes1970_to_datetime(60))
    
    
class NetcdfFileTest(TestCase):

    def setUp(self):
        filename = os.path.join(settings.OCEAN_NETCDF_BASEDIR, 
                                'Phase_One_dummy.nc')
        self.netcdf_file = netcdf.NetcdfFile(filename)

    def test_smoke(self):
        # Turn it on and make sure it at least doesn't belch out smoke.
        self.assertTrue(self.netcdf_file.dataset)

    def test_stations1(self):
        self.assertEquals(len(self.netcdf_file.stations), 8)

    def test_stations2(self):
        available_keys = sorted(self.netcdf_file.stations[0].keys())
        expected_keys = sorted(['x', 'y', 'station_index', 'id', 'name'])
        self.assertEquals(available_keys, expected_keys)

    def test_stations3(self):
        first_item = self.netcdf_file.stations[0]
        self.assertEquals(first_item['x'], 51.5)
        self.assertEquals(first_item['name'], 'Test_7')

    def test_parameters1(self):
        parameters = self.netcdf_file.parameters
        self.assertEquals(len(parameters), 1)

    def test_parameters2(self):
        parameter = self.netcdf_file.parameters[0]
        self.assertEquals(parameter['unit'], 'm')

    def test_workspace_acceptables(self):
        acceptables = self.netcdf_file.workspace_acceptables
        self.assertEquals(acceptables[0].adapter_name, 'adapter_ocean')

    def test_workspace_timestamps(self):
        timestamps = self.netcdf_file.timestamps
        self.assertEquals(type(timestamps[0]), datetime.datetime)

    def test_values(self):
        parameter_id = self.netcdf_file.parameters[0]['id']
        station_index = 7
        self.assertEquals(
            len(self.netcdf_file.values(parameter_id, station_index)),
            len(self.netcdf_file.timestamps))

    def test_time_value_pairs1(self):
        parameter_id = self.netcdf_file.parameters[0]['id']
        station_index = 7
        time = self.netcdf_file.timestamps[-1]
        value = float(self.netcdf_file.values(parameter_id, station_index)[-1])
        self.assertEquals(
            self.netcdf_file.time_value_pairs(parameter_id, station_index)[-1],
            (time, value))

    def test_time_value_pairs2(self):
        parameter_id = self.netcdf_file.parameters[0]['id']
        station_index = 7
        time = self.netcdf_file.timestamps[0]
        value = float(self.netcdf_file.values(parameter_id, station_index)[0])
        # Value is NaN, so the first time/value pair returned
        # shouldn't be the first time and first value!
        self.assertNotEquals(
            self.netcdf_file.time_value_pairs(parameter_id, station_index)[0],
            (time, value))
                      
    
class RawNetcdfViewTest(TestCase):

    def test_filepaths(self):
        view = views.RawNetcdfView()
        self.assertTrue(view.filepaths)
    
    def test_netcdf_files(self):
        # More of a smoke test.
        view = views.RawNetcdfView()
        self.assertEquals(len(view.netcdf_files), 1)


class MainViewTest(TestCase):

    def test_point_files(self):
        view = views.MainView()
        self.assertEquals(len(view.point_files()), 1)

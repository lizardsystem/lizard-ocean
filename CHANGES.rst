Changelog of lizard-ocean
===================================================


0.1 (unreleased)
----------------

- Started netcdf file reading including a view for debug purposes.
  Every netcdf file ends up as a category on the main page and its
  parameters as map layers. The data points are rendered on the map
  and all the regular lizard-map functionality works (clicking, graph,
  date range).

- Added function in raster.py to read dir with rasters and return a
  dict.

- Test pngs to raster sample dir.

- Added ``OCEAN_RASTER_BASEDIR`` and ``OCEAN_NETCDF_BASEDIR`` settings
  with a local sample dir as default.

- Started main page.

- Initial project structure created with nensskel 1.34.dev0.

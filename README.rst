lizard-ocean
==========================================

Lizard app for showing png and netcdf ocean monitoring data, initially
for the "ADOOS: Abu Dhabi ocean observing system" website. Note: the
png and netcdf files are exported from FEWS.


Input data
----------

There are two basic kinds of data:

- **Netcdf files**: contain locations and their timeseries. There are
  two kinds in the ADOOS project: buoy locations and gridpoints (note:
  this means points placed on a grid on a map, not image-like grid
  data).

- **Animations of PNGs**. Sequentially numbered PNG files including
  ``*.pngw`` projection files. Should be shown in the order given. In
  the initial ADOOS project there are two sets of PNGs, the second set
  has more detail and deals with a smaller area.

In the initial project, both kinds each are used twice. So we should
allow an arbitrary number of them.


TODO and TO_FIGURE_OUT: 

- Mapping of var/ocean-netcdf/xyz and var/ocean-png/abc to items in
  the sidebar and on the map.

- User interaction.

- Display on the map.

- PNG animation.

- Debug data-dump page.

- Django-appconfig integration.

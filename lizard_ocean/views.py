# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function

from django.utils.translation import ugettext as _
# from django.core.urlresolvers import reverse
from lizard_map.views import MapView
from lizard_ui.views import UiView

from lizard_ocean import netcdf


# class TodoView(UiView):
#     """Simple view without a map."""
#     template_name = 'lizard_ocean/todo.html'
#     page_title = _('TODO view')


class MainView(MapView):
    """Main view of the application."""
    template_name = 'lizard_ocean/main.html'
    # page_title = _('')


class RawNetcdfView(UiView):
    """Raw debug view of the netcdf data."""
    template_name = 'lizard_ocean/raw_netcdf.html'
    # page_title = _('')

    @property
    def filepaths(self):
        return netcdf.netcdf_filepaths()

    @property
    def netcdf_files(self):
        """Return the wrapped netcdf files."""
        result = []
        for filename in netcdf.netcdf_filepaths():
            netcdf_file = netcdf.NetcdfFile(filename)
            # View-related adjustments/additions.
            netcdf_file.headings = netcdf_file.metadata_keys
            netcdf_file.rows = []
            for station in netcdf_file.stations:
                row = [station[key] for key in netcdf_file.metadata_keys]
                netcdf_file.rows.append(row)
            result.append(netcdf_file)
        return result

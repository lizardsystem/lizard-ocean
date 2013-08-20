# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function
import os

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

    # @property
    # def workspace(self):
    #     """Return workspace, but ensure our own workspace is included."""
    #     ws = super(MainView, self).workspace
    #     ws.add_workspace_item('Ocean',
    #                           'adapter_ocean',
    #                           {})
    #     # ^^^ Note: add_workspace_item() first looks whether the item is
    #     # already available before adding. So it is a good way of ensuring it
    #     # is present, without the risk of duplication.
    #     return ws
    
    def point_files(self):
        """Return workspace acceptables, ordered per netcdf file."""
        result = []
        for filename in netcdf.netcdf_filepaths():
            netcdf_file = netcdf.NetcdfFile(filename)
            name = os.path.basename(filename)[:-3]
            name = name.replace('_', ' ')
            result.append({
                'name': name,
                'workspace_acceptables': netcdf_file.workspace_acceptables})
        return result


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
            # Sample values
            netcdf_file.sample_parameter = netcdf_file.parameters[0]['name']
            netcdf_file.sample_station_index = 0
            netcdf_file.sample_values = netcdf_file.values(
                netcdf_file.parameters[0]['id'], 0)
            result.append(netcdf_file)
        return result

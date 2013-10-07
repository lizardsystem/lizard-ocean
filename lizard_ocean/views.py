# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function

import os

from django.utils.translation import ugettext as _
# from django.core.urlresolvers import reverse
from django.views.generic.base import View
from django.utils import simplejson as json
from django.http import HttpResponse
from django.utils.functional import cached_property
from django.conf import settings

from lizard_map.views import MapView
from lizard_map.lizard_widgets import WorkspaceAcceptable
from lizard_ui.views import UiView

from lizard_ocean import netcdf
from lizard_ocean import raster
from lizard_ocean import ocean_data

import mapnik
from lizard_map import coordinates
from lizard_ocean.layers import FilteredOceanAdapter

# class TodoView(UiView):
#     """Simple view without a map."""
#     template_name = 'lizard_ocean/todo.html'
#     page_title = _('TODO view')

class WmsView(View):
    def get(self, request):
        # WMS standard parameters
        layers = request.GET.get('LAYERS', '')
        layers = [layer.strip() for layer in layers.split(',')]
        width = int(request.GET.get('WIDTH', '512'))
        height = int(request.GET.get('HEIGHT', '512'))
        opacity = float(request.GET.get('OPACITY', '1.0'))
        bbox = request.GET.get('BBOX', '')
        bbox = tuple([float(i.strip()) for i in bbox.split(',')])
        srs = request.GET.get('SRS', 'EPSG:3857')

        # Either a time span, or a single time can be passed
        times = request.GET.get('TIME', '')
        times = times.split('/')
        if len(times) == 2:
            time_from = dateutil.parser.parse(times[0])
            time_until = dateutil.parser.parse(times[1])
        else:
            time_from = time_until = None

        return self.serve_mapnik(request, layers, width, height, bbox, srs, opacity)

    def serve_mapnik(self, request, layers, width, height, bbox, srs, opacity):
        map = mapnik.Map(width, height)
        map.srs = coordinates.srs_to_mapnik_projection[srs]
        map.background = mapnik.Color(b'transparent')

        #from lizard_map.models import WorkspaceEditItem
        #adapkwargs = {'adapter_class': u'adapter_ocean', 'layer_arguments': {'parameter_id': u'H_simulated', 'filename': u'2013.09.08_06.00.00_EAM.Flow.HC.nc'}}
        #adap = OceanPointAdapter(WorkspaceEditItem.objects.get(pk=228), **adapkwargs)
        #layers, styles = adap.layer()

        tree = ocean_data.get_data_tree(settings.OCEAN_BASEDIR)
#        filename_parameter_map = ocean_data.get_filename_parameter_map(tree, layers)
#         print(netcdfs)
#         filename_parameter_map = {
#             '/home/ejvos/adoos/var/ocean-netcdf/2013.09.08_06.00.00_EAM.Flow.FC.nc': {
#                 'station_ids': [],
#                 'parameter_ids': ['H_meting']
#             }
#         }
        selected_nodes = ocean_data.filter_by_identifier(tree, layers)
        locations = ocean_data.get_locations(selected_nodes)
        adapter = FilteredOceanAdapter(locations)
        layers, styles = adapter.point_layer()
        for layer in layers:
            map.layers.append(layer)
        for name in styles:
            map.append_style(name, styles[name])
        map.zoom_to_box(mapnik.Envelope(*bbox))
        img = mapnik.Image(width, height)
        mapnik.render(map, img)
        response = HttpResponse(img.tostring(b'png'), content_type='image/png')
        return response

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

    def raster_sets(self):
        """Return workspace acceptables, ordered per directory containing png files."""
        result = []
        for raster_set in raster.raster_sets():
            adapter_layer_json = json.dumps(
                {
                    'raster_set_dir': raster_set.dir,
                    'custom_handler_data': {
                        'filenames': raster_set.png_filenames
                    },
                    'needs_custom_handler': True
                }
            )
            wsa = WorkspaceAcceptable(
                name=raster_set.name,
                adapter_name='adapter_ocean_raster',
                adapter_layer_json=adapter_layer_json
            )
            result.append(wsa)
        return result

    @cached_property
    def tree_json(self):
        try:
            tree = ocean_data.to_fancytree(ocean_data.get_data_tree(settings.OCEAN_BASEDIR))
        except Exception as ex:
            raise Exception(ex)
        return json.dumps(tree)

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

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
from django.contrib.gis.geos import Point
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.http import Http404

import mapnik
from dateutil.parser import parse as date_parse

from lizard_map.views import MapView
from lizard_map.views import popup_json
from lizard_ui.views import UiView

from lizard_ocean import netcdf
from lizard_ocean import raster
from lizard_ocean import ocean_data

from lizard_map import coordinates
from lizard_ocean.layers import FilteredOceanAdapter

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
        filter_by_type = request.GET.get('FILTERBYTYPE', 'locations')

        return self.serve_mapnik(request, layers, filter_by_type, width, height, bbox, srs, opacity)

    def serve_mapnik(self, request, layers, filter_by_type, width, height, bbox, srs, opacity):
        map = mapnik.Map(width, height)
        map.srs = coordinates.srs_to_mapnik_projection[srs]
        map.background = mapnik.Color(b'transparent')
        tree = ocean_data.Tree()

        selected_nodes = tree.filter_by_identifier(layers)
        if filter_by_type == 'locations':
            filtered_nodes = selected_nodes.filter_by_property('is_location')
        elif filter_by_type == 'rasters':
            filtered_nodes = selected_nodes.filter_by_property('is_raster')
        else:
            filtered_nodes = selected_nodes
        adapter = FilteredOceanAdapter(filtered_nodes)

        layers, styles = adapter.layers()
        for layer in layers:
            map.layers.append(layer)
        for name in styles:
            map.append_style(name, styles[name])
        map.zoom_to_box(mapnik.Envelope(*bbox))
        img = mapnik.Image(width, height)
        mapnik.render(map, img)
        response = HttpResponse(img.tostring(b'png'), content_type='image/png')
        return response

class RastersetInfoView(View):
    @method_decorator(never_cache)
    def get(self, request):
        identifiers = request.GET.get('identifiers', '')
        identifiers = [identifier.strip() for identifier in identifiers.split(',')]

        rasterset_info = []

        tree = ocean_data.Tree()
        selected_nodes = tree.filter_by_identifier(identifiers)
        rastersets = selected_nodes.filter_by_property('is_rasterset').get()

        for rasterset in rastersets:
            info = {
                'name': rasterset.name,
                'identifier': rasterset.identifier,
                'children': [
                    {
                        'name': raster.name,
                        'identifier': raster.identifier,
                    }
                    for raster in rasterset.children
                ],
            }
            rasterset_info.append(info)

        rasterset_identifiers = [rasterset.identifier for rasterset in rastersets]

        # HACK: Trick to also pull in individual selected rasters.
        rasters = selected_nodes.filter_by_property('is_raster').get()
        for raster in rasters:
            # Skip rasters which already have been added as part of a rasterset.
            if raster.parent in rasterset_identifiers:
                continue
            # Find out if rasterset is already present.
            rasterset = None
            for info in rasterset_info:
                if info['identifier'] == raster.parent:
                    rasterset = info
                    break
            if not rasterset:
                rasterset_node = tree.node_dict[raster.parent]
                info = {
                    'name': rasterset_node.name,
                    'identifier': rasterset_node.identifier,
                    'children': []
                }
                rasterset_info.append(info)
                rasterset = info
            rasterset['children'].append({
                'name': raster.name,
                'identifier': raster.identifier,
            })

        response = HttpResponse(json.dumps(rasterset_info), content_type='application/json')
        return response

class MapClickView(View):
    @method_decorator(never_cache)
    def get(self, request):
        identifiers = request.GET.get('identifiers', '')
        identifiers = [identifier.strip() for identifier in identifiers.split(',')]
        lon = float(request.GET['lon'])
        lat = float(request.GET['lat'])
        srs = request.GET.get('srs', 'EPSG:3857')
        srid = int(srs.lower().lstrip('epsg:'))
        bbox = request.GET['bbox']
        bbox = tuple([float(i.strip()) for i in bbox.split(',')])
        width = float(request.GET['width'])
        height = float(request.GET['height'])
        resolution = request.GET.get('resolution')
        if resolution: resolution = float(resolution)
        x = request.GET.get('x')
        y = request.GET.get('y')

        tree = ocean_data.Tree()
        selected_nodes = tree.filter_by_identifier(identifiers)

        point = Point((lon, lat), srid=srid)

        adapter = FilteredOceanAdapter(selected_nodes)
        search_results = adapter.search(point, srid=srid, bbox=bbox, width=width, height=height, resolution=resolution)
        if not search_results:
            raise Http404

        if len(search_results) > 8:
            search_results = search_results[:8]

        # Group by parameter. Kind of a hack.
        params_map = {}
        for search_result in search_results:
            location = search_result['location']
            parameter = tree.node_dict[location.parent]
            if parameter.parameter_id not in params_map:
                params_map[parameter.parameter_id] = {
                    'identifiers': [],
                    'names': [],
                }
            params_map[parameter.parameter_id]['identifiers'].append(location.identifier)
            params_map[parameter.parameter_id]['names'].append(parameter.parameter_name)

        response = HttpResponse(json.dumps(params_map), content_type='application/json')
        return response

class GraphView(View):
    format = 'flot'

    @method_decorator(never_cache)
    def get(self, request):
        identifiers = request.GET['identifiers']
        identifiers = [identifier.strip() for identifier in identifiers.split(',')]
        start_date = date_parse(request.GET['dt_start'])
        end_date = date_parse(request.GET['dt_end'])

        tree = ocean_data.Tree()
        selected_nodes = tree.filter_by_identifier(identifiers)
        adapter = FilteredOceanAdapter(selected_nodes, tree=tree)

        if self.format == 'flot':
            response_dict = adapter.flot_graph_data(start_date, end_date)
            response = HttpResponse(json.dumps(response_dict), content_type='application/json')
            return response
        elif self.format == 'png':
            width = float(request.GET['width'])
            height = float(request.GET['height'])
            bytes = adapter.image(start_date, end_date, width=width, height=height)
            response = HttpResponse(bytes, content_type='image/png')
            return response

class MainView(MapView):
    """Main view of the application."""
    template_name = 'lizard_ocean/main.html'
    # page_title = _('')

    @cached_property
    def tree_json(self):
        try:
            tree = ocean_data.Tree()
            tree = ocean_data.to_fancytree(tree.get())
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

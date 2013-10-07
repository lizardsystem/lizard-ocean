# Note: no __unicode__ stuff at the top due to mapnik. Perhaps 2.2
# works, though.
import datetime
import math
import os
import logging

from django.utils.functional import cached_property
from django.conf import settings
from django.http import Http404
from lizard_map import coordinates
from lizard_map.exceptions import WorkspaceItemError
from lizard_map import workspace
from lizard_map.adapter import FlotGraph, Graph
from lizard_map.models import ICON_ORIGINALS
from lizard_map.symbol_manager import SymbolManager
import mapnik
import pytz

from lizard_ocean import netcdf
from lizard_ocean import ocean_data


logger = logging.getLogger(__name__)

ICON_STYLE = {'icon': 'buoy.png',  # Buoy.png is available in lizard-map.
              'mask': ('buoy_mask.png', ),
              'color': (1, 1, 0, 0)}


def get_pointsymbolizer_args(path, format='png', width=16, height=16):
    '''
    Wrapper to support both mapnik 0.7 and mapnik 2.x.

    For example, in mapnik 2.x the constructor of PointSymbolizer
    needs the file path wrapped in a PathExpression.
    '''
    if hasattr(mapnik, 'PathExpression'):
        return (mapnik.PathExpression(path),)
    return (path, format, width, height)

def distance(x1, y1, x2, y2):
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

class FilteredOceanAdapter(object):
    def __init__(self, nodes):
        self.nodes = nodes

    def layers(self):
        layers = []
        styles = {}

        # Draw locations to a single fixed layer.
        locations = [node for node in self.nodes if node['is_location']]
        if locations:
            point_layer = mapnik.Layer(b'ocean locations', coordinates.WGS84)
            point_layer.datasource = mapnik.MemoryDatasource()

            s_name_1 = b'ocean_location_style'
            styles[s_name_1] = self._get_location_style()
            point_layer.styles.append(s_name_1)

            context = mapnik.Context()
            for i, location in enumerate(locations):
                f = mapnik.Feature(context, i)
                f['Name'] = str(location['name'])
                # TODO: might want to use something like this, instead of WKT. But how?
                #f.add_geometry(Point(station['x'], station['y']))
                f.add_geometries_from_wkt('POINT({} {})'.format(location['location_x'], location['location_y']))
                point_layer.datasource.add_feature(f)
    
            layers.append(point_layer)

        rasters = [node for node in self.nodes if node['is_raster']]
        if rasters:
            s_name_2 = b'ocean_raster_style'
            styles[s_name_2] = self._get_raster_style()

            # Create a raster layer
            for raster in rasters:
                file = raster['path']
                layer_name = raster['name']
                raster_ds = mapnik.Gdal(file=str(file), shared=True)
                layer = mapnik.Layer(str(layer_name), coordinates.WGS84)
                layer.datasource = raster_ds
                layer.styles.append(s_name_2)
                layers.append(layer)

        return layers, styles

    def search(self, google_x, google_y, radius=None):
        """Return list of dict {'distance': <float>, 'timeserie':
        <timeserie>} of closest points that match x, y, radius.

        """
        result = []
        for location in self.nodes:
            x, y = coordinates.wgs84_to_google(
                location['location_x'],
                location['location_y'])
            dist = distance(google_x, google_y, x, y)
            if dist < radius:
                result.append(
                    {'distance': dist,
                     'name': location['name'],
                     'shortname': location['name'],
                     'identifier': {'station_id': location['location_id']},
                     'google_coords': (x, y),
                     'object': None})
        result.sort(key=lambda item: item['distance'])
        if result:
            return result[:1]
        else:
            return []

    def _get_location_style(self):
        symbol_manager = SymbolManager(
            ICON_ORIGINALS,
            os.path.join(settings.MEDIA_ROOT, 'generated_icons'))
        output_filename = symbol_manager.get_symbol_transformed(
            ICON_STYLE['icon'], **ICON_STYLE)
        output_filename_abs = os.path.join(
            settings.MEDIA_ROOT, 'generated_icons', output_filename)
        # use filename in mapnik pointsymbolizer
        point_looks = mapnik.PointSymbolizer(*get_pointsymbolizer_args(output_filename_abs))
        point_looks.allow_overlap = True
        layout_rule = mapnik.Rule()
        layout_rule.symbols.append(point_looks)
        point_style = mapnik.Style()
        point_style.rules.append(layout_rule)
        return point_style

    def _get_raster_style(self):
        s = mapnik.Style()
        r = mapnik.Rule()
        rs = mapnik.RasterSymbolizer()
        rs.scaling = mapnik.scaling_method.BILINEAR8
        r.symbols.append(rs)
        s.rules.append(r)
        return s

'''
class OceanPointAdapter(workspace.WorkspaceItemAdapter):
    # Note: bit of copy/paste from lizard-fewsjdbc's adapter.

    def __init__(self, *args, **kwargs):
        #import pdb; pdb.set_trace()
        super(OceanPointAdapter, self).__init__(*args, **kwargs)
        if not 'filename' in self.layer_arguments:
            raise WorkspaceItemError("Key 'filename' not found")
        self.filename = os.path.join(settings.OCEAN_NETCDF_BASEDIR, 
                                     self.layer_arguments['filename'])
        self.parameter_id = self.layer_arguments['parameter_id']
        #self.parameter_name = ''
        #self.parameter_unit = ''
        #for parameter in self.netcdf_file.parameters:
        #    if parameter['id'] == self.parameter_id:
        #        self.parameter_unit= parameter['unit']
        #        self.parameter_name= parameter['name']
        filename_parameter_map = {
            self.filename: {
                'station_ids': [],
                'parameter_ids': [self.parameter_id],
            }
        }
        self.filtered_adapter = FilteredOceanAdapter(filename_parameter_map)

    def symbol_url(self, identifier=None, start_date=None, end_date=None,
                   icon_style=None):
        """Return symbol for identifier."""
        sm = SymbolManager(
            ICON_ORIGINALS, 
            os.path.join(settings.MEDIA_ROOT, 'generated_icons'))
        if icon_style is None:
            icon_style = ICON_STYLE
        output_filename = sm.get_symbol_transformed(icon_style['icon'],
                                                    **icon_style)
        return settings.MEDIA_URL + 'generated_icons/' + output_filename

    def layer(self, layer_ids=None, webcolor=None, request=None):
        """Return layer and styles that render points.

        """
        return self.filtered_adapter.point_layer()

    def search(self, google_x, google_y, radius=None):
        """Return list of dict {'distance': <float>, 'timeserie':
        <timeserie>} of closest points that match x, y, radius.

        """
        results = self.filtered_adapter.search(google_x, google_y, radius)
        for result in results:
            result.update({'workspace_item': self.workspace_item})
        return results

    def location(self, station_id, layout=None):
        """Return location dict.
        """
        result = self.filtered_adapter.search_station(station_id)
        result.update({'workspace_item': self.workspace_item})
        return result

    def html(self, *args, **kwargs):
        return super(OceanPointAdapter, self).html_default(*args, **kwargs)

    def flot_graph_data(self, identifiers, start_date, end_date, layout_extra=None, raise_404_if_empty=False):
        return self._render_graph(identifiers, start_date, end_date, layout_extra=layout_extra, raise_404_if_empty=raise_404_if_empty, GraphClass=FlotGraph)

    def image(self, identifiers, start_date, end_date, width=380.0, height=250.0, layout_extra=None, raise_404_if_empty=False):
        return self._render_graph(identifiers, start_date, end_date, width=width, height=height, layout_extra=layout_extra, raise_404_if_empty=raise_404_if_empty, GraphClass=Graph)

    def _render_graph(
        self,
        identifiers,
        start_date,
        end_date,
        layout_extra=None,
        raise_404_if_empty=False,
        GraphClass=FlotGraph,
        **extra_params
    ):
        """
        Visualize timeseries in a graph.

        Legend is always drawn.

        New: this is now a more generalized version of image(), to support
        FlotGraph.

        """
        today = datetime.datetime.now()
        graph = GraphClass(start_date, end_date, today=today,
                           tz=pytz.timezone(settings.TIME_ZONE),
                           **extra_params)
        graph.axes.grid(True)
        graph.axes.set_ylabel('{} ({})'.format(self.parameter_name,
                                               self.parameter_unit))

        title = None
        y_min, y_max = None, None

        is_empty = True
        for identifier in identifiers:
            location = self.location(**identifier)
            station_index = location['object']['station_index']
            # Plot data if available.
            pairs = self.netcdf_file.time_value_pairs(self.parameter_id, 
                                                      station_index)
            pairs = [(date, value) for date, value in pairs
                     if start_date < date < end_date]
            dates = [date for date, value in pairs]
            values = [value for date, value in pairs]
            if values:
                graph.axes.plot(dates, values,
                                lw=1,
                                label=location['object']['name'])

        if is_empty and raise_404_if_empty:
            raise Http404

        # Originally legend was only turned on if layout.get('legend')
        # was true. However, as far as I can see there is no way for
        # that to become set anymore. Since a legend should always be
        # drawn, we simply put the following:
        graph.legend()

        # If there is data, don't draw a frame around the legend
        if graph.axes.legend_ is not None:
            graph.axes.legend_.draw_frame(False)
        else:
            # TODO: If there isn't, draw a message. Give a hint that
            # using another time period might help.
            pass

        # Extra layout parameters. From lizard-fewsunblobbed.
        y_min_manual = y_min is not None
        y_max_manual = y_max is not None
        if y_min is None:
            y_min, _ = graph.axes.get_ylim()
        if y_max is None:
            _, y_max = graph.axes.get_ylim()

        if title:
            graph.suptitle(title)

        graph.set_ylim(y_min, y_max, y_min_manual, y_max_manual)

        graph.add_today()
        return graph.render()

    def values(self, identifier, start_date, end_date):
        location = self.location(**identifier)
        station_index = location['object']['station_index']
        # Plot data if available.
        pairs = self.netcdf_file.time_value_pairs(self.parameter_id, 
                                                  station_index)
        pairs = [(date, value) for date, value in pairs
                 if start_date < date < end_date]
        return [{'value': value, 
                 'datetime': date, 
                 'unit': self.parameter_unit}
                for date, value in pairs]


class OceanRasterAdapter(workspace.WorkspaceItemAdapter):
    """Registered as adapter_ocean_raster"""

    def __init__(self, *args, **kwargs):
        super(OceanRasterAdapter, self).__init__(*args, **kwargs)

        if not 'raster_set_dir' in self.layer_arguments:
            raise WorkspaceItemError("Key 'raster_set_dir' not found")
        self.raster_set_dir = self.layer_arguments['raster_set_dir']

    def search(self, google_x, google_y, radius=None):
        return []

    def layer(self, layer_ids=None, request=None):
        filename = request.GET.get('FILENAME')
        fullpath = os.path.join(self.raster_set_dir, filename)

        # Simple security check. Perhaps too simple?
        if not fullpath.startswith(settings.OCEAN_RASTER_BASEDIR):
            raise WorkspaceItemError('Mismatch beween settings.OCEAN_RASTER_BASEDIR and supplied FILENAME.')

        layers = []
        styles = {}

        STYLE_NAME = b'ocean_raster_style'

        # Create a default style
        s = mapnik.Style()
        r = mapnik.Rule()
        rs = mapnik.RasterSymbolizer()
        rs.scaling = mapnik.scaling_method.BILINEAR8
        r.symbols.append(rs)
        s.rules.append(r)
        styles[STYLE_NAME] = s

        # Create a raster layer
        raster = mapnik.Gdal(base=str(self.raster_set_dir), file=str(filename), shared=True)
        layer = mapnik.Layer(b'ocean_raster_layer', coordinates.WGS84)
        layer.datasource = raster
        layer.styles.append(STYLE_NAME)
        layers.append(layer)

        return layers, styles

    def location(self, identifier, region_name, layout=None):
        return None

    def image(self, identifiers=None, start_date=None, end_date=None,
              width=None, height=None, layout_extra=None):
        return None

    def flot_graph_data(
        self, identifiers, start_date, end_date, layout_extra=None,
        raise_404_if_empty=False
    ):
        return None

    def values(self, identifier, start_date, end_date):
        return None

    def html(self, identifiers=None, layout_options=None):
        return None

    def legend(self, updates=None):
        return None
'''

def apply_world_file(basedir, filename, layer):
    '''
    Find a matching worldfile for given file. If found, update the Mapnik layer
    with the coordinates in the worldfile.

    0.000085830078125  (size of pixel in x direction)                            =(east-west)/image width
    0.000000000000     (rotation term for row)
    0.000000000000     (rotation term for column)
    -0.00006612890625  (size of pixel in y direction)                            =-(north-south)/image height
    -106.54541         (x coordinate of centre of upper left pixel in map units) =west
    39.622615          (y coordinate of centre of upper left pixel in map units) =north
    '''

    filename_noext, ext = os.path.splitext(filename)
    if ext:
        ext_map = {
            '.png': '.pngw',
            '.tiff': '.tfw',
        }
        ext_worldfile = ext_map.get(ext)
        if ext_worldfile:
            filename_worldfile = '{}{}'.format(filename_noext, ext_worldfile)
            path_worldfile = os.path.join(basedir, filename_worldfile)
            if os.path.isfile(path_worldfile):
                with open(path_worldfile, 'r') as fd:
                    lines = [line.strip() for line in fd]
                if len(lines) == 6:
                    print lines
                    size_x, rot_row, rot_col, size_y, x, y = lines

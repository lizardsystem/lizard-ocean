# Note: no __unicode__ stuff at the top due to mapnik. Perhaps 2.2
# works, though.
import os

from django.conf import settings
from lizard_map import coordinates
from lizard_map import workspace
from lizard_map.models import ICON_ORIGINALS
from lizard_map.symbol_manager import SymbolManager
import mapnik

from lizard_ocean import netcdf


ICON_STYLE = {'icon': 'buoy.png',  # Buoy.png is available in lizard-map.
              'mask': ('buoy_mask.png', ),
              'color': (1, 1, 0, 0)}


class OceanPointAdapter(workspace.WorkspaceItemAdapter):
    # Note: bit of copy/paste from lizard-fewsjdbc's adapter.

    def __init__(self, *args, **kwargs):
        super(OceanPointAdapter, self).__init__(*args, **kwargs)
        # self.filenames = self.layer_arguments['filenames']  
        # TODO: switch for an ID or so!!! Probably means DB objects.
        # Filename: filename without the full path, so adjust it.
        self.filenames = [os.path.join(settings.OCEAN_NETCDF_BASEDIR, 
                                       'Phase_One_dummy.nc')]
        # ^^^ dummy

    def style(self):
        """Return mapnik point style.

        (Copy/pasted from lizard-sticky).
        """
        symbol_manager = SymbolManager(
            ICON_ORIGINALS,
            os.path.join(settings.MEDIA_ROOT, 'generated_icons'))
        output_filename = symbol_manager.get_symbol_transformed(
            ICON_STYLE['icon'], **ICON_STYLE)
        output_filename_abs = os.path.join(
            settings.MEDIA_ROOT, 'generated_icons', output_filename)
        # use filename in mapnik pointsymbolizer
        point_looks = mapnik.PointSymbolizer(
            output_filename_abs, 'png', 16, 16)
        point_looks.allow_overlap = True
        layout_rule = mapnik.Rule()
        layout_rule.symbols.append(point_looks)
        point_style = mapnik.Style()
        point_style.rules.append(layout_rule)
        return point_style

    def layer(self, layer_ids=None, webcolor=None, request=None):
        """Return layer and styles that render points.

        """
        layers = []
        styles = {}
        layer = mapnik.Layer("OCEAN points layer", coordinates.WGS84)
        layer.datasource = mapnik.PointDatasource()
        # Use these coordinates to put points 'around' actual
        # coordinates, to compensate for bug #402 in mapnik.
        around = [(0.00001, 0),
                  (-0.00001, 0),
                  (0, 0.00001),
                  (0, -0.00001)]

        for filename in self.filenames:
            netcdf_file = netcdf.NetcdfFile(filename)
            for station in netcdf_file.stations:
                layer.datasource.add_point(
                    station['x'], 
                    station['y'], 
                    'Name', 
                    str(station['name']))
                for offset_x, offset_y in around:
                    layer.datasource.add_point(
                        station['x'] + offset_x, 
                        station['y'] + offset_y,
                        'Name', 
                        str(station['name']))

        # generate "unique" point style name and append to layer
        style_name = "ocean"
        styles[style_name] = self.style()
        layer.styles.append(style_name)

        layers = [layer, ]
        return layers, styles


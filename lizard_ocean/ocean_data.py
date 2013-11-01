# -*- coding: utf-8 -*-

# Futures
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import
from __future__ import division

# Python standard library
import os
import hashlib
import logging
import shutil
from hashlib import sha1
from collections import namedtuple
try:
    import cPickle as pickle
except ImportError:
    import pickle

# Django
from django.conf import settings
from django.core.cache import cache

# Third party modules
from recordtype import recordtype

# Our own module
from lizard_ocean import netcdf
from lizard_ocean import raster

logger = logging.getLogger(__name__)

# Define a class we use to store a tree representing the datasets available
# on the disk. We use recordtype objects, which are more efficient to serialize.
Node = recordtype('Node', """
    path, identifier, name, children, parent,
    is_rasterset, is_raster, is_rasterset_legend, is_netcdf, is_worldfile,
    is_parameter, parameter_id, parameter_name, parameter_unit,
    is_location, location_id, location_x, location_y, location_index
""")

def make_node(path, name, parent_node):
    '''Return a skeleton node instance for use in the data tree.'''
    # Just store the first 8 characters of the hash, for efficiency.
    identifier = hashlib.md5(path).hexdigest()[:8]
    return Node(
        path, identifier, name, None, parent_node,
        False, False, False, False, False,
        False, None, None, None,
        False, None, None, None, None
    )

def get_netcdf_parameters_as_nodes(netcdf_path, parent_node):
    '''Read parameters and locations from a NetCDF file, and return them as data tree nodes.'''
    nodes = []
    netcdf_file = netcdf.NetcdfFile(netcdf_path)
    stations = netcdf_file.stations()
    for parameter in netcdf_file.parameters():
        # Make up a unique path for the parameter.
        path = '{}/{}'.format(netcdf_path, parameter['id'])
        # Prettify parameter name.
        parameter_name = parameter['name'].replace('_', ' ')
        node = make_node(path, parameter_name, parent_node)

        children = []
        # Add all locations under each parameter. This isn't very efficient when
        # all locations have data for all parameters.
        for location in locations:
            # Make up a unique path for the parameter and location combination.
            child_path = '{}/{}/{}'.format(path, parameter['id'], location['id'])
            # Prettify location name.
            location_name = location['name'].lstrip('_')
            # Store location data in the node.
            child_node = make_node(child_path, location_name, node)
            child_node.is_location = True
            child_node.location_id = location['id']
            child_node.location_x = location['x']
            child_node.location_y = location['y']
            child_node.location_index = location['index']
            children.append(child_node)

        # Sort by location name.
        children.sort(key=lambda item: item.name)

        # Store parameter data in the node.
        node.is_parameter = True
        node.parameter_id = parameter['id']
        node.parameter_name = parameter_name
        node.parameter_unit = parameter['unit']
        node.children = children
        nodes.append(node)
    netcdf_file.close()

    # Sort by parameter name.
    nodes.sort(key=lambda item: item.name)

    return nodes

def fixup_missing_worldfile_nodes(nodes):
    '''
    GDAL wants a matching worldfile (.pngw) for each georeferenced raster (.png).
    However, the data is supplied by Deltares with only a single worldfile per directory.
    In this method, we clone this worldfile to match the filename of each raster.
    '''
    for rasterset in filter_by_property(nodes, 'is_rasterset'):
        rasters = filter_by_property(rasterset.children, 'is_raster')
        worldfiles = filter_by_property(rasterset.children, 'is_worldfile')
        if len(worldfiles) == 1 and len(rasters) != 1:
            pngw_src = worldfiles[0].path
            for raster in rasters:
                pngw_dst = os.path.splitext(raster.path)[0] + '.pngw'
                if not os.path.exists(pngw_dst):
                    logger.info('creating a png worldfile %s', pngw_dst)
                    try:
                        shutil.copy(pngw_src, pngw_dst)
                    except:
                        logger.exception('error while copying png worldfile')
                        pass

def get_data_tree(directory, level=0, parent_node=None):
    '''
    Crawl a nested directory structure and search for lizard-ocean compatible
    data files (NetCDF, PNG). Returns a nested list representation of it.
    '''
    if level > 20:
        raise Exception('Too much recursion in "{}"'.format(directory))

    mtime = os.path.getmtime(directory)
    cache_key = '{}:{}'.format(directory, mtime)
    nodes = cache.get(cache_key)

    if nodes is None:
        nodes = []
        for fn in sorted(os.listdir(directory)):
            path = os.path.join(directory, fn)
            bn, ext = os.path.splitext(fn)
            ext = ext.lower()
            bn_lower = bn.lower()
            # Prettify file name.
            name = bn.replace('_', ' ')
            node = make_node(path, name, parent_node)
            if os.path.isdir(path):
                # Recurse through subdirectories.
                node.children = get_data_tree(path, level + 1, node)
            elif os.path.isfile(path):
                if ext == '.png' and parent_node:
                    if not parent_node.is_rasterset:
                        parent_node.is_rasterset = True
                    if 'legend' in bn_lower:
                        node.is_rasterset_legend = True
                    else:
                        node.is_raster = True
                elif ext == '.pngw':
                    node.is_worldfile = True
                elif ext == '.nc':
                    node.is_netcdf = True
                    node.children = get_netcdf_parameters_as_nodes(path, node)
                else:
                    node = None
            else:
                node = None

            if node:
                nodes.append(node)

        # Grab this moment to fix the worldfiles.
        fixup_missing_worldfile_nodes(nodes)

        logger.debug('get_data_tree: cache MISS %s %s %s', directory, mtime, len(pickle.dumps(nodes)))
        cache.set(cache_key, nodes, 300)
    else:
        logger.debug('get_data_tree: cache hit')

    return nodes

def flatten_nodes(nodes):
    '''Flatten all nested nodes in a tree and return them as a list.'''
    result = []
    for node in nodes:
        result.append(node)
        if node.children:
            result += flatten_nodes(node.children)
    return result

def get_node_dict(nodes):
    '''Build a dict of tree nodes, using their identifier as a key.'''
    nodes_flat = flatten_nodes(nodes)
    return dict([(node.identifier, node) for node in nodes_flat])

def to_fancytree(nodes):
    '''
    Convert an Ocean data tree to a jQuery Fancytree compatible format.
    You can serialize this to JSON and serve it to Fancytree.
    '''
    result = []
    for node in nodes:
        folder = node.children is not None
        fancy_node = {
            'title': node.name,
            'identifier': node.identifier,
            'folder': folder,
        }
        if folder:
            # Recurse
            fancy_node['children'] = to_fancytree(node.children)

        do_add_node = True
        if node.is_raster:
            fancy_node['iconclass'] = 'ui-icon ui-icon-document'
        elif node.is_rasterset:
            fancy_node['iconclass'] = 'ui-icon ui-icon-video'
        elif node.is_netcdf:
            fancy_node['iconclass'] = 'ui-icon ui-icon-copy'
        elif node.is_parameter:
            fancy_node['iconclass'] = 'ui-icon ui-icon-image'
        elif node.is_location:
            fancy_node['iconclass'] = 'ui-icon ui-icon-pin-s'
        elif node.is_worldfile:
            do_add_node = False
        elif node.is_rasterset_legend:
            do_add_node = False
        else:
            # Node is probably the root node.
            pass

        if do_add_node:
            result.append(fancy_node)
    return result

def filter_by_identifier(node_dict, nodes, identifiers):
    '''Filters the tree by given identifiers. Does not modify passed list.'''
    nodes = [node_dict[identifier] for identifier in identifiers if identifier in node_dict]
    return nodes

def filter_by_property(nodes, property):
    '''Find out nodes in the passed set of nodes by property, recursively. Does not modify passed list.'''
    result = []
    for node in nodes:
        if getattr(node, property):
            result.append(node)
        if node.children:
            result += filter_by_property(node.children, property)
    return result

class Tree(object):
    '''Represents the tree of data files on the disk.'''
    def __init__(self, directory=None):
        if directory is None:
            directory = settings.OCEAN_BASEDIR

        self.tree = get_data_tree(directory)
        self.node_dict = get_node_dict(self.tree)

    def filter_by_identifier(self, identifiers):
        return NodeList(self, self.tree[:]).filter_by_identifier(identifiers)

    def filter_by_property(self, property):
        return NodeList(self, self.tree[:]).filter_by_property(property)

    def get(self):
        return self.tree

class NodeList(object):
    '''
    Represents a subset of the data tree, like a Django QuerySet.
    TODO: might be able to merge this class with Tree.
    '''
    def __init__(self, tree, nodes):
        self.tree = tree
        self.nodes = nodes

    def filter_by_identifier(self, identifiers):
        return NodeList(self.tree, filter_by_identifier(self.tree.node_dict, self.nodes[:], identifiers))

    def filter_by_property(self, property):
        return NodeList(self.tree, filter_by_property(self.nodes[:], property))

    def get(self):
        return self.nodes

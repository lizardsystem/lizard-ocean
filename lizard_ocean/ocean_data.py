# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import
from __future__ import division

import os
import hashlib
import logging
from hashlib import sha1
from collections import namedtuple
import cPickle as pickle

from recordtype import recordtype
from django.conf import settings
from django.core.cache import cache

from lizard_ocean import netcdf
from lizard_ocean import raster

logger = logging.getLogger(__name__)

Node = recordtype('Node', """
    path, identifier, name, children, parent,
    is_rasterset, is_raster, is_netcdf,
    is_parameter, parameter_id, parameter_name, parameter_unit,
    is_location, location_id, location_x, location_y, location_index
""")

def make_node(path, name, parent_node):
    '''Return a skeleton node instance for use in the data tree.'''
    identifier = hashlib.md5(path).hexdigest()[:8]
    return Node(
        path, identifier, name, None, parent_node.identifier if parent_node else None,
        False, False, False,
        False, None, None, None,
        False, None, None, None, None
    )

def get_netcdf_parameters_as_nodes(netcdf_path, parent_node):
    '''Read parameters from a NetCDF file and return them as data tree nodes.'''
    nodes = []
    netcdf_file = netcdf.NetcdfFile(netcdf_path)
    stations = netcdf_file.stations()
    for parameter in netcdf_file.parameters():
        path = '{}/{}'.format(netcdf_path, parameter['id'])
        node = make_node(path, parameter['name'], parent_node)

        children = []
        for station in stations:
            child_path = '{}/{}/{}'.format(path, parameter['id'], station['id'])
            child_node = make_node(child_path, station['name'], node)
            child_node.is_location = True
            child_node.location_id = station['id']
            child_node.location_x = station['x']
            child_node.location_y = station['y']
            child_node.location_index = station['index']
            children.append(child_node)

        node.is_parameter = True
        node.parameter_id = parameter['id']
        node.parameter_name = parameter['name']
        node.parameter_unit = parameter['unit']
        node.children = children
        nodes.append(node)
    netcdf_file.close()
    return nodes

def get_data_tree(dir, level=0, parent_node=None):
    '''
    Crawl a nested directory structure and search for lizard-ocean compatible
    data files (NetCDF, PNG). Returns a nested list representation of it.
    '''
    if level > 20:
        raise Exception('Too much recursion in "{}"'.format(dir))

    mtime = os.path.getmtime(dir)
    cache_key = '{}:{}'.format(dir, mtime)
    nodes = cache.get(cache_key)

    if nodes is None:
        nodes = []
        for fn in sorted(os.listdir(dir)):
            path = os.path.join(dir, fn)
            bn, ext = os.path.splitext(fn)
            node = make_node(path, fn, parent_node)
            if os.path.isdir(path):
                node.children = get_data_tree(path, level + 1, node)
            elif os.path.isfile(path):
                if ext == '.png' and parent_node:
                    if not parent_node.is_rasterset:
                        parent_node.is_rasterset = True
                    node.is_raster = True
                elif ext == '.nc':
                    node.is_netcdf = True
                    node.children = get_netcdf_parameters_as_nodes(path, node)
                else:
                    node = None
            else:
                node = None

            if node:
                nodes.append(node)
        logger.debug('get_data_tree: cache MISS %s %s %s', dir, mtime, len(pickle.dumps(nodes)))
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
    '''Build a dict of all tree nodes, using their identifier as a key.'''
    nodes_flat = flatten_nodes(nodes)
    return dict([(node.identifier, node) for node in nodes_flat])

def to_fancytree(nodes):
    '''Convert an Ocean data tree to a Fancytree compatible format.'''
    result = []
    for node in nodes:
        folder = node.children is not None
        fancy_node = {
            'title': node.name,
            'identifier': node.identifier,
            'folder': folder,
        }
        if folder:
            fancy_node['children'] = to_fancytree(node.children)
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
        result.append(fancy_node)
    return result

def filter_by_identifier(nodes, identifiers):
    '''Filters the tree by given identifiers.'''
    node_dict = get_node_dict(nodes)
    nodes = [node_dict[identifier] for identifier in identifiers if identifier in node_dict]
    return nodes

def filter_by_property(nodes, property):
    '''Find out nodes in the passed set of nodes by property, recursively.'''
    result = []
    for node in nodes:
        if getattr(node, property):
            result.append(node)
        if node.children:
            result += filter_by_property(node.children, property)
    return result

class Tree(object):
    def __init__(self, dir=None):
        if dir is None:
            dir = settings.OCEAN_BASEDIR

        self.tree = get_data_tree(settings.OCEAN_BASEDIR)
        self.node_dict = get_node_dict(self.tree)

    def filter_by_identifier(self, identifiers):
        return NodeList(self.tree[:]).filter_by_identifier(identifiers)

    def filter_by_property(self, property):
        return NodeList(self.tree[:]).filter_by_property(property)

    def get(self):
        return self.tree

class NodeList(object):
    def __init__(self, nodes):
        self.nodes = nodes

    def filter_by_identifier(self, identifiers):
        return NodeList(filter_by_identifier(self.nodes, identifiers))

    def filter_by_property(self, property):
        return NodeList(filter_by_property(self.nodes, property))

    def get(self):
        return self.nodes

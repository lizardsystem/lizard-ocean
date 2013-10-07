# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import
from __future__ import division

import os
import hashlib

from django.utils import simplejson as json

from lizard_ocean import netcdf
from lizard_ocean import raster

def make_node(path, name, parent_node):
    '''Return a skeleton node instance for use in the data tree.'''
    identifier = hashlib.md5(path).hexdigest()[:10]
    return {
        'path': path,
        'name': name,
        'identifier': identifier,
        'children': None,
        'parent': parent_node['identifier'] if parent_node else None,
        'is_rasterset': False,
        'is_rasterset_item': False,
        'is_netcdf': False,
        'is_netcdf_parameter': False,
        'parameter_id': None,
        'is_netcdf_location': False,
        'location_id': False,
        'location_x': None,
        'location_y': None,
    }

def get_netcdf_parameters_as_nodes(netcdf_path, parent_node):
    '''Read parameters from a NetCDF file and return them as data tree nodes.'''
    nodes = []
    netcdf_file = netcdf.NetcdfFile(netcdf_path)
    stations = netcdf_file.stations
    for parameter in netcdf_file.parameters:
        path = '{}/{}'.format(netcdf_path, parameter['id'])
        node = make_node(path, parameter['name'], parent_node)

        children = []
        for station in stations:
            child_path = '{}/{}'.format(path, station['id'])
            child_node = make_node(child_path, station['name'], node)
            child_node.update({
                'is_netcdf_location': True,
                'station_id': station['id'],
                'location_x': station['x'],
                'location_y': station['y'],
            })
            children.append(child_node)

        node.update({
            'is_netcdf_parameter': True,
            'parameter_id': parameter['id'],
            'children': children,
        })
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
    nodes = []
    for fn in os.listdir(dir):
        path = os.path.join(dir, fn)
        bn, ext = os.path.splitext(fn)
        node = make_node(path, fn, parent_node)
        if os.path.isdir(path):
            node.update({
                'children': get_data_tree(path, level + 1, node)
            })
        elif os.path.isfile(path):
            if ext == '.png' and parent_node:
                if not parent_node['is_rasterset']:
                    parent_node['is_rasterset'] = True
                node.update({
                    'is_rasterset_item': True,
                })
            elif ext == '.nc':
                node.update({
                    'is_netcdf': True,
                    'children': get_netcdf_parameters_as_nodes(path, node),
                })
            else:
                node = None
        else:
            node = None

        if node:
            nodes.append(node)
    return nodes

def flatten_data_tree(tree):
    '''Flatten all nested nodes in a tree and return them as a list.'''
    result = []
    for node in tree:
        result.append(node)
        if node['children']:
            result += flatten_data_tree(node['children'])
    return result

def get_data_tree_dict(tree):
    '''Build a dict of all tree nodes, using their identifier as a key.'''
    tree_flat = flatten_data_tree(tree)
    return dict([(node['identifier'], node) for node in tree_flat])

def to_fancytree(tree):
    '''Convert an Ocean data tree to a Fancytree compatible format.'''
    result = []
    for node in tree:
        folder = node['children'] is not None
        fancy_node = {
            'title': node['name'],
            'identifier': node['identifier'],
            'folder': folder,
        }
        if folder:
            fancy_node['children'] = to_fancytree(node['children'])
        if node['is_rasterset_item']:
            fancy_node['iconclass'] = 'ui-icon ui-icon-document'
        elif node['is_rasterset']:
            fancy_node['iconclass'] = 'ui-icon ui-icon-video'
        elif node['is_netcdf']:
            fancy_node['iconclass'] = 'ui-icon ui-icon-copy'
        elif node['is_netcdf_parameter']:
            fancy_node['iconclass'] = 'ui-icon ui-icon-image'
        elif node['is_netcdf_location']:
            fancy_node['iconclass'] = 'ui-icon ui-icon-pin-s'
        result.append(fancy_node)
    return result

def filter_by_identifier(tree, identifiers):
    '''Filters the tree by given identifiers.'''
    tree_dict = get_data_tree_dict(tree)
    nodes = [tree_dict[identifier] for identifier in identifiers if identifier in tree_dict]
    return nodes

def get_locations(nodes):
    '''Find out locations in the passed set of nodes, and their children.'''
    result = []
    for node in nodes:
        if node['is_netcdf_location']:
            result.append(node)
        if node['children']:
            result += get_locations(node['children'])
    return result

def get_filename_parameter_map(tree, identifiers):
    '''Filters the tree by given identifiers.'''
    filename_parameter_map = {}
    tree_dict = get_data_tree_dict(tree)
    nodes = [tree_dict[identifier] for identifier in identifiers if identifier in tree_dict]

    def get_or_create(path):
        if path in filename_parameter_map:
            return filename_parameter_map[path]
        else:
            item = {
                'station_ids': [],
                'parameter_ids': []
            }
            filename_parameter_map[path] = item
            return item
            
    for node in nodes:
        if node['is_netcdf_parameter']:
            parent_node = tree_dict[node['parent']]
            item = get_or_create(parent_node['path'])
            item['parameter_ids'].append(node['parameter_id'])
        else:
            item = get_or_create(node['path'])
    return filename_parameter_map

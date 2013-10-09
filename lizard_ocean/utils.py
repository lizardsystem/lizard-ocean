# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function

from django.core.cache import cache
from django.conf import settings

from hashlib import sha1
from functools import wraps
import logging

logger = logging.getLogger(__name__)

def cached_instance_method(seconds=300, ignore_cache=False):
    '''Dont use'''
    def outer_wrapper(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            instance = args[0]
            if hasattr(instance, 'cache_key'):
                # Use the cache_key property on the instance to get the right key.
                key = instance.cache_key
            else:
                key = str(f.__module__) + str(f.__name__) + str(args) + str(kwargs)
            # Try getting result from cache.
            result = cache.get(key)
            if ignore_cache or result is None:
                # Execute function.
                result = f(*args, **kwargs)
                # Cache the result.
                cache.set(key, result, seconds)
            return result
        return wrapper
    return outer_wrapper

"""This module provides caching functionality for functions.

By default, data is stored in the .pkl format. The `load_fn` and `save_fn` parameters can be used to implement a custom format.

Usage:
```
@cached(path="/tmp/cache", log_level="DEBUG", path_seperators=["a", "b", "c"], identifiers=["hardcoded_value"], instance_identifiers=["instance_attribute"])
def my_function(a, b, c):
    ...
```    
"""

import functools
import hashlib
import inspect
import logging
import os
import pickle

import pandas as pd

logger = logging.getLogger(__name__)


def search(path, key):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    return True if key in os.listdir(path) else False


class cached:
    def __init__(
        self,
        path: str = "/tmp/cache",
        disabled: bool = False,
        refresh: bool = False,
        log_level: str = "INFO",
        identifiers: list = [],
        path_seperators: list = [],
        instance_identifiers: list = [],
        instance_path_seperators: list = [],
        load_fn=pd.read_pickle,
        save_fn=pd.to_pickle,
        search_fn=search,
        propagate_kwargs: bool = False,
        name: str = None,
    ):
        """Save the result of the decorated function in a cache. Function arguments are hashed such that subsequent
        calls with the same arguments result in a cache hit

        Args:
            path: disk path to store cached objects. Defaults to "cache".
            disabled: whether or not to bypass the cache for the function call. Defaults to False.
            refresh: whether or not to bypass cache lookup to force a new cache write. Defaults to False.
            log_level: level to emit logs at. defaults to INFO
            identifiers: additional arguments that are hashed to identify a unique function call. Defaults to [].
            path_seperators: list of argument names to use as path seperators after `path`
            instance_identifiers: name of instance attributes to include in `identifiers` if `is_method` is `True`. Defaults to [].
            instance_path_seperators: name of instance attributes to include in `path_seperators` if `is_method` is `True`. Defaults to [].
            load_fn: Function to load cached data. Defaults to pd.read_pickle.
            save_fn: Function to save cached data. Defaults to pd.to_pickle.
            search_fn: Function ((path, key) -> bool) to override default search function. Defaults to os.listdir.
            propagate_kwargs: whether or not to propagate keyword arguments to the decorated function. Defaults to False.
            name: name of function or operation being cached. Defaults to None.
        """
        self.params = {
            "path": path,
            "disabled": disabled,
            "refresh": refresh,
            "log_level": log_level,
            "identifiers": identifiers.copy(),
            "path_seperators": path_seperators.copy(),
            "instance_identifiers": instance_identifiers.copy(),
            "instance_path_seperators": instance_path_seperators.copy(),
            "load_fn": load_fn,
            "save_fn": save_fn,
            "search_fn": search_fn,
            "propagate_kwargs": propagate_kwargs,
            "name": name,
        }

    def __call__(self, func):
        self.params["name"] = self.params["name"] or func.__name__

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if os.getenv("PYUTIL_DISABLE_CACHE"):
                return func(*args, **kwargs)

            all_args = sort_dict(inspect.getcallargs(func, *args, **kwargs))
            # Update params using override passed in through calling function
            params = self.get_cache_params(kwargs)
            return self.perf_cache_lookup(func, params, all_args, *args, **kwargs)

        return wrapper

    @classmethod
    def log(cls, level, *msg):
        logger.log(logging._nameToLevel[level], *msg)

    def get_cache_params(self, kwargs):
        params = {}
        for k, v in self.params.items():
            if isinstance(v, list) or isinstance(v, dict):
                params[k] = v.copy()
            else:
                params[k] = v

        if "cache_kwargs" in kwargs:
            # Support special cache_kwargs parameter in case calling function has a name clash with cache params
            params.update(kwargs["cache_kwargs"])
            if not params["propagate_kwargs"]:
                del kwargs["cache_kwargs"]

        else:
            # Since cache_kwargs was not provided, check for overrides directly in kwargs.
            # Note that params get deleted from kwargs so cache_kwargs should be used in case of
            # name conflicts
            params.update(kwargs)

            if not params["propagate_kwargs"]:
                for key in params.keys():
                    try:
                        # Delete override from function kwargs before passing to query
                        del kwargs[key]
                    except KeyError:
                        pass
        return params

    @classmethod
    def perf_cache_lookup(cls, func, params, all_args, *args, **kwargs):
        path = params["path"]
        disabled = params["disabled"]
        refresh = params["refresh"]
        log_level = params["log_level"]
        identifiers = params["identifiers"]
        path_seperators = params["path_seperators"]
        instance_identifiers = params["instance_identifiers"]
        instance_path_seperators = params["instance_path_seperators"]
        load_fn = params["load_fn"]
        save_fn = params["save_fn"]
        search_fn = params["search_fn"]
        name = params["name"]

        # Short circuit if disabled
        if disabled:
            return func(*args, **kwargs)

        # Parse identifiers and path seperators
        path_seperators = [all_args[ps] for ps in path_seperators]
        if "self" in all_args:
            instance = all_args["self"]
            identifiers.extend([getattr(instance, id) for id in instance_identifiers])
            path_seperators.extend([getattr(instance, ps) for ps in instance_path_seperators])

        # Add path seperators
        path = os.path.join(path, *path_seperators)

        # Hash arguments
        hashable = {k: v for k, v in all_args.items() if k not in params and k not in ["cache_kwargs", "self"]}
        identifiers_hashed = [hash_item(id) for id in identifiers]
        key = hash_item([hash_item(i) for i in [hashable, sorted(identifiers_hashed)]])

        # Logs will show identifiers and hashable arguments in the function call
        argument_string = (*(f"(id:{i})" for i in identifiers), *(f"{k}={v}" for k, v in hashable.items()))
        argument_string = f"({', '.join(str(arg) for arg in argument_string)})"

        # Cache lookup
        if not refresh and search_fn(path, key) is True:
            cls.log(
                log_level, f"Using cached value in call to {name}{argument_string} | key={key} ({path})"[:200] + "..."
            )
            return load_fn(os.path.join(path, key))
        else:
            data = func(*args, **kwargs)
            cls.log(
                log_level, f"Saving cached value in call to {name}{argument_string} | key={key} ({path})"[:200] + "..."
            )
            save_fn(data, os.path.join(path, key))
            return data


def hash_item(i):
    """Hash a python object by pickling and then applying MD5 to resulting bytes"""
    if isinstance(i, dict):
        return hash_dict(i)
    try:
        hash = hashlib.md5(pickle.dumps(i)).hexdigest()
    except TypeError:
        logger.warning(f"Unable to hash {i}, using hash of the object's class instead")
        hash = hashlib.md5(pickle.dumps(i.__class__)).hexdigest()
    except AttributeError:
        logger.warning(f"Unable to hash the objects class, using hash of class name instead")
        hash = hashlib.md5(pickle.dumps(i.__class__.__name__)).hexdigest()
    return hash


def hash_dict(d: dict) -> str:
    """Hash dict in order-agnostic manner by ordering keys and hashes of values"""

    # order keys and hash result
    key_hash = hash_item(list(sorted(d.keys())))

    # hash_item will call this function recursively if dict is passed
    values = [hash_item(i) for i in d.values()]

    return hash_item([key_hash, sorted(values)])


def sort_dict(d, reverse=False) -> dict:
    """Sort a dict based on keys recursively"""
    new_d = {}
    sorted_keys = sorted(d, reverse=reverse)
    for key in sorted_keys:
        if isinstance(d[key], dict):
            new_d[key] = sort_dict(d[key])
        else:
            new_d[key] = d[key]
    return new_d

"""Miscellaneous utility functions""
"""

import datetime
import itertools
import logging
import os

logger = logging.getLogger(__name__)


def make_timestamped_dir(path):
    """Create a directory with a timestamped name in the specified path"""
    time_now = datetime.datetime.now()
    date_now = time_now.date().strftime("%Y-%m-%d")
    hour_now = time_now.strftime("%H")
    minute_now = time_now.strftime("%M")
    full_log_dir = os.path.join(path, date_now, hour_now, minute_now)
    os.makedirs(full_log_dir, exist_ok=True)
    return full_log_dir


def unique_file_name(path):
    """Return a unique file name by appending _i to the path where i is the smallest integer such that the path does not exist"""
    i = 2
    while os.path.exists(path):
        path = f"{path}_{i}"
        i += 1
    return f"{path}.log"


def format_dict(dict_, ind="    ", trail="_"):
    """Return string representation of dict with correct indentation"""
    out = "{\n"
    n = max(len(str(x)) for x in dict_.keys()) if len(dict_) > 0 else 0
    for k, v in dict_.items():
        out += ind + f"{k}:".ljust(n + 2, trail)
        if isinstance(v, dict):
            out += "{ \n" + format_dict(v, ind + "    ")
        else:
            out += str(v) + "\n"

    if len(ind) > 0:
        out += "}\n"
    return out


def split_key(key, _map, delimeter="_"):
    """Given a key and a dict with keys that are strings seperated by a delimeter:
    split the key into subsets of other keys from the map which all combine to form the original key. Returns the split key as a list of keys.
    Returns (-1,) if the key cannot be split into subsets that are in the map.

    Example:
    dict contains keys: "A_B", "B_C", "C"
    split_key("A_B_C", dict) returns ["A_B", "C"]
    """
    NOT_IN_MAP = (-1,)
    ret = []
    notes = key.split(delimeter)
    n_notes = len(notes)

    good_subsets = []

    # Split the key into subsets of decreasing length
    for subset_length in range(n_notes - 1, 0, -1):
        for subset in itertools.combinations(notes, subset_length):
            s = delimeter.join(subset)
            if s in _map:
                good_subsets.append(subset)

    # Try to find the longest (subset, remainder) pair that is in the map
    for subset in good_subsets:
        remainder = delimeter.join(list(filter(lambda x: x not in subset, notes)))
        s = delimeter.join(subset)
        if remainder in _map:
            return [s, remainder]

    # Split up the remainders and find a pair recursively
    for subset in good_subsets:
        remainder = delimeter.join(list(filter(lambda x: x not in subset, notes)))
        s = delimeter.join(subset)
        partitioned_remainder = split_key(remainder, _map)
        if partitioned_remainder != NOT_IN_MAP:
            return [s, *partitioned_remainder]

    return NOT_IN_MAP

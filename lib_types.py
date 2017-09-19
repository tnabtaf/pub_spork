#!/usr/local/bin/python3
"""Defines different types of libraries and how they map to classes."""

import cul_pub
import zotero_pub

# command line argument settings
CITEULIKE_JSON = "citeulike-json"
ZOTERO_CSV = "zotero-csv"

# mapping from commmand line arg to module that handles it.

LIB_TYPE_MAPPING = {
    CITEULIKE_JSON: cul_pub,
    ZOTERO_CSV: zotero_pub,
    }

LIB_TYPES = list(LIB_TYPE_MAPPING.keys())


def get_lib_module(lib_command_line_arg):
    """Given a command line argument specifying the publication library type,
    return the module that handles it.
    """
    return LIB_TYPE_MAPPING[lib_command_line_arg]


def get_lib_types_as_text_list():
    text_list = ""
    for lib_type in LIB_TYPES[0:-1]:
        text_list += lib_type + ", "
    if text_list:
        text_list += " and "
    text_list += LIB_TYPES[-1]

    return text_list

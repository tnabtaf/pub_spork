#!/usr/local/bin/python3
"""Defines different report formats."""

import html_report
import markdown_report
import bootstrap_buttons_report
import bootstrap_cards_report

# command line argument settings
MARKDOWN = "markdown"
HTML = "html"
TSV = "tsv"
BOOTSTRAP_BUTTONS = "bootstrap-buttons"
BOOTSTRAP_CARDS = "bootstrap-cards"

# mapping from commmand line arg to module that handles it.
FORMAT_MAPPING = {
    HTML: html_report,
    MARKDOWN: markdown_report,
    BOOTSTRAP_BUTTONS: bootstrap_buttons_report,
    BOOTSTRAP_CARDS: bootstrap_cards_report
    }

FORMATS = list(FORMAT_MAPPING.keys())


def get_format_module(format_command_line_arg):
    """Given a command line argument specifying a report format type,
    return the module that generates it.
    """
    return FORMAT_MAPPING[format_command_line_arg]


def get_formats_as_text_list():
    text_list = ""
    for report_format in FORMATS[0:-1]:
        text_list += report_format + ", "
    if text_list:
        text_list += " and "
    text_list += FORMATS[-1]

    return text_list

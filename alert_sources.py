#!/usr/local/bin/python3
"""Defines different types of alert sources."""

import email_alert_gs
import email_alert_ncbi
import email_alert_sd
import email_alert_wiley
import email_alert_wos

# command line argument settings
EMAIL_GS = "googlescholar-email"
EMAIL_NCBI = "myncbi-email"
EMAIL_SD = "sciencedirect-email"
EMAIL_WILEY = "wiley-email"
EMAIL_WOS = "webofscience-email"

# mapping from commmand line arg to module that handles it.

ALERT_SOURCE_MAPPING = {
    EMAIL_GS: email_alert_gs,
    EMAIL_NCBI: email_alert_ncbi,
    EMAIL_SD: email_alert_sd,
    EMAIL_WILEY: email_alert_wiley,
    EMAIL_WOS: email_alert_wos,
    }

ALERT_SOURCES = list(ALERT_SOURCE_MAPPING.keys())


def get_alert_source_module(alert_source_command_line_arg):
    """Given a command line argument specifying the alert source
    return the module that handles it.
    """

    return ALERT_SOURCE_MAPPING[alert_source_command_line_arg]


def get_alert_sources_as_text_list():
    """Return the list of alert sources as a comma separated test string,
    with an "and" between the last two items.
    """

    text_list = ""
    for alert_source in ALERT_SOURCES[0:-1]:
        text_list += alert_source + ", "
    if text_list:
        text_list += " and "
    text_list += ALERT_SOURCES[-1]

    return text_list

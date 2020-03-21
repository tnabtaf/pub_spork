#!/usr/local/bin/python3
"""Superclass for alerts and alert sources of all kinds.

Alerts can be emails, RSS, whatever.  They report papers that match some
condition we are interested in.
"""

import csv

class AlertSource(object):
    """Superclass for alert sources of all kinds."""

    def __init__(self):
        """
        Define an alert source, e.g., ScienceDirect Email
        """
        # meant to be overridden by subclasses.

        return(None)


class Alert(object):
    """Superclass for alerts of all kinds.

    Alerts can be emails, RSS, whatever.  They report papers that match some
    condition we are interested in.  Each Alert has one search string, and
    0, 1, or more publications that match that search string
    """
    def __init__(self):
        """Create an empty alert."""

        self._alert = None                    # The original alert
        # List of pub_alerts generated from this alert.
        self.pub_alerts = None
        # Text string describing the alert.  Usually comes from the alert.
        self.search = None
        self.exclude = False

        return None


# Exclude Columns

ALERT_SOURCE = "alert source"  # This column is treated as a comment
ALERT_SEARCH = "alert text"


class ExcludeAlert(object):
    """
    Information about alerts that exist to exclude results from our
    search results. These searches exist to identify pubs we don't want.
    Why?  Because it was just easier and shorter to create separate,
    *negative* alerts for things we kept seeing as false positives. The
    alternative was to include the excluded terms in all searches, and
    that was intractable, unreadable, and hit search string length limits.
    """
    def __init__(self, row):
        self._row = row
        self.alert_source = row[ALERT_SOURCE]  # GS email?  WoS RSS?
        self.alert_search = row[ALERT_SEARCH]  # text / name of negative search
        return None


class ExcludeAlertsDB(object):
    """
    Database of exclude alerts.
    """
    def __init__(self, exclude_alerts_path):
        """
        Given a path to a TSV file containing a list of exclude alerts, and
        the alert type for each, build and return a database of those
        exclude alerts.  If the path is none, then create an empty DB.
        """

        # Dictionaries of exclude alerts, first by alert type, and then by
        # search text within each alert type.  Basically a 2 level nested
        # dictionary.  TODO: This dictionary is not used at lookup time
        self._by_source_then_search = {}
        # by search text only (this is actually enough)
        self._by_search = {}

        if exclude_alerts_path:
            tsv_in = open(exclude_alerts_path, "r")
            tsv_reader = csv.DictReader(
                tsv_in, dialect="excel-tab")  # fieldnames=COLUMNS
            for row in tsv_reader:
                exclude_alert = ExcludeAlert(row)
                self.add_exclude_alert(exclude_alert)

            tsv_in.close()

        return None

    def add_exclude_alert(self, exclude_alert):
        if exclude_alert.alert_source not in self._by_source_then_search:
            self._by_source_then_search[exclude_alert.alert_source] = {}
        self._by_source_then_search[exclude_alert.alert_source][
            exclude_alert.alert_search] = exclude_alert
        self._by_search[exclude_alert.alert_search] = exclude_alert

        return None

    def is_an_exclude_alert(self, pub_alert):
        """
        Return true if the pub_alert is in the exclude database.
        """
        if pub_alert.search.strip() in self._by_search:
            return True
        return False

        # if pub_alert.alert.source_id in self._by_source_then_search:
        #    if (pub_alaert.alert.search
        #          in self._by_source_then_search[pub_alert.alert.source_id]):
        #        return True
        # return False

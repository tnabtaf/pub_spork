#!/usr/local/bin/python3
"""Superclass for alerts and alert sources of all kinds.

Alerts can be emails, RSS, whatever.  They report papers that match some
condition we are interested in.
"""


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
    condition we are interested in.
    """
    def __init__(self):
        """Create an empty alert."""

        self._alert = None                    # The original alert
        # List of pub_alerts generated from this alert.
        self.pub_alerts = None
        # Text string describing the alert.  Usually comes from the alert.
        self.search = None

        return None

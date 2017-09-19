#!/usr/local/bin/python3
"""A pairing of a publication and the alert that reported it."""

# import publication
# import alert


class PubAlert(object):
    """A pairing of a publication and the alert that reported it."""

    def __init__(self, pub, the_alert):
        """Create pub-alert pairing."""
        self.pub = pub
        self.alert = the_alert
        # text that matched in this pub. From alert. Not all alerts have this.
        self.text_from_pub = None

        return None

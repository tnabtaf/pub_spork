#!/usr/local/bin/python3
"""Superclass for email pub alerts.
"""

import sys
import getpass
import imaplib                            # Email protocol

import alert

IS_EMAIL_SOURCE = True

HEADER_PARTS = "(BODY.PEEK[HEADER.FIELDS (From Subject)])"
BODY_PARTS = "(BODY.PEEK[TEXT])"


class Email(object):
    """
    Abstraction of an IMAP email.
    """
    def __init__(self, header, body):
        self.header = header
        header_sender_subject = self.header[0][1].decode("utf-8")
        header_lines = header_sender_subject.split("\r\n")
        for line in header_lines:
            if line[0:6] == "From: ":
                self.sender = line[6:]
            elif line[0:9] == "Subject: ":
                self.subject = line[9:]

        self.body = body
        self.body_text = self.body[0][1]

        return(None)


class EmailAlert(alert.Alert):
    """
    Abstraction of an email alert.

    Should be overridden by subclass.
    """
    def __init__(self):
        """Init method for EmailAlerts.  This is an abstract method that
        just document attributes.
        """
        self._alert = None           # Alert
        self.pub_alerts = None       # PubAlert. List generated from this alert
        self.search = None           # str. Search alert is for.
        self._email_body_text = None  # str. body of email.
        self.ref = None              # str. Where pub published.

        return(None)


class AlertSource(alert.AlertSource):
    """Source that is email alerts."""

    def __init__(self, account, imaphost):
        """Given an email account, the and IMAP host for it, open a
        connection to that account.
        """
        # all pub_alerts from this source
        self.module = None
        self._connection = imaplib.IMAP4_SSL(imaphost)
        self._connection.login(account, getpass.getpass())
        self._current_email_alerts = []         # TODO: May not need this.
        self._current_pub_alerts = []
        self._msg_nums = None

        return(None)

    def get_pub_alerts(self, senders, mailbox, since, before):
        """
        Given the name of a mailbox, an array of sender email addresses, 
        a start date, and an end date, return all the pub_alerts from that 
        source.

        Senders is an array because providers change the sending email 
        address sometimes.  Using all known email addresses, instead of 
        just the latest one, allows us to scan as far back as we can.
        """

        # Get each email / alert
        self._current_email_alerts = []  # TODO: May not need this.
        self._current_pub_alerts = []

        for sender in senders:
            search_string = _build_imap_search_string(sender, since, before)
            self._connection.select(mailbox, True)
            typ, self._msg_nums = self._connection.uid(
                'search', None, search_string)

            # _msg_nums is a list of email numbers
            for msg_num in self._msg_nums[0].split():
                typ, header = self._connection.uid(
                    "fetch", msg_num, HEADER_PARTS)
                typ, body = self._connection.uid("fetch", msg_num, BODY_PARTS)
                email = Email(header, body)
                # Email alerts can have different versions.
                # Detect which version this is and then invoke the correct
                # constructor for the version.
                alert_class = self.module.sniff_class_for_alert(email)
                email_alert = alert_class(email)
                # email_alert = self.module.EmailAlert(email)
                self._current_email_alerts.append(email_alert)

                # Within each email / alert, generate a pub_alert for each pub.
                # each email can contain 0, 1, or more pub_alerts
                pub_alerts_in_email = len(email_alert.pub_alerts)
                if pub_alerts_in_email:
                    self._current_pub_alerts += email_alert.pub_alerts
                else:
                    print("Warning: Alert for search", file=sys.stderr)
                    print(
                        "  " + email_alert.search + "'",
                        file=sys.stderr)
                    print(
                        "  from source '" + self.module.SOURCE_NAME_TEXT
                        + "' does not contain any papers.\n",
                        file=sys.stderr)

        if len(self._msg_nums) == 0:
            print(
                "Warning: No emails were found from "
                + self.module.SOURCE_NAME_TEXT + "\n")

        return iter(self._current_pub_alerts)

def _build_imap_search_string(
        sender=None,
        sentSince=None,
        sentBefore=None):
    """Builds an IMAP search string from the given inputs.  At least one
    search parameter must be provided.
    """
    clauses = []
    if sentSince:
        clauses.append('SENTSINCE ' + sentSince)
    if sentBefore:
        clauses.append('SENTBEFORE ' + sentBefore)
    if sender:
        clauses.append('From "' + sender + '"')

    if len(clauses) == 0:
        raise AssertionError(
            "At least one parameter must be passed to IMAP.buildSearchString")

    return('(' + " ".join(clauses) + ')')

#!/usr/local/bin/python3
"""Superclass for email pub alerts.
"""

# import ssl
import inspect
import sys
import getpass
import imaplib                            # Email protocol
import base64
import quopri
import re

import alert

# Define constants that should be defined for all subclasses.
IS_EMAIL_SOURCE = True                    # versus, say RSS
SENDERS = None                            # list of email addresses
SOURCE_NAME_TEXT = None                   # eg "ScienceDirect Email

# nasty IMAP bits
HEADER_PARTS = (
    "(BODY.PEEK[HEADER.FIELDS (From Subject Content-Transfer-Encoding)])")
BODY_PARTS = "(BODY.PEEK[TEXT])"

ENCODING_RE = re.compile(rb'Content-Transfer-Encoding: ([\w-]+)')

class Email(object):
    """
    Abstraction of an IMAP email.
    """
    def __init__(self, header, body):
        self.header = header
        self.body = body

        header_sender_subject = self.header[0][1].decode("utf-8")
        header_lines = header_sender_subject.split("\r\n")
        self.encoding = None
        for line in header_lines:
            if line[0:6] == "From: ":
                self.sender = line[6:]
            elif line[0:9] == "Subject: ":
                self.subject = line[9:]
            elif line[0:27] == "Content-Transfer-Encoding: ":
                self.encoding = line[27:]

        if self.encoding == None:
            # sometimes encoding is stored in the body for multi-part messages
            # 
            # body is at [0][1]. Use first encoding we find
            self.encoding = ENCODING_RE.search(
                self.body[0][1]).group(1).decode("utf-8")

        # Decode email body before returning it
        if self.encoding == "base64":
            self.body_text = base64.standard_b64decode(self.body[0][1])
        elif self.encoding in ["quoted-printable", "binary"]:
            # Binary appears in NCBI emails, but they lie, I think
            self.body_text = str(quopri.decodestring(
                self.body[0][1]).decode("utf-8"))
            # TODO: Need to get UTF encoding from email header as well.
        elif self.encoding in ["7bit", "8bit"]:
            self.body_text = self.body[0][1].decode("utf-8")
        else:
            print(
                "ERROR: Unrecognized Content-Transfer-Encoding: "
                + "{0}".format(line), file=sys.stderr)
            print("   for email with subject: {0}".format(
                self.subject))

        return(None)


class EmailAlert(alert.Alert):
    """
    Email Alert!
    All kinds of email alerts subclass this.
    """
    def __init__(self):
        """Init method for EmailAlerts.  Mainly documents attributes,
        but also sets some defaults.
        """
        self._alert = None           # Alert
        self.pub_alerts = None       # PubAlert. List generated from this alert
        self.search = None           # str. Search alert is for.
        self._email_body_text = None  # str. body of email.
        self.warn_if_empty = True    # issue warning if no pubs in alert.

        return(None)

    def get_search_text_with_alert_source(self):
        """
        Return text / name of search, with leading text identifying where 
        the alert came from
        """
        return inspect.getmodule(self).SOURCE_NAME_TEXT + ": " + self.search


class AlertSource(alert.AlertSource):
    """Source that is email alerts."""

    def __init__(self, account, imaphost):
        """Given an email account, the and IMAP host for it, open a
        connection to that account.
        """
        # all pub_alerts from this source
        self.module = None
        # context = ssl.create_default_context()
        self._connection = imaplib.IMAP4_SSL(imaphost)  # ,ssl_context=context)
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
                elif email_alert.warn_if_empty:
                    print("Warning: Alert for search", file=sys.stderr)
                    print(
                        "  '" + email_alert.search + "'",
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

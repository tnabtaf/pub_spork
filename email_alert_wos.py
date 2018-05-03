#!/usr/local/bin/python3
"""Information about a Web of Science reference / Citation"""

import html.parser
import re
import sys

import email_alert
import pub_alert
import publication


# SENDER = "noreply@isiknowledge.com"
# SENDER = "noreply@webofscience.com"
# SENDER = "noreply@clarivate.com" Starting on 2017/11/01

SENDER = [
    "noreply@isiknowledge.com",
    "noreply@webofscience.com",
    "noreply@clarivate.com"
    ]

IS_EMAIL_SOURCE = True

SOURCE_NAME_TEXT = "Web of Science Email"              # used in messages


class EmailAlert(email_alert.EmailAlert, html.parser.HTMLParser):
    """All the information in a Web of Science Email.

    Parse HTML email body from Web Of Science. The body maybe reporting
    more than one paper.

    And WOS email alerts have two formats, dang it:
      Web of Science Citation Alert
      Web of Science Search Alert
    I think only the header differs.
    """

    paper_start_re = re.compile(r'Record \d+ of \d+\.')
    cited_article_re = re.compile(r'.*Cited Article:.*')
    alert_query_re = re.compile(r'.*Alert Query:.*')
    expiration_notice_re = re.compile(
        r'.*Web of Science Citation Alert Expiration Notice')

    def __init__(self, email):

        html.parser.HTMLParser.__init__(self)

        self._alert = email
        self.pub_alerts = []
        self.search = "WoS: "

        body_text = str(self._alert.body_text)

        # strip out all the annoying "\r", "\n", "\t"s and quotes.
        body_text = body_text.replace("\\r", "")
        body_text = body_text.replace("\\n", "")
        body_text = body_text.replace("\\t", "")
        body_text = body_text.replace("\\'", "'")
        self._email_body_text = body_text

        self._current_pub = None

        self._in_title = False
        self._in_title_value = False
        self._in_authors = False
        self._in_query = False
        self._in_query_value = False
        self._in_ref = False

        if EmailAlert.expiration_notice_re.match(body_text):
            expiring_search = re.match(
                r".+?Cited Article:\s+(.+?)\s+Alert Expires:", body_text)
            print("Warning: Search expiring for", file=sys.stderr)
            print(
                "  WOS: {0}\n".format(expiring_search.group(1)),
                file=sys.stderr)
            self.search += expiring_search.group(1)
        else:
            self.feed(body_text)  # process the HTML body text.

        return None

    def handle_data(self, data):

        data = data.strip()
        starting = EmailAlert.paper_start_re.match(data)
        if starting:
            # Each paper starts with: "Record m of n. "
            self._current_pub = publication.Pub()
            self._current_pub_alert = pub_alert.PubAlert(
                self._current_pub, self)
            self.pub_alerts.append(self._current_pub_alert)

        elif data == "Title:":
            self._in_title = True

        elif data == "Authors:":
            self._in_authors = True

        elif (EmailAlert.cited_article_re.match(data)
              or EmailAlert.alert_query_re.match(data)):
            self._in_query = True

        elif data == "Source:":
            self._in_ref = True
            self._current_pub.ref = ""

        elif self._in_title_value:
            if len(self._current_pub.title) > 0:
                self._current_pub.set_title(
                    self._current_pub.title + " " + data)
            else:
                self._current_pub.set_title(data)

        elif self._in_authors:
            # WOS Author lists look like:
            #   Galia, W; Leriche, F; Cruveiller, S; Thevenot-Sergentet, D
            canonical_first_author = publication.to_canonical(
                data.split(",")[0])
            self._current_pub.set_authors(data, canonical_first_author)
            self._in_authors = False

        elif self._in_query_value:
            # need to strip "]]>" from anywhere. Bug in WOS, if punctuation
            # in title.
            self.search += data.replace("]]>", "")
            self._in_query_value = False

        elif self._in_ref:
            self._current_pub.ref += data + " "

        return None

    def handle_starttag(self, tag, attrs):

        if self._in_title and tag == "value":
            self._in_title_value = True

        elif self._in_query and tag == "font":
            self._in_query_value = True
            self._in_query = False

        elif self._in_ref and tag == "a":
            self._current_pub.url = attrs[0][1]
            self._current_pub.canonical_doi = publication.to_canonical_doi(
                self._current_pub.url)

        return None

    def handle_endtag(self, tag):

        # print("In handle_endtag: " + tag)
        if self._in_title_value and tag == "value":
            # print("Clearing in_title_value, in_title")
            self._in_title_value = False
            self._in_title = False

        elif tag == "td" and self._in_ref:
            self._in_ref = False

        return None

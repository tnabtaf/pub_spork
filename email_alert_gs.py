#!/usr/local/bin/python3
"""Email pub alerts from Google Scholar."""

import re
import html.parser
import urllib.parse

import email_alert
import pub_alert
import publication

SENDERS = ["scholaralerts-noreply@google.com"]
IS_EMAIL_SOURCE = True
SOURCE_NAME_TEXT = "Google Scholar Email"              # used in messages

MIN_TRUNCATED_TITLE_LEN = 135  # what's the shortest possible truncated title?


class GSEmailAlert(email_alert.EmailAlert, html.parser.HTMLParser):
    """All the information in a Google Scholar Email alert.

    Parse HTML email body from Google Scholar.  The body maybe reporting more
    than one paper.
    """

    # The formatting of Google Scholar email alerts changed on 2017/10/04
    # Before that, toward the top of the email it said:
    #  Scholar Alert: [ "Galaxy: a platform for large-scale genome analysis" ]
    # after 2017/10/04, towards the bottom of the email it sometimes says:
    #  [ "A framework for ENCODE data: large-scale analyses" ] - new results
    # Sometimes, the only clue is in the email subject line.
    #
    # Format changed again around 2018/01.  "Font" tags stopped showing up.
    # Now using divs instead. Change caused search string, and text in pub to
    # disappear.

    # States
    # Just starting; ignore everything before this
    STATE_LOOKING_FOR_HTML_PART = "Looking for HTML Part"

    # next important bit is anchor containing referencing pub title
    STATE_LOOKING_FOR_TITLE_LINK = "Looking for title link"

    # And then we are in the title link
    STATE_IN_TITLE_LINK = "In title link"

    # after url to referencing pub, the title of that pub is next
    STATE_IN_TITLE_TEXT = "In title text"

    # Title is followed by author list for referencing paper
    STATE_IN_AUTHOR_LIST = "In author list"

    # Sometimes there is an excerpt from the referencing pub.
    STATE_TEXT_FROM_PUB_NEXT = "Text from pub next"

    # and we have found that excerpt.  This is the last state for each
    # referencing pub in the email.
    STATE_IN_TEXT_FROM_PUB = "In text from pub"

    # sometimes, the search string is at the bottom of the email.
    STATE_IN_SEARCH = "In search"

    # Final state
    STATE_SEARCH_PROCESSED = "Search Processed"

    search_start_re = re.compile(r'(Scholar Alert: )|(\[ \()')
    html_part_start_re = re.compile(
        r'Content-Type: text/html; charset="UTF-8"', re.MULTILINE)

    def __init__(self, email):

        html.parser.HTMLParser.__init__(self)

        self._alert = email
        self.pub_alerts = []
        self.search = ""

        # Google Scholar email body content is Quoted Printable encoded.
        self._email_body_text = self._alert.body_text

        self._current_pub = None
        self._current_pub_alert = None

        self._state = GSEmailAlert.STATE_LOOKING_FOR_HTML_PART

        # process the HTML body text.
        self.feed(self._email_body_text)

        # If search was not in message body, then pull it from subject line
        if not self._state == GSEmailAlert.STATE_SEARCH_PROCESSED:
            self.search += " " + self._alert.subject
            self._state = GSEmailAlert.STATE_SEARCH_PROCESSED

        return None

    # Parsing Methods

    def handle_data(self, data):

        data = data.strip()
        if data == "":
            return(None)

        if self._state == GSEmailAlert.STATE_LOOKING_FOR_HTML_PART:
            if GSEmailAlert.html_part_start_re.search(data):
                # Ignore any parts until we get to text/html.
                # Not ignoring them leads to duplicate entries.
                self._state = GSEmailAlert.STATE_LOOKING_FOR_TITLE_LINK

        elif (self._state == GSEmailAlert.STATE_LOOKING_FOR_TITLE_LINK
            and GSEmailAlert.search_start_re.match(data)):
            self.search += data
            self._state = GSEmailAlert.STATE_IN_SEARCH

        elif self._state == GSEmailAlert.STATE_IN_SEARCH:
            self.search += " " + data

        elif self._state == GSEmailAlert.STATE_IN_TITLE_TEXT:
            # sometimes we lose space between two parts of title.
            pub_title = self._current_pub.title
            if (pub_title and pub_title[-1] != " "):
                pub_title += " "
            pub_title += data
            self._current_pub.set_title(pub_title)

        elif self._state ==  GSEmailAlert.STATE_IN_AUTHOR_LIST:
            if self._current_pub.canonical_first_author:
                canonical_first_author = (
                    self._current_pub.canonical_first_author)
            else:
                # Google authors format: EB Alonso, L Cockx, J Swinnen
                canonical_first_author = (
                    publication.to_canonical(
                        data.split(",")[0].split(" ")[-1]))
            # Author list may also have source at end
            parts = data.split("- ")
            self._current_pub.set_authors(
                self._current_pub.authors + parts[0].strip(),
                canonical_first_author)
            if len(parts) == 2:
                self._current_pub.ref = parts[1]

        elif self._state ==  GSEmailAlert.STATE_IN_TEXT_FROM_PUB:
            self._current_pub_alert.text_from_pub += data + " "

        return(None)

    def handle_starttag(self, tag, attrs):

        if (tag == "h3"
            and self._state == GSEmailAlert.STATE_LOOKING_FOR_TITLE_LINK):
            # link to paper is shown in h3.
            self._state =  GSEmailAlert.STATE_IN_TITLE_LINK
            self._current_pub = publication.Pub()
            self._current_pub_alert = pub_alert.PubAlert(
                self._current_pub, self)
            self.pub_alerts.append(self._current_pub_alert)

        elif tag == "a" and self._state == GSEmailAlert.STATE_IN_TITLE_LINK:
            full_url = attrs[0][1]
            url_args = full_url[full_url.find("?")+1:].split("&")

            for url_arg in url_args:
                if url_arg[0:2] == "q=":
                    # need to get rid of URL encoding.
                    self._current_pub.url = urllib.parse.unquote(
                        url_arg[2:])
                    break
                elif url_arg[0:4] == "url=":
                    self._current_pub.url = urllib.parse.unquote(
                        url_arg[4:])
                    break
            if not self._current_pub.url:
                # Some URLs link directly to Google Scholar.
                self._current_pub.url = full_url
            self._state =  GSEmailAlert.STATE_IN_TITLE_TEXT

        elif (tag in ["font", "div"]
                  and self._state == GSEmailAlert.STATE_TEXT_FROM_PUB_NEXT):
            self._state =  GSEmailAlert.STATE_IN_TEXT_FROM_PUB
            self._current_pub_alert.text_from_pub = ""

        return (None)

    def handle_endtag(self, tag):

        if tag == "b" and self._state ==  GSEmailAlert.STATE_IN_SEARCH:
            self._state = GSEmailAlert.STATE_SEARCH_PROCESSED
        elif tag == "h3" and self._state == GSEmailAlert.STATE_IN_TITLE_TEXT:
            self._state = GSEmailAlert.STATE_IN_AUTHOR_LIST
        elif tag == "div" and self._state == GSEmailAlert.STATE_IN_AUTHOR_LIST:
            self._state = GSEmailAlert.STATE_TEXT_FROM_PUB_NEXT
        elif (tag in ["font", "div"]
            and self._state == GSEmailAlert.STATE_IN_TEXT_FROM_PUB):
            self._state = GSEmailAlert.STATE_LOOKING_FOR_TITLE_LINK

        return (None)

    def handle_startendtag(self, tag, attrs):
        """
        Process tags like IMG and BR that don't have end tags.
        """
        return(None)


def sniff_class_for_alert(email):
    """
    Given an email alert from Google Scholar, figure out which version
    of alert this is and then return the class for that version.

    We only have one version of email alerts from Google Scholar.

    Well, sort of.  There have been two format changes since this code
    was first written, but they were both minor, and could be handled in
    the context of the existing parser code without too much work.
    """
    return GSEmailAlert

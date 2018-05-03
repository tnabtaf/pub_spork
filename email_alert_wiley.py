#!/usr/local/bin/python3
"""Email pub alerts from Wiley Online Library."""

import re
import quopri                             # Quoted printable encoding
import html.parser

import email_alert
import pub_alert
import publication

SENDER = ["WileyOnlineLibrary@wiley.com"]

IS_EMAIL_SOURCE = True

SOURCE_NAME_TEXT = "Wiley Online Library"


class EmailAlert(email_alert.EmailAlert, html.parser.HTMLParser):
    """
    All the information in a Wiley Saved Search Alert.

    Parse HTML email body from Wiley.  The body maybe reporting more
    than one paper.
    """
    def __init__(self, email):

        html.parser.HTMLParser.__init__(self)
        self._alert = email
        self.pub_alerts = []
        self.search = "Wiley Online Library: "
        self.ref = None                   # where pub was published.

        # email uses Quoted Printable encoding Decode it.
        decoded = quopri.decodestring(self._alert.body_text).decode('utf-8')
        self._email_body_text = decoded

        self._current_pub = None

        self._in_search = False
        self._awaiting_title = False
        self._in_title = False
        self._awaiting_journal = False
        self._in_journal = False
        self._awaiting_authors = False
        self._in_authors = False

        # It's a Multipart email; just ignore anything outside HTML part.
        self.feed(self._email_body_text)  # process the HTML body text.

        return None

    def handle_data(self, data):

        data = data.strip()

        if self._in_search:
            self.search += data
        elif self._in_title:
            self._current_pub.set_title(self._current_pub.title + data)
        elif self._in_journal:
            self._current_pub.ref += data
        elif self._in_authors:
            # Author string also has date in it:
            # March 2015Pieter-Jan L. Maenhaut, Hend Moens and Filip De Turck
            # strip off anything looking like a year and before.
            authors = re.split(r"\d{4}", data)[-1]
            canonical_first_author = self._current_pub.canonical_first_author
            if not canonical_first_author:
                # extract last name of first author.
                first_author = authors.split(",")[0]
                # part that follows last period, or first space
                name_parts = first_author.split(". ")
                if len(name_parts) > 1:
                    last_name = name_parts[-1]
                else:
                    name_parts = first_author.split(" ")
                    last_name = " ".join(name_parts[1:])
                canonical_first_author = publication.to_canonical(last_name)
            self._current_pub.set_authors(
                self._current_pub.authors + " " + authors,
                canonical_first_author)

        return(None)

    def handle_starttag(self, tag, attrs):

        if tag == "html":
            self.parsing = True
        elif self.parsing and tag == "strong":
            self._in_search = True
        elif (self.parsing
              and tag == "a"
              and len(attrs) > 2
              and attrs[2][1] == "http://journalshelp.wiley.com"):
            self.parsing = False          # Done looking at input.
            self._awaiting_title = False
        elif self.parsing and self._awaiting_title and tag == "a":
            self._awaiting_title = False
            self._in_title = True

            self._current_pub = publication.Pub()
            self.pub_alerts.append(pub_alert.PubAlert(self._current_pub, self))

            # URL looks like
            # http://onlinelibrary.wiley.com/doi/10.1002/spe.2320/abstract?
            #  campaign=wolsavedsearch
            # http://onlinelibrary.wiley.com/doi/10.1002/cpe.3533/abstract
            base_url = attrs[1][1]
            if base_url[0:4] != "http":
                # Wiley sometimes forgets leading http://
                base_url = "http://" + base_url
            url_parts = base_url.split("/")
            self._current_pub.canonical_doi = (
                publication.to_canonical_doi("/".join(url_parts[4:6])))
            self._current_pub.url = base_url
        elif self._awaiting_journal and tag == "span":
            self._in_journal = True
            self._awaiting_journal = False
            self._current_pub.ref = ""

        return (None)

    def handle_endtag(self, tag):

        if self._in_search and tag == "strong":
            self._in_search = False
            self._awaiting_title = True
        elif self._in_title and tag == "a":
            self._in_title = False
            self._awaiting_journal = True
        elif self._in_journal and tag == "span":
            self._in_journal = False
            self._awaiting_authors = True

        return (None)

    def handle_startendtag(self, tag, attrs):
        """
        Process tags like IMG and BR that don't have end tags.
        """
        if self._awaiting_authors and tag == "br":
            self._in_authors = True
            self._awaiting_authors = False
        elif self._in_authors and tag == "br":
            self._in_authors = False
            self._awaiting_title = True   # in case there are more

        return(None)

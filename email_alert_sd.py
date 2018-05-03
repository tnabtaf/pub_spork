#!/usr/local/bin/python3
"""Email pub alerts from ScienceDirect.
"""

import re
import base64
import html.parser

import publication
import email_alert
import pub_alert

SENDER = ["salert@prod.sciencedirect.com"]

SD_BASE_URL = "http://www.sciencedirect.com"
SD_ARTICLE_BASE = "/science/article/pii/"
SD_ARTICLE_BASE_URL = SD_BASE_URL + SD_ARTICLE_BASE
# proxy string goes in between base url and article base.

IS_EMAIL_SOURCE = True

SOURCE_NAME_TEXT = "ScienceDirect Email"                    # used in messages


class EmailAlert(email_alert.EmailAlert, html.parser.HTMLParser):
    """
    All the information in a Science Direct Email alert.

    Parse HTML email body from ScienceDirect.  The body maybe reporting more
    than one paper.
    """
    search_start_re = re.compile(
        r'(More\.\.\.   )*Access (the|all \d+) new result[s]*')

    def __init__(self, email):

        html.parser.HTMLParser.__init__(self)

        self._alert = email
        self.pub_alerts = []
        self.search = ""
        # SD email body content is base64 encoded.  Decode it.
        self._email_body_text = base64.standard_b64decode(
            self._alert.body_text)
        self._current_pub_alert = None

        self._in_search = False
        self._in_title_link = False
        self._in_title_text = False
        self._in_title_text_span_depth = 0
        self._after_title_before_ref = False
        self._in_ref = False
        self._in_authors = False

        self.feed(self._email_body_text.decode('utf-8'))  # process the HTML

        return None

    # Parsing Methods

    def handle_data(self, data):
        data = data.strip()
        startingSearch = EmailAlert.search_start_re.match(data)
        if startingSearch:
            self._in_search = True
        elif self._in_search:
            if data == '':
                self._in_search = False
            else:
                data = data.replace('quot;', '"')
                self.search += data
        elif self._in_title_text:
            self._current_pub_alert.pub.set_title(
                self._current_pub_alert.pub.title + data + " ")
        elif self._in_ref:
            self._current_pub_alert.pub.ref = data
            self._in_ref = False
        elif self._in_authors:
            self._current_pub_alert.pub.set_authors(
                self._current_pub_alert.pub.authors + data,
                to_canonical_first_author(
                    self._current_pub_alert.pub.authors + data))

        return(None)

    def handle_starttag(self, tag, attrs):
        if tag == "td" and (
                len(attrs) > 0
                and attrs[0][0] == "class"
                and attrs[0][1] == "txtcontent"):
            """
            Paper has started; next tag is an anchor, and it has paper URL
            We now have a long URL that points to a public HTML version of
            the paper.  We don't have a doi. But we will have a title shortly.
            ScienceDirect has an API we could use to extract the DOI, or we
            could pull it from the HTML page.
            TODO: For now, go with title only match
            """
            self._in_title_link = True
            pub = publication.Pub()
            self._current_pub_alert = pub_alert.PubAlert(pub, self)
            self.pub_alerts.append(self._current_pub_alert)

        elif tag == "a" and self._in_title_link:
            full_url = attrs[0][1]
            url_args = full_url.split("&")
            for url_arg in url_args:
                if url_arg.startswith("_piikey="):
                    self._current_pub_alert.pub.url = gen_pub_url(url_arg[8:])
                    break
            self._in_title_link = False

        elif tag == "span" and (
                attrs[0][0] == "class"
                and attrs[0][1] == "artTitle"):
            self._in_title_text = True
            self._in_title_text_span_depth = 1
        elif self._in_title_text and tag == "span":
            self._in_title_text_span_depth += 1
        elif tag == "i" and self._after_title_before_ref:
            self._in_ref = True
            self._after_title_before_ref = False

        elif (tag == "span"
              and attrs[0][0] == "class"
              and attrs[0][1] == "authorTxt"):
            self._in_authors = True

        return None

    def handle_endtag(self, tag):

        if self._in_title_text and tag == "span":
            self._in_title_text_span_depth -= 1
            if self._in_title_text_span_depth == 0:
                self._in_title_text = False
                self._after_title_before_ref = True
                self._current_pub_alert.pub.set_title(
                    self._current_pub_alert.pub.title.strip())
        elif self._in_authors and tag == "span":
            self._in_authors = False

        return None

    def handle_startendtag(self, tag, attrs):
        """
        Process tags like IMG and BR that don't have end tags.
        """
        return None

    def handle_entityref(self, name):
        """
        Having troubles with embedded &nbsp;'s in Author list.
        """
        if name == "nbsp" and self._in_authors:
            self._current_pub_alert.pub.set_authors(
                self._current_pub_alert.pub.authors + " ",
                to_canonical_first_author(
                    self._current_pub_alert.pub.authors + " "))
        return None


def to_canonical_first_author(sd_alert_authors_text):
    """Convert an SD email alert author list to a canonical first
    author name.

    Canonical first author is last name of first author.
    """
    # SD alert authors look like:
    #  Eugene Matthew P. Almazan, Sydney L. Lesko, Michael P. Markey
    # Last name of first author
    # - starts at last space or period before the first comma
    # - ends at the first comma
    if sd_alert_authors_text:
        first_author = sd_alert_authors_text.split(",")[0]
        by_dots = first_author.split(".")
        if len(by_dots) > 1:
            # Last name is what follows the last period
            first_author = by_dots[-1]
        else:
            # or if there is no period: it's what follows the last space.
            first_author = by_dots[-1].split()[-1]
        canonical_first_author = publication.to_canonical(first_author)
    else:
        canonical_first_author = None
    return canonical_first_author


def gen_pub_url(pub_url_part, paywall_proxy=None):
    """Given the part of the URL that links to a particular pub, generate the
    full URL for the paper.

    An optional paywall proxy modifier can be included. The proxy looks like:
      .proxy1.library.jhu.edu
    """
    if paywall_proxy:
        return SD_ARTICLE_BASE_URL + paywall_proxy + pub_url_part
    return SD_ARTICLE_BASE_URL + pub_url_part

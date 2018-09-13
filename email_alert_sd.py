#!/usr/local/bin/python3
"""Email pub alerts from ScienceDirect.
"""

import re
import base64  # emails from 2018/08 and before
import quopri  # emails from 2018/08 and later
import urllib.parse
import html.parser
import sys

import publication
import email_alert
import pub_alert

# Formats changed radically in August 2018

SENDER_2018_AND_BEFORE = "salert@prod.sciencedirect.com"    # 2018/08 & before
SENDER_CURRENT = "sciencedirect@notification.elsevier.com"  # 2018/08 & after

SENDERS = [
    SENDER_2018_AND_BEFORE,
    SENDER_CURRENT
    ]

SD_BASE_URL = "http://www.sciencedirect.com"
SD_ARTICLE_BASE = "/science/article/pii/"
SD_ARTICLE_BASE_URL = SD_BASE_URL + SD_ARTICLE_BASE
# proxy string goes in between base url and article base.

CURRENT_SUBJECT_START_RE = re.compile(
        r'New [sS]earch (Alert|results)')

IS_EMAIL_SOURCE = True

SOURCE_NAME_TEXT = "ScienceDirect Email"                    # used in messages


class SDEmailAlert2018AndBefore(
        email_alert.EmailAlert,
        html.parser.HTMLParser):
    """
    All the information in a Science Direct Email alert from August 2018 and
    before.

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
        # SD email body content is base64 encoded before 2018/08
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
        #self.feed(self._email_body_text)  # process the HTML

        return None

    # Parsing Methods

    def handle_data(self, data):
        data = data.strip()
        startingSearch = SDEmailAlert2018AndBefore.search_start_re.match(data)
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

class SDEmailAlert(email_alert.EmailAlert, html.parser.HTMLParser):
    """
    All the information in a Science Direct Email alert from August 2018 and
    later.

    Parse HTML email body from ScienceDirect.  The body maybe reporting more
    than one paper.
    """
    def __init__(self, email):

        html.parser.HTMLParser.__init__(self)

        self._alert = email
        self.pub_alerts = []
        self.search = ""
        # SD emails use quoted printable encoding.  Decode it.
        self._email_body_text = quopri.decodestring(
            self._alert.body_text).decode("utf-8")
        self._current_pub_alert = None

        self._in_html_part = False
        self._in_td_depth = 0
        self._in_h1 = False
        self._in_search = False
        self._in_pub_info = False
        self._in_pub_title = False
        self._expecting_pub_type = False
        self._expecting_ref = False
        self._in_ref = False
        self._expecting_authors = False
        self._in_authors = False
        
        self.feed(self._email_body_text)  # process the HTML

        return None

    # Parsing Methods

    def handle_starttag(self, tag, attrs):
        """
        The search is wrapped in an H1:
          <h1 style="color:#505050;font-size:27px;line-height:40px;font-family:Arial,Helvetica">
            Showing top results for search alert:<br/>GalaxyProject.org
          </h1>
        There are other H1's so need to also match on data text.

        Everything of interest about a matched pub is in a TD followed by an H2.
        There are many TD's but only paper alerts are have H2's
          <td align="left" valign="top">
            <h2 style="color:#505050;font-size:23px;line-height:32px;font-family:Georgia,Arial,Helvetica">
              <a href="https://www.sciencedirect.com/science/article/pii/S0025619618304026?dgcid=raven_sd_search_email" 
                 style="word-wrap:break-word;color:#007398;font-weight:none;text-decoration:none">
                C3 Glomerulopathy: Ten Years' Experience at Mayo Clinic
              </a>
            </h2>
            <p align="left" style="color:#505050;font-size:15px;line-height:24px;font-family:Arial,Helvetica;margin-bottom:2px">
              <span style="font-style:italic">
              </span>Research article
            </p>
            <p align="left" style="color:#848484;font-size:15px;line-height:24px;font-family:Arial,Helvetica;margin-bottom:2px">
              <span style="color:#848484">
                <span>Mayo Clinic Proceedings, Volume 93, Issue 8, Pages 991-1008, 
                </span>
              </span>
            </p>
            <p align="left" style="color:#505050;font-size:15px;line-height:24px;font-family:Arial,Helvetica;margin-bottom:2px">
              Aishwarya Ravindran, Fernando C. Fervenza, Richard J. H. Smith, ... Sanjeev Sethi
            </p>
          </td>
        """
        if self._in_html_part:
            if tag == "td":
                self._in_td_depth += 1
            elif tag == "h1" :
                self._in_h1 = True
            elif tag == "h2" and self._in_td_depth:
                # everything in this TD is about the publication.
                # The H2 is the first element in the TD
                self._in_pub_info = True
                self._in_pub_title = True
                # paper has started
                pub = publication.Pub()
                self._current_pub_alert = pub_alert.PubAlert(pub, self)
                self.pub_alerts.append(self._current_pub_alert)

            elif tag == "a" and self._in_pub_title:
                # pub title is the content of the a tag.
                # pub URL is where the a tag points to.
                full_url = urllib.parse.unquote(attrs[0][1])

                # Current email links look like:
                # https://cwhib9vv.r.us-east-1.awstrack.me/L0/
                #   https:%2F%2Fwww.sciencedirect.com%2Fscience%2Farticle%2Fpii%2FB9780128156094000108
                #   %3Fdgcid=raven_sd_search_email/1/01000164f4ef81a4-8297928b-681a-463a-86c6-30f8eaf2bd7e-000000/_ewE29jTmNGAovSLl4HHgzWfTRQ=68
                #
                # We want the middle part, the second HTTPS.
                # Proxy links won't work with full redirect URL
                minus_redirect = "https" + full_url.split("https")[2]
                self._current_pub_alert.pub.url = minus_redirect.split("?")[0]
                self._current_pub_alert.pub.title = ""

            elif tag == "p" and self._expecting_pub_type:
                self._expecting_pub_type = False
                self._expecting_ref = True

            elif tag == "p" and self._expecting_ref:
                self._expecting_ref = False
                self._in_ref = True

            elif tag == "p" and self._expecting_authors:
                self._expecting_authors = False
                self._in_authors = True

        return(None)

    def handle_data(self, data):
        data = data.strip()

        # ScienceDirect emails contain 2 parts, each with identical html text,
        # except for the part header.  To avoid reporting everything twice,
        # only parse the official HTML attachment

        if len(data) > 12 and data[0:12] == "------=_Part":
            # starting a new part.  Is it the part we are interested in?
            part_lines = data.split("\r\n")
            self._in_html_part = False
            for line in part_lines:
                if line[0:14] == "Content-Type: ":
                    content_type_items = line.split(";")
                    for item in content_type_items:
                        if item.split(" ")[1].strip() == "text/html":
                            self._in_html_part = True
                            break
        
        elif self._in_html_part:
            if self._in_h1 and data == "Showing top results for search alert:":
                self._in_search = True
            elif self._in_search:
                self.search = "ScienceDirect search: " + data
            elif self._in_pub_title:
                self._current_pub_alert.pub.set_title(
                    self._current_pub_alert.pub.title + data + " ")
            elif self._in_ref:
                self._current_pub_alert.pub.ref = data
                self._in_ref = False
                self._expecting_authors = True
            elif self._in_authors:
                self._current_pub_alert.pub.set_authors(
                    data, to_canonical_first_author(data))
                self._in_authors = False
                self._in_pub = False  # Done with this pub alert.

        return(None)

    def handle_endtag(self, tag):

        if self._in_html_part:
            if tag == "a" and self._in_pub_title:
                self._current_pub_alert.pub.set_title(
                    self._current_pub_alert.pub.title.strip())
                self._in_pub_title = False
                self._expecting_pub_type = True

            elif tag == "td":
                self._in_td_depth -= 1

            elif tag == "h1":
                self._in_h1 = False
                self._in_search = False

        return(None)

    def handle_startendtag(self, tag, attrs):
        """
        Process tags like IMG and BR that don't have end tags.
        """
        return None

    def handle_entityref(self, name):
        """
        Having troubles with embedded &nbsp;'s in Author list.

        Don't know if this happens in current version or not.
        """
        if name == "nbsp" and self._in_authors:
            self._current_pub_alert.pub.set_authors(
                self._current_pub_alert.pub.authors + " ",
                to_canonical_first_author(
                    self._current_pub_alert.pub.authors + " "))
        return None


def sniff_class_for_alert(email):
    """
    Given an email alert from ScienceDirect, figure out which version
    of alert this is and then return the class for that version.

    ScienceDirect introduced an entirely new system and format for email
    alerts in August 2018.
    """
    # Subject or sender can be used to distinguish the two versions.
    # Subject was already parsed out when the Email object was constructed.
    #  New Subject Line: New [sS]earch (Alert|Results) ...
    #  Old Subject Line: ScienceDirect Search Alert: ....
    # That seems easy...

    print(email.subject, file=sys.stderr)
    if CURRENT_SUBJECT_START_RE.match(email.subject):
        return SDEmailAlert
    else:
        return SDEmailAlert2018AndBefore

    
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

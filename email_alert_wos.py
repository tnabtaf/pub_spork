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

SENDERS = [
    "noreply@isiknowledge.com",
    "noreply@webofscience.com",
    "noreply@clarivate.com"
    ]

IS_EMAIL_SOURCE = True

SOURCE_NAME_TEXT = "Web of Science Email"              # used in messages

CURRENT_BODY_TEXT_START_TAG_RE = re.compile(
        r"[b'\\rn]*<!DOCTYPE html>")


class WoSEmailAlert2018AndBefore(
        email_alert.EmailAlert, html.parser.HTMLParser):
    """All the information in a Web of Science Email.

    Parse HTML email body from Web Of Science. The body maybe reporting
    more than one paper.

    Before August 2018:
    And WOS email alerts have two formats, dang it:
      Web of Science Citation Alert
      Web of Science Search Alert
    I think only the header differs.

    After August 2018:
      Completely different email format
      Web of Science Alert - Novak, P    Is a citation alert.
      Web of Science Alert - Genomics Virtual Lab    Is a topic alert.
      They might have the same internal structure though.
    """

    paper_start_re = re.compile(r'Record \d+ of \d+')
    cited_article_re = re.compile(r'.*Cited Article:.*')
    alert_query_re = re.compile(r'.*Alert Query:.*')
    expiration_notice_re = re.compile(
        r'.*Web of Science Citation Alert Expiration Notice')

    def __init__(self, email):

        html.parser.HTMLParser.__init__(self)

        self._alert = email
        self.pub_alerts = []
        self.search = "WoS: "
        self.warn_if_empty = False  # WoS sends even if nothing to report

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

        if WoSEmailAlert2018AndBefore.expiration_notice_re.match(body_text):
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
        starting = WoSEmailAlert2018AndBefore.paper_start_re.match(data)
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

        elif (WoSEmailAlert2018AndBefore.cited_article_re.match(data)
              or WoSEmailAlert2018AndBefore.alert_query_re.match(data)):
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


class WoSEmailAlert(email_alert.EmailAlert, html.parser.HTMLParser):
    """All the information in a Web of Science Email.

    Parse HTML email body from Web Of Science. The body maybe reporting
    more than one paper.

    Format from 2018/08/15 on.
      Web of Science Alert - Novak, P    Is a citation alert.
      Web of Science Alert - Genomics Virtual Lab    Is a topic alert.
      They might have the same internal structure

    What to look for
      Your article &quot; | Your saved search for &quot;
      the next <span> start
      The text of the search
      </span> end
      <span> start
      cited n times | has n new records
      </span> end
      Record m of n
      <a class="smallV110" href="http://gateway.webofknowledge.com/gateway/\
Gateway.cgi?GWVersion=2&amp;SrcAuth=Alerting&amp;SrcApp=Alerting&amp;\
DestApp=WOS&amp;DestLinkType=FullRecord&amp;UT=WOS:000460742800042"
      - which is the only place that smallV110 appears
      - that URL is not useful.  Requires a login, and points to WOS, not \
the paper
      Pipeline for the Rapid Development of Cytogenetic Markers Using Genomic \
Data of Related Species
      </a>
      Authors:
      <span start
      Author list
      </span end
      <value>GENES</value>
      then pretty much all the data between the next td can be saved as text.
      <td style="max-width: 760px; display: block; clear: both; \
font-family: arial; padding-left: 20px; padding-right: 20px; font-size: 12px; \
color: #666666" class="container container-padding"><span \
style="color: #666666; font-weight: 600;">Volume: </span><span s\
tyle="color: #666666; font-weight: normal;">
<value>10</value> &nbsp;&nbsp;&nbsp;&nbsp;</span><span \
style="color: #666666; font-weight: 600;">Issue: </span><span \
style="color: #666666; font-weight: normal;">
<value>2</value> &nbsp;&nbsp;&nbsp;&nbsp;</span><span \
style="color: #666666; \
font-weight: 600;">Published: </span><span style="color: #666666; \
font-weight: normal;">
<value>FEB 2019</value> &nbsp;&nbsp;&nbsp;&nbsp;</span>
<span style="font-weight: 600; color:#666666">Language:
</span><span style="color:#666666">English</span> \
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;

<span style="font-weight: 600; color:#666666">Document type:
</span><span style="color:#666666">Article</span></td>
    next td contains the DOI:
    <td style="max-width: 760px; display: block; clear: both; \
background-color: #ffffff; font-size: 12px; font-family: arial; \
padding-left: 20px; padding-right: 20px;" bgcolor="#ffffff" \
class="container container-padding"><span style="color: #666666; \
font-weight: 600;">DOI:</span><span style="color: #666666;">
<a href="http://dx.doi.org/10.3390/genes10020113">10.3390/genes10020113</a> \
</span></td>
Then followed by keywords and abstract.
    """

    expiration_notice_re = re.compile(
        r'.*You have an expiring Saved Search alert from Web of Science')
    search_preface_re = re.compile(r'(Your article|Your saved search for) "')
    paper_start_re = re.compile(r'Record \d+ of \d+')
    count_re = re.compile(r'(cited|has) (\d+) (times|new records)')

    cited_article_re = re.compile(r'.*Cited Article:.*')
    alert_query_re = re.compile(r'.*Alert Query:.*')

    def __init__(self, email):

        html.parser.HTMLParser.__init__(self)

        self._alert = email
        self.pub_alerts = []
        self.search = "WoS: "
        self.warn_if_empty = False  # WoS sends even if nothing to report
        self.expected_pub_count = None
        self.found_pub_count = 0

        body_text = str(self._alert.body_text)

        # strip out all the annoying "\r", "\n", "\t"s and quotes.
        body_text = body_text.replace("\\r", "")
        body_text = body_text.replace("\\n", "")
        body_text = body_text.replace("\\t", "")
        body_text = body_text.replace("\\'", "'")
        self._email_body_text = body_text

        self._current_pub = None

        self._expecting_search = True
        self._in_search_section = False
        self._in_search_text = False
        self._expecting_count_section = False
        self._in_count_section = False
        self._expecting_pub_section = False
        self._expecting_pub = False
        self._expecting_title = False
        self._in_title = False
        self._expecting_authors = False
        self._in_authors = False
        self._expecting_journal = False
        self._in_journal = False
        self._expecting_citation = False
        self._in_citation = False
        self._expecting_doi = False
        self._in_doi_section = False
        self._in_doi = False
        self._done = False

        if WoSEmailAlert.expiration_notice_re.match(body_text):
            expiring_search = re.match(
                r'.+?Your alert for <span.+?>&quot;\s*(.+?)&quot;',
                body_text)
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
        if data == "":
            return None                   # nothing to see here folks.

        if self._expecting_search:
            if WoSEmailAlert.search_preface_re.match(data):
                self._expecting_search = False
                self._in_search_section = True

        elif self._in_search_text:
            self.search += data
            self._in_search_text = False
            self._expecting_count_section = True

        elif self._in_count_section:
            self.expected_pub_count = int(WoSEmailAlert.count_re.match(
                data).group(2))
            self._in_count_section = False
            self._expecting_pub_section = True

        elif self._expecting_pub and WoSEmailAlert.paper_start_re.match(data):
            # Each paper starts with: "Record m of n. "
            self._current_pub = publication.Pub()
            self._current_pub_alert = pub_alert.PubAlert(
                self._current_pub, self)
            self.pub_alerts.append(self._current_pub_alert)
            self.found_pub_count += 1
            self._expecting_pub = False
            self._expecting_title = True

        elif self._in_title:
            self._current_pub.set_title(data)
            self._in_title = False
            self._expecting_authors = True

        elif self._expecting_authors and data == "Authors:":
            self._expecting_authors = False
            self._in_authors = True

        elif self._in_authors:
            # WOS Author lists look like:
            #   Galia, W; Leriche, F; Cruveiller, S; Thevenot-Sergentet, D
            canonical_first_author = publication.to_canonical(
                data.split(",")[0])
            self._current_pub.set_authors(data, canonical_first_author)
            self._in_authors = False
            self._expecting_journal = True

        elif self._in_journal:
            self._current_pub.ref = data
            self._in_journal = False
            self._expecting_citation = True

        elif self._in_citation:
            self._current_pub.ref += ", " + data

        elif self._expecting_doi and data == "DOI:":
            self._expecting_doi = False
            self._in_doi_section = True

        elif self._in_doi:
            self._current_pub.canonical_doi = publication.to_canonical_doi(
                data)
            self._in_doi = False
            self._expecting_pub = True

        return None

    def handle_starttag(self, tag, attrs):

        if self._in_search_section and tag == "span":
            self._in_search_section = False
            self._in_search_text = True

        elif self._expecting_count_section and tag == "span":
            self._expecting_count_section = False
            self._in_count_section = True

        elif self._expecting_pub_section and tag == "table":
            self._expect_pub_section = False
            self._expecting_pub = True

        elif self._expecting_title and tag == "a":
            if attrs[0][1] == "smallV110":
                self._expecting_title = False
                self._in_title = True

        elif self._expecting_journal and tag == "value":
            self._expecting_journal = False
            self._in_journal = True

        elif self._expecting_citation and tag == "td":
            self._expecting_citation = False
            self._in_citation = True

        elif self._in_doi_section and tag == "a":
            self._current_pub.url = attrs[0][1]
            self._in_doi_section = False
            self._in_doi = True

        return None

    def handle_endtag(self, tag):

        # print("In handle_endtag: " + tag)
        if self._in_citation and tag == "td":
            self._in_citation = False
            self._expecting_doi = True

        elif self._expecting_pub and tag == "body":
            # done with pubs. Check count
            if self.expected_pub_count != self.found_pub_count:
                print(
                    "Warning: WoS expected and found pub counts disagree.",
                    file=sys.stderr)
                print(
                    "  Expected: {0}\n  Found:   {1}\n".format(
                        self.expected_pub_count, self.found_pub_count))
            self._expecting_pub = False
            self._done = True

        return None


def sniff_class_for_alert(email):
    """
    Given an email alert from Web of Science, figure out which version
    of alert this is and then return the class for that version.

    Emails from WOS changed formats in mid-August, 2018.
    Detect which format we are dealing with.

    Subject lines are in same format.
    Old body text: starts with <html> tag.
    New body text: starts with <!DOCTYPE html> tag.
    """
    #
    if CURRENT_BODY_TEXT_START_TAG_RE.match(str(email.body_text)):
        return WoSEmailAlert
    else:
        return WoSEmailAlert2018AndBefore

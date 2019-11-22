#!/usr/local/bin/python3
"""Email pub alerts from Wiley Online Library."""

import re
import html.parser

import email_alert
import pub_alert
import publication

SENDERS = ["WileyOnlineLibrary@wiley.com"]

IS_EMAIL_SOURCE = True

SOURCE_NAME_TEXT = "Wiley Online Library"

SUBJECT_START_2018 = "Saved Search Alert"
SUBJECT_START_2018_LEN = len(SUBJECT_START_2018)
CURRENT_CITATION_SUBJECT = "Article Event Alert"



class WileyEmailAlert2018AndBefore(
        email_alert.EmailAlert, html.parser.HTMLParser):
    """
    All the information in a Wiley Saved Search Alert, using the 2018 and
    before format.

    Parse HTML email body from Wiley.  The body maybe reporting more
    than one paper.
    """

    SEARCH_COMING = "Saved Search Alert result notifications for"

    def __init__(self, email):

        html.parser.HTMLParser.__init__(self)
        email_alert.EmailAlert.__init__(self)
        self._alert = email
        self.pub_alerts = []
        self.search = "Wiley Online Library: "

        # email uses Quoted Printable encoding
        self._email_body_text = self._alert.body_text

        self._current_pub = None

        self._parsing = False
        self._search_coming = False
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

        if self._parsing and (
                data == WileyEmailAlert2018AndBefore.SEARCH_COMING):
            self._search_coming = True
        elif self._in_search:
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
            self._parsing = True
        elif self._search_coming and tag == "strong":  # 2018
            self._search_coming = False
            self._in_search = True
        elif (self._parsing
              and tag == "a"
              and len(attrs) > 2
              and attrs[2][1] == "http://journalshelp.wiley.com"):
            self._parsing = False          # Done looking at input.
            self._awaiting_title = False
        elif self._parsing and self._awaiting_title and tag == "a":
            self._awaiting_title = False
            self._in_title = True

            self._current_pub = publication.Pub()
            self.pub_alerts.append(pub_alert.PubAlert(self._current_pub, self))

            # URL looks like
            # http://onlinelibrary.wiley.com/doi/10.1002/spe.2320/abstract?
            #  campaign=wolsavedsearch
            # http://onlinelibrary.wiley.com/doi/10.1002/cpe.3533/abstract
            # loop through attrs looking for href
            for attr in attrs:
                if attr[0] == "href":
                    base_url = attr[1]
                    break
            if base_url[0:4] != "http":
                # Wiley sometimes forgets leading http://
                base_url = "http://" + base_url
            self._current_pub.url = base_url
            # self._current_pub.url = (
            #    publication.get_potentially_redirected_url(base_url))
            if base_url.split("/")[3] == "doi":
                doi_bits = "/".join(base_url.split("/")[4:6])
                self._current_pub.canonical_doi = (
                    publication.to_canonical_doi(doi_bits))
        elif self._awaiting_journal and tag == "span":
            self._in_journal = True
            self._awaiting_journal = False
            self._current_pub.ref = ""

        return (None)

    def handle_endtag(self, tag):

        if self._in_search and tag == "strong":  #2018
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

class WileyEmailAlert(email_alert.EmailAlert, html.parser.HTMLParser):
    """
    All the information in a Wiley Saved Search Alert, from 2019 on.

    Parse HTML email body from Wiley.  The body maybe reporting more
    than one paper.
    """

    SEARCH_COMING = "Your criteria:"

    STATE_PARSING_STARTED = "Parsing Started"
    STATE_AWAITING_SEARCH = "Awaiting Search"
    STATE_IN_SEARCH = "In Search"
    STATE_AWAITING_TITLE = "Awaiting Title"
    STATE_IN_TITLE = "In Title"
    STATE_AWAITING_JOURNAL = "Awaiting Journal"
    STATE_IN_JOURNAL = "In Journal"
    STATE_AWAITING_AUTHORS = "Awaiting Authors"
    STATE_IN_AUTHORS = "In Authors"
    STATE_DONE = "Done"

    def __init__(self, email):

        html.parser.HTMLParser.__init__(self)
        email_alert.EmailAlert.__init__(self)
        self._alert = email
        self.pub_alerts = []
        self.search = "Wiley Online Library: "

        # email uses Quoted Printable encoding.
        self._email_body_text = self._alert.body_text

        self._current_pub = None

        self._state = None

        # It's a Multipart email; just ignore anything outside HTML part.
        self.feed(self._email_body_text)  # process the HTML body text.

        return None

    def handle_data(self, data):

        data = data.strip()

        if (self._state == WileyEmailAlert.STATE_PARSING_STARTED
                and data == WileyEmailAlert.SEARCH_COMING):
            self._state = WileyEmailAlert.STATE_AWAITING_SEARCH
        elif self._state == WileyEmailAlert.STATE_IN_SEARCH:
            self.search += data
        elif self._state == WileyEmailAlert.STATE_IN_TITLE:
            self._current_pub.set_title(self._current_pub.title + data)
        elif self._state == WileyEmailAlert.STATE_IN_JOURNAL:
            self._current_pub.ref += data
        elif self._state == WileyEmailAlert.STATE_IN_AUTHORS:
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
            self._state = WileyEmailAlert.STATE_PARSING_STARTED
        elif (self._state != WileyEmailAlert.STATE_DONE
              and tag == "a"
              and len(attrs) > 2
              and attrs[2][1] == "http://journalshelp.wiley.com"):
            self._state = WileyEmailAlert.STATE_DONE   # Done looking at input.
        elif (self._state == WileyEmailAlert.STATE_AWAITING_TITLE
              and tag == "a"):
            self._state = WileyEmailAlert.STATE_IN_TITLE
            self._current_pub = publication.Pub()
            self.pub_alerts.append(pub_alert.PubAlert(self._current_pub, self))

            # URL looks like
            # http://el.wiley.com/wf/click?upn=-2F4d0Y8aR13lVHu481a...
            # however, that redirects to
            # https://onlinelibrary.wiley.com/doi/10.15252/embr.201847227
            # EXCEPT IT DOES NOT. FROM THIS PROGRAM IT REDIRECTS TO
            # https://onlinelibrary.wiley.com/action/cookieAbsent
            #   Hmm. Works for CURL.  Updated publication.py to use CURL
            #   Nope, still doesn't work, still get cookieAbsent.
            # loop through attrs looking for href
            for attr in attrs:
                if attr[0] == "href":
                    base_url = attr[1]
                    break
            # if base_url[0:4] != "http":
                # Wiley sometimes forgets leading http://
                # base_url = "http://" + base_url
            self._current_pub.url = base_url
            # self._current_pub.url = (
            #    publication.get_potentially_redirected_url(base_url))
            if base_url.split("/")[3] == "doi":
                doi_bits = "/".join(base_url.split("/")[4:6])
                self._current_pub.canonical_doi = (
                    publication.to_canonical_doi(doi_bits))
        elif (self._state == WileyEmailAlert.STATE_AWAITING_JOURNAL
              and tag == "span"):
            self._state = WileyEmailAlert.STATE_IN_JOURNAL
            self._current_pub.ref = ""

        return (None)

    def handle_endtag(self, tag):

        if (self._state == WileyEmailAlert.STATE_AWAITING_SEARCH
            and tag == "strong"):  # 2019
            self._state = WileyEmailAlert.STATE_IN_SEARCH
        elif (self._state == WileyEmailAlert.STATE_IN_SEARCH
              and tag == "div"):  #2019
            self._state = WileyEmailAlert.STATE_AWAITING_TITLE
        elif self._state == WileyEmailAlert.STATE_IN_TITLE and tag == "a":
            self._state = WileyEmailAlert.STATE_AWAITING_JOURNAL
        elif self._state == WileyEmailAlert.STATE_IN_JOURNAL and tag == "span":
            self._state = WileyEmailAlert.STATE_AWAITING_AUTHORS

        return (None)

    def handle_startendtag(self, tag, attrs):
        """
        Process tags like IMG and BR that don't have end tags.
        """
        if (self._state == WileyEmailAlert.STATE_AWAITING_AUTHORS
            and tag == "br"):
            self._state = WileyEmailAlert.STATE_IN_AUTHORS
        elif self._state == WileyEmailAlert.STATE_IN_AUTHORS and tag == "br":
            self._state = WileyEmailAlert.STATE_AWAITING_TITLE 

        return(None)


class WileyEmailCitationAlert(email_alert.EmailAlert, html.parser.HTMLParser):
    """
    All the information in a Wiley Citation Alert, from 2019 on.

    These are different enough from the save search alerts to merit
    their own parse.
    """
    STATE_IN_SEARCH = "In Search"
    STATE_AWAITING_PUBS = "Awaiting Pubs"
    STATE_IN_PUB_LIST = "In Pub List"
    STATE_AWAITING_AUTHOR_OR_TITLE = "Awaiting Author or Title"
    STATE_IN_AUTHOR = "In Author"
    STATE_IN_TITLE_SECTION = "In Title Section"
    STATE_IN_JOURNAL = IN_JOURNAL = "In Journal"
    STATE_IN_DOI = "In DOI"
    STATE_IN_VOLUME = "In Volume"
    STATE_IN_REF_TAIL = "In Ref Tail"
    STATE_DONE = "Done"

    def __init__(self, email):

        html.parser.HTMLParser.__init__(self)
        email_alert.EmailAlert.__init__(self)
        self._alert = email
        self.pub_alerts = []
        self.search = "Wiley Online Library: "

        # email uses Quoted Printable encoding Decode it.
        self._email_body_text = self._alert.body_text

        self._current_pub = None
        self._state = None

        # It's a Multipart email; just ignore anything outside HTML part.
        self.feed(self._email_body_text)  # process the HTML body text.

        return None

    def handle_starttag(self, tag, attrs):

        if tag == "h5":
            self._state = WileyEmailCitationAlert.STATE_IN_SEARCH  # only 1 h5; wraps pub being cited.
        elif (tag =="p"
              and self._state == WileyEmailCitationAlert.STATE_IN_PUB_LIST):
            self._state = WileyEmailCitationAlert.STATE_AWAITING_AUTHOR_OR_TITLE
            self._current_pub = publication.Pub()
            self.pub_alerts.append(pub_alert.PubAlert(self._current_pub, self))
        elif (
            tag == "span"
            and self._state
                == WileyEmailCitationAlert.STATE_AWAITING_AUTHOR_OR_TITLE):
            # Just entered an author.
            self._state = WileyEmailCitationAlert.STATE_IN_AUTHOR
        elif (tag == "em"
              and self._state == WileyEmailCitationAlert.STATE_IN_TITLE_SECTION):
            # em here means journal, I sure hope.
            self._state = WileyEmailCitationAlert.STATE_IN_JOURNAL
        elif (tag == "strong"
              and self._state == WileyEmailCitationAlert.STATE_IN_TITLE_SECTION):
            self._state = WileyEmailCitationAlert.STATE_IN_VOLUME
        elif (tag == "hr"
              and self._state == WileyEmailCitationAlert.STATE_IN_PUB_LIST):
            self._state = WileyEmailCitationAlert.STATE_DONE
        return (None)


    YEAR_RE = re.compile(r"\([12][0-9][0-9][0-9]\)\.$")

    def handle_title_section_data(self, data):
        """
        Title sections are complicated. As of May 2019, title sections look like

           Dissecting the Control of Flowering Time in Grasses
           Using Brachypodium distachyon,
           ,
           10.1007/7397_2015_10,
           (259-273),
           1-Jan-(2015).
        OR
          ,
           Dynamic multi-workflow scheduling: A deadline and
           cost-aware approach for commercial clouds,
            <em>Future Generation Computer Systems</em>,
            10.1016/j.future.2019.04.029,
            <strong>100</strong>,
            (98-108),
            1-Nov-(2019).
        So, um crap.
        That info may arrive in a single string, or in several strings
        """
        parts = data.split(", ")
        # What do we have?
        if len(parts) > 4 and publication.is_canonical_doi(parts[-3]):
            # probably (certainly?) have title section in a single string.
            #  title in parts[1:-4],
            #  DOI in parts[-3],
            #  Journal parts[-4],
            #  Other ref misc in parts[-2:]
            self._current_pub.set_title(
                self._current_pub.title + " ".join(parts[1:-4]))
            self._current_pub.canonical_doi = parts[-3]
            self._current_pub.ref += parts[-4] + ", " + ", ".join(parts[-2:])

        else:
            # Um, crap.  Are we in just the title, or some ref stuff?
            # If parts[-1] ends in (year). then we are in ref
            if WileyEmailCitationAlert.YEAR_RE.search(data):
                self._current_pub.ref += data
            else:  # gotta be (gotta be!) title
                self._current_pub.set_title(self._current_pub.title + " " + data)

        return None


    def handle_data(self, data):

        data = data.strip()

        if self._state == WileyEmailCitationAlert.STATE_IN_SEARCH:
            self.search += data
        elif self._state == WileyEmailCitationAlert.STATE_IN_AUTHOR:
            canonical_first_author = self._current_pub.canonical_first_author
            if not canonical_first_author:
                # extract last name of first author.
                last_name = data.split(" ")[-1]
                canonical_first_author = publication.to_canonical(last_name)
            self._current_pub.set_authors(
                self._current_pub.authors + " " + data,
                canonical_first_author)
        elif self._state == WileyEmailCitationAlert.STATE_AWAITING_AUTHOR_OR_TITLE:
            # could be an author list joiner ", " or "and" or start of title
            if data in [",", "and"]:
                # still in author list
                self._current_pub.set_authors(
                    self._current_pub.authors + " " + data,
                    self._current_pub.canonical_first_author)
            else:  # Into title
                self._state = WileyEmailCitationAlert.STATE_IN_TITLE_SECTION
                self.handle_title_section_data(data)
        elif self._state == WileyEmailCitationAlert.STATE_IN_JOURNAL:
            self._current_pub.ref += " " + data
        elif self._state == WileyEmailCitationAlert.STATE_IN_DOI:
            self._current_pub.canonical_doi = data
            self._state = WileyEmailCitationAlert.STATE_IN_TITLE_SECTION
        elif self._state == WileyEmailCitationAlert.STATE_IN_VOLUME:
            self._current_pub.ref += ", " + data
        elif self._state == WileyEmailCitationAlert.STATE_IN_REF_TAIL:
            self._current_pub.ref += ", " + data
            self._state = WileyEmailCitationAlert.STATE_IN_TITLE_SECTION

        return(None)


    def handle_endtag(self, tag):

        if (tag == "h5"
            and self._state == WileyEmailCitationAlert.STATE_IN_SEARCH):
            self._state = WileyEmailCitationAlert.STATE_AWAITING_PUBS
        elif (tag == "h2"
              and self._state == WileyEmailCitationAlert.STATE_AWAITING_PUBS):
            self._state = WileyEmailCitationAlert.STATE_IN_PUB_LIST
        elif (tag == "span"
              and self._state == WileyEmailCitationAlert.STATE_IN_AUTHOR):
            self._state = WileyEmailCitationAlert.STATE_AWAITING_AUTHOR_OR_TITLE
        elif (tag == "em"
              and self._state == WileyEmailCitationAlert.STATE_IN_JOURNAL):
            self._state = WileyEmailCitationAlert.STATE_IN_DOI
        elif (tag == "strong"
              and self._state == WileyEmailCitationAlert.STATE_IN_VOLUME):
            self._state = WileyEmailCitationAlert.STATE_IN_REF_TAIL
        elif (tag == "p"
              and self._state == WileyEmailCitationAlert.STATE_IN_TITLE_SECTION):
            self._state = WileyEmailCitationAlert.STATE_IN_PUB_LIST

        return (None)


def sniff_class_for_alert(email):
    """
    Given an email alert from Wiley, figure out which version
    of alert this is and then return the class for that version.

    2018 and before has the subject line "Saved Search Alert"
    2019 and on has "Wiley Online Library x new match for" or
    "xxxx yyyy Article Event Alert (doi:10.1002/0471142727.mb1910s89)"
    for citation alerts.
    """

    if str(email.subject)[:SUBJECT_START_2018_LEN] == SUBJECT_START_2018:
        return WileyEmailAlert2018AndBefore
    elif CURRENT_CITATION_SUBJECT in str(email.subject):
        return WileyEmailCitationAlert
    else:
        return WileyEmailAlert

#!/usr/local/bin/python3
"""Email pub alerts from Google Scholar."""

import re
import quopri                             # Quoted printable encoding
import html.parser
import urllib.parse

import email_alert
import pub_alert
import publication

SENDER = ["scholaralerts-noreply@google.com"]

IS_EMAIL_SOURCE = True

SOURCE_NAME_TEXT = "Google Scholar Email"              # used in messages


class EmailAlert(email_alert.EmailAlert, html.parser.HTMLParser):
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
    # Format changed again around 2018/01.  "Font" tags stopped showing up.  Now
    # using divs instead. Change caused search string, and text in pub to
    # disappear.
    
    search_start_re = re.compile(r'(Scholar Alert: )|(\[ \()')

    def __init__(self, email):

        html.parser.HTMLParser.__init__(self)

        self._alert = email
        self.pub_alerts = []
        self.search = "Google: "
        self.ref = None                   # Where pub was published.

        # Google Scholar email body content is Quoted Printable encoded.
        # Decode it.
        self._email_body_text = quopri.decodestring(self._alert.body_text)

        self._current_pub = None
        self._current_pub_alert = None

        self._in_search = False
        self._search_processed = False
        self._in_title_ink = False
        self._in_title_text = False
        self._in_author_list = False
        self._text_from_pub_next = False
        self._in_text_from_pub = False

        # process the HTML body text.
        self.feed(self._email_body_text.decode('utf-8'))

        # If search was not in message body, then pull it from subject line
        if not self._search_processed:
            self.search += " " + self._alert.subject
            self._search_processed = True
        
        return None

    # Parsing Methods

    def handle_data(self, data):

        data = data.strip()
        starting_search = EmailAlert.search_start_re.match(data)
        if starting_search:
            self.search += data
            self._in_search = True

        elif self._in_search:
            self.search += " " + data

        elif self._in_title_text and data:
            # sometimes we lose space between two parts of title.
            pub_title = self._current_pub.title
            if (pub_title and pub_title[-1] != " "):
                pub_title += " "
            pub_title += data
            self._current_pub.set_title(pub_title)

        elif self._in_author_list and data:
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
        elif self._in_text_from_pub and data:
            self._current_pub_alert.text_from_pub += data + " "

        return(None)

    def handle_starttag(self, tag, attrs):

        if tag == "h3":
            # link to paper is shown in h3.
            self._in_title_link = True
            self._current_pub = publication.Pub()
            self._current_pub_alert = pub_alert.PubAlert(
                self._current_pub, self)
            self.pub_alerts.append(self._current_pub_alert)

        elif tag == "a" and self._in_title_link:
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
            self._in_title_link = False
            self._in_title_text = True

        elif tag in ["font", "div"] and self._text_from_pub_next:
            self._text_from_pub_next = False
            self._in_text_from_pub = True
            self._current_pub_alert.text_from_pub = ""

        return (None)

    def handle_endtag(self, tag):

        if tag == "b" and self._in_search:
            self._in_search = False
            self._search_processed = True
        elif tag == "a" and self._in_title_text:
            self._in_title_text = False
        elif tag == "h3":
            self._in_author_list = True
        elif tag == "div" and self._in_author_list:
            self._in_author_list = False
            self._text_from_pub_next = True
        elif tag in ["font", "div"] and self._in_text_from_pub:
            self._in_text_from_pub = False

        return (None)

    def handle_startendtag(self, tag, attrs):
        """
        Process tags like IMG and BR that don't have end tags.
        """
        return(None)

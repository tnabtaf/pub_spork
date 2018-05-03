#!/usr/local/bin/python3
"""Handle publication alerts from MyNCBI."""

import html.parser
import quopri

import email_alert
import pub_alert
import publication

IS_EMAIL_SOURCE = True

SENDER = ["efback@ncbi.nlm.nih.gov"]


class EmailAlert(email_alert.EmailAlert, html.parser.HTMLParser):
    """
    All the information in an NCBI emil alert.

    NCBI emails have a header which specifies the search that was matched,
    followed by a list of papers that matched.
    """
    def __init__(self, email):

        html.parser.HTMLParser.__init__(self)

        self._alert = email
        self.pub_alerts = []
        self.search = "My NCBI: "

        # email from NCBI uses Quoted Printable encoding.  Unencode it.
        decoded = str(quopri.decodestring(email.body_text))
        # strip out all the annoying "\r", "\n", "\t"s and quotes.
        decoded = decoded.replace("\\r", "")
        decoded = decoded.replace("\\n", "")
        decoded = decoded.replace("\\t", "")
        decoded = decoded.replace("\\'", "'")
        self._email_body_text = decoded
        self.ref = None                   # Where pub was published.

        self._current_pub = None
        self._in_senders_message = False
        self._in_search = False
        self._in_search_text = False
        self._in_title = False
        self._expecting_authors = False
        self._really_expecting_authors = False
        self._in_authors = False
        self._in_ref = False
        self._in_ref_details = False

        self.feed(str(self._email_body_text))  # process the HTML body text.

        return None

    def handle_data(self, data):

        data = data.strip()
        # print("Data", data)

        if data == "Search:":
            self._in_search = True
        elif data == "Sender's message:":
            self._in_senders_message = True
        elif self._in_senders_message:
            self.search += data + ": "
        elif self._in_search_text:
            self.search += data
            self._in_search_text = False
        elif self._in_title:
            self._current_pub.set_title(data[:-1])  # clip trailing .
            self._in_title = False
            self._expecting_authors = True
        elif self._in_authors:
            authors = data[:-1]                   # clip trailing .
            self._current_pub.set_authors(
                authors, get_canonical_first_author(authors))
            self._in_authors = False
        elif self._in_ref_details:
            # volume number, DOI
            parts = data.split(" doi: ")
            self._current_pub.ref += " " + parts[0][1:]  # clip leading .
            if len(parts) == 2:
                doi_parts = parts[1].split(" ")    # get rid of crap after DOI
                self._current_pub.canonical_doi = publication.to_canonical_doi(
                    doi_parts[0][0:-1])  # clip trailing .
            self._in_ref_details = False

        return(None)

    def handle_starttag(self, tag, attrs):
        # print("Tag", tag)
        # print("Attrs", attrs)

        if self._in_search and tag == "b":
            self._in_search_text = True
            self._in_search = False
        elif (tag == "a" and len(attrs) > 1 and attrs[1][0] == "ref" and
              "linkname=pubmed_pubmed" not in attrs[0][1]):
            self._current_pub = publication.Pub()
            self._current_pub_alert = pub_alert.PubAlert(
                self._current_pub, self)
            self.pub_alerts.append(self._current_pub_alert)
            self._current_pub.url = attrs[0][1]
            self._in_title = True
        elif tag == "td" and self._expecting_authors:
            # This case actually handled by handle_startendtag
            self._expecting_authors = False
            self._really_expecting_authors = True
        elif tag == "td" and self._really_expecting_authors:
            self._really_expecting_authors = False
            self._in_authors = True
        elif (tag == "span"
              and attrs[0][0] == "class"
              and attrs[0][1] == "jrnl"):
            # Title tag has better jrnl name than display
            self._current_pub.ref = attrs[1][1]
            self._in_ref = True

        return (None)

    def handle_endtag(self, tag):
        # print("EndTag", tag)
        if tag == "span" and self._in_ref:
            self._in_ref = False
            self._in_ref_details = True
        elif tag == "p" and self._in_senders_message:
            self._in_senders_message = False
        return (None)

    def handle_startendtag(self, tag, attrs):
        """
        Process tags like IMG and BR that don't have end tags.
        """

        # There's an important TD with no content we need to catch too.
        if tag == "td" and self._expecting_authors:
            self._expecting_authors = False
            self._really_expecting_authors = True

        return(None)


def get_canonical_first_author(ncbi_author_list):
    """Extract the first author's last name.

    NCBI author lists look like:
      Wreczycka K, Gosdschan A, Yusuf D, Grüning B, Assenov Y, Akalin A.
    """
    first_author = ncbi_author_list.split(",")[0]
    last_name = first_author.split(" ")[:-1]
    return publication.to_canonical(" ".join(last_name))

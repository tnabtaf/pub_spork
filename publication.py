#!/usr/local/bin/python3
"""
Publication objects.

A publication object describes an identified publication in whatever level
of detail we have.

The pub class is intended to be subclassed and different subclasses have
different types of information.

Pubs can come from
- Libraries (like CiteULike or Zotero)
- Alerts (like Google Scholar Emails or RSS feeds)
- A database of previously known pubs.

This would be called an abstract class in C.
"""

import inspect
import re
import ssl
import sys
import urllib.request

SSL_CONTEXT = ssl.SSLContext(ssl.PROTOCOL_TLS)

# Some publishers restrict access if you come in as Python
HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.10; "
        + "rv:62.0) Gecko/20100101 Firefox/62.0")
    }

# Cache any URLs that we have already checked for redirects.  Checking for
# redirects is expensive. Don't do it more than once for a URL.

redirect_cache = {}


class Pub(object):
    """An identified publication in whatever level of detail we have.

    Can come from many sources (and has equivalent subtypes for those
    sources.
    """

    def __init__(self):
        """Create an identified publication.

        This is only meant to be called by subclass constructors.  It is not
        meant to be invoked directly.

        Many of these fields are overwritten by subclass constructors.
        """
        self.title = ""                   # Unmodified title string
        self.canonical_title = None       # Lower, no spaces or non-alphanums
        self.canonical_doi = None         # just the DOI (no http..), lowercase
        self.url = None

        # Type of pub, if known. e.g., phd thesis, journal article, etc
        self.pub_type = None              # probably BibTeX
        self.authors = ""                 # Author list. No particular format
        # canonical name of first author: last name all lower case.
        self.canonical_first_author = None

        self.year = None                  # Publication year
        # TODO: maybe this should be a set?
        self.tags = None                  # List of Keywords for this pub
        self.journal_name = None          # Name if from a journal
        self.canonical_journal = None     # None if not from a journal
        self.ref = None                   # reference to pub
        self.entry_date = None            # Date added to library.

        return None

    def set_title(self, title):
        """Sets the title and canonical title of a pub."""
        self.title = title
        self.canonical_title = to_canonical(self.title)
        return self.canonical_title

    def set_authors(self, authors, canonical_first_author):
        self.authors = authors
        self.canonical_first_author = canonical_first_author
        return None


class PubLibrary(object):
    """A collection of publications.

    TODO: Should this inherit from list? Dictionary?
    """

    def __init__(self):
        """Create a collection of publications from a given source.

        This is only meant to be called by subclass constructors.  It is not
        meant to be invoked directly.

        Many of these fields are overwritten by subclass constructors.

        Libraries support several access methods:
          lookup by canonical DOI
          lookup by given title
          lookup by canonical title

        """
        self.url = None
        self.all_pubs = []
        self._by_canonical_title = {}
        self._by_canonical_doi = {}

        # These are populated by prep_for_reports
        self._by_year = None
        self._by_tag = None
        self._by_journal = None
        self._journal_alpha_rank = None
        self.journal_pubs_rank = None

        return None

    def add_pub(self, pub):
        """Add a populated publication to thelibrary."""
        self.all_pubs.append(pub)
        if pub.canonical_title is None or pub.canonical_title == "":
            # everything should have a title
            raise AssertionError("Pub has empty title")
        # TODO: This will overwrite anything with a duplicate title.
        self._by_canonical_title[pub.canonical_title] = pub
        # not everything has a doi
        if pub.canonical_doi:
            self._by_canonical_doi[pub.canonical_doi] = pub

        return None

    def __len__(self):
        """Return number of pubs in library."""
        # Every pub has a title.
        return(len(self.all_pubs))

    def get_by_canonical_title(self, canonical_title):
        """Given a canonical title string, return the pub for that title.

        If the title does not exist in the library then return None.
        """
        return self._by_canonical_title.get(canonical_title)

    def get_by_given_title(self, given_title):
        """Given and original, messy, mixed case pub title, return the pub.

        Returns None if pub title is not in library.
        """
        return self._by_canonical_title.get(to_canonical(given_title))

    def get_by_canonical_doi(self, canonical_doi):
        """Given a canonical doi, return the pub with that DOI.

        If the DOI does not exist in the library, return None.
        """
        return self._by_canonical_doi.get(canonical_doi)

    def prep_for_reports(self, only_these_tags_path=None):
        """Called by reporting programs to setup a bunch of quick-access
        data structures for reporting about the library.
        """

        # These are replaced by frozensets at the end.
        by_year = {}          # unordered array of papers from that year
        by_tag = {}           # value is unordered array of papers w/ tag
        by_journal = {}       # unordered list of papers in each journal

        sorted_by_journal = []  # sorted by canonical journal name

        if only_these_tags_path:
            # only pay attention to tags listed in the file.
            tag_file = open(only_these_tags_path, "r")
            for tag in tag_file:
                by_tag[tag.strip()] = []
            tag_file.close()

        # key is canonical Journal Name; value is alphabetized rank.
        self._journal_alpha_rank = {}

        for paper in self.all_pubs:

            # Process Year
            if paper.year == "unknown":
                # Fix these when you find them.
                print("Year UNKNOWN: " + paper.title, file=sys.stderr)
            if paper.year not in by_year:
                by_year[paper.year] = []
            by_year[paper.year].append(paper)

            # Process tags
            for tag in paper.tags:
                if only_these_tags_path:
                    if tag in by_tag:
                        by_tag[tag].append(paper)
                else:
                    if tag not in by_tag:
                        by_tag[tag] = []
                    by_tag[tag].append(paper)
            if len(paper.tags) == 0:
                # should not happen, flag it when it happens.
                print("Paper missing tags: " + paper.title, file=sys.stderr)

            # Process Journal
            jrnl = paper.canonical_journal
            if jrnl:
                if jrnl not in by_journal:
                    by_journal[jrnl] = []
                    sorted_by_journal.append(jrnl)
                by_journal[jrnl].append(paper)

        # create set versions
        self._by_year = {}
        for year in by_year:
            self._by_year[year] = frozenset(by_year[year])
        self._by_tag = {}
        for tag in by_tag:
            self._by_tag[tag] = frozenset(by_tag[tag])
        self._by_journal = {}
        for journal in by_journal:
            self._by_journal[journal] = frozenset(by_journal[journal])

        # create sorted list of Journal names
        sorted_by_journal.sort()
        for idx in range(len(sorted_by_journal)):
            self._journal_alpha_rank[sorted_by_journal[idx]] = idx

        # create list of Journal names sorted by most pubs.
        self.journal_pubs_rank = sorted(
            by_journal.values(),
            key=lambda jrnl_pubs: "{:09d}{}".format(
                len(self.all_pubs) - len(jrnl_pubs),
                jrnl_pubs[0].canonical_journal))

        return(None)

    def get_pubs(
            self,
            tag=None,
            year=None,
            journal=None,
            start_entry_date=None,
            end_entry_date=None):
        """
        Given any combination of tag, year, journal and/or startDate and
        endDate, return the only the set of papers that have the sepcified
        combination of values.
        """
        sets = []
        if tag:
            sets.append(self._by_tag[tag])
        if year:
            sets.append(self._by_year[year])
        if journal:
            sets.append(self._by_journal[journal])

        if len(sets) > 1:
            selected = sets[0]
            for restriction in sets[1:]:
                selected = selected.intersection(restriction)
        elif len(sets) == 1:
            selected = sets[0]
        else:  # sets is empty
            selected = frozenset(self.all_pubs)

        # apply date selections if present
        if start_entry_date or end_entry_date:
            match_dates = []
            for paper in selected:
                in_so_far = True
                if start_entry_date and paper.entry_date < start_entry_date:
                    in_so_far = False
                elif end_entry_date and paper.entry_date > end_entry_date:
                    in_so_far = False
                if in_so_far:
                    match_dates.append(paper)

            selected = match_dates

        return(selected)

    def get_years(self):
        """Return a list of years that papers were published in,
        in chronological order.
        """
        return(sorted(self._by_year.keys()))

    def get_tags(self):
        """Return a list of tags that have been assigned to pubs.  List is
        in sorted in alphabetical order.
        """
        return(sorted(self._by_tag.keys()))

    def gen_tag_url(self, tag):
        """Given a tag, generate a URL that points to collection
        of pubs with this tag in the online version of this library.

        This method is meant to be overridden by subclasses.
        """
        raise NotImplementedError(
            inspect.currentframe().f_code.co_name
            + "not implemented by subclass "
            + self.__class__.__name__)

    def gen_tag_year_url(self, tag, year):
        """Given a tag and a year, generate a URL thot shows all papers with
        that tag published in that year.

        This method is meant to be overridden by subclasses.
        """
        raise NotImplementedError(
            inspect.currentframe().f_code.co_name
            + "not implemented by subclass "
            + self.__class__.__name__)


def is_google_truncated_title(title_text):
    """Given a non-canonical title string, return true if it is a Google
    Scholar truncated title.

    These titles end with a non-breaking space and an ellipsis.
    """
    return title_text.endswith(" …")  # that's a non-breaking space.


def trim_google_truncate(title_text):
    """Given a title string, remove the Google truncate string from the end,
    if it is there.  If it isn't there, then return original text.
    """
    new_title = title_text
    if title_text.endswith("  …"):
        new_title = title_text[0:-3]
    elif title_text.endswith(" …"):
        new_title = title_text[0:-2]
    return new_title


def to_canonical(messy):
    """Convert a messy string to a canonical string.

    Canonical strings:
    - are all lower case
    - have spaces removed
    - have non-alphanumeric characters removed.

    This does not convert non-ascii chars to ascii, although that is worth
    thinking about.

    The canonical version of None is None.
    """
    if messy:
        return re.sub(r'\W+', '', messy).lower()
    return None


def is_canonical_doi(given_doi):
    """Return true if given_doi is already in canonical form.

    Canonical form means no leading http and starts with 10.
    """
    is_canonical = False
    if given_doi not in ["", None]:
        is_canonical = given_doi.startswith("10.")
    return is_canonical


def to_canonical_doi(given_doi):
    """Convert a possibly full, mixed case DOI, to just the DOI, all in
    lower case.

    Input DOIs can have these formats:
    - 10.1016/j.iheduc.2008.03.001
    - doi:10.1016/j.iheduc.2008.03.001
    - http://dx.doi.org/10.1016/j.iheduc.2008.03.001
    - https://doi.org/10.1016/j.iheduc.2008.03.001

    And in all sorts of mixed cases.

    The goal is to return
    10.1016/j.iheduc.2008.03.001

    Strip off everything before the leading 10. (The DOI spec allows / in
    the DOI, so can't use that.)

    The canonical version of
      None is None,
      the empty string is the empty string
      any non-doi string is that string (and a warning gets issued)
    """
    doi_only = given_doi
    if given_doi:
        # DOIs are officially case insensitive.
        doi_lower = given_doi.lower()
        # if it's a URL (with or without protocol), cut it to just the doi.
        # all DOIs start with 10.
        doi_start = doi_lower.find("10.")
        if doi_start == -1 and doi_lower != "":
            print(
                "Warning: DOI column not empty, but not a DOI: '" +
                given_doi + "'", file=sys.stderr)
            print("  Replacing with the empty string.\n", file=sys.stderr)
            doi_only = ""
        else:
            doi_only = doi_lower[doi_start:]

    return doi_only


def get_potentially_redirected_url(pub_url):
    """
    Some URLs (like DOIs) redirect to another URL.  Get that URL, or
    return the original URL if it does not redirect.
    """
    global redirect_cache
    if pub_url:
        if pub_url in redirect_cache:
            redirect_url = redirect_cache[pub_url]
        else:
            try:
                request = urllib.request.Request(
                    pub_url, headers=HTTP_HEADERS)
                url_response = urllib.request.urlopen(
                    request, context=SSL_CONTEXT)
                redirect_url = url_response.geturl()  # different if redirected
            except:
                print("Error: {0}".format(sys.exc_info()[0]), file=sys.stderr)
                print(
                    "  while processing URL: {0}\n".format(pub_url),
                    file=sys.stderr)
                redirect_url = pub_url
            redirect_cache[pub_url] = redirect_url
        return redirect_url

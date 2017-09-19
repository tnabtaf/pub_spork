#!/usr/local/bin/python3
"""CiteULike Publication objects.

Defines publications from CiteULike service.
"""

import json
import sys
import urllib.parse

import publication


SERVICE_NAME = "CiteULike"

# CUL URLs
#
# User library
#  http://www.citeulike.org/user/galaxyproject
# Group Library
#  http://www.citeulike.org/group/16008/library
# Particular tag in a user library
#  http://www.citeulike.org/user/galaxyproject/tag/methods
# Particular tag in a group library
#  http://www.citeulike.org/group/16008/tag/methods
# AND search in a user library
#  http://www.citeulike.org/search/username?q=tag%3Amethods+%26%26+year%3A2017&search=Search+library&username=galaxyproject
# AND search in a group library
#  http://www.citeulike.org/search/group?q=tag%3Amethods+%26%26+year%3A2017&search=Search+library&group_id=16008

# Group library in JSON format
#  http://www.citeulike.org/json/group/16008

CUL_BASE_URL = "http://www.citeulike.org"

CUL_SEARCH_LOGICAL_AND = "+%26%26+"              # " && "
CUL_SEARCH_YEAR = "year%3A"               # "year:"
CUL_SEARCH_TAG = "tag%3A"                # "tag:"

# append after user or group to get all papers with a tag.
CUL_TAG_SUFFIX = "/tag/"


class Pub(publication.Pub):
    """A publication defined in a CiteULike library.

    Initially (and probably forever) the original definition of CUL pubs
    comes from a CUL JSON export of the whole library.
    """
    def __init__(self, cul_json):
        """Create a CiteULike publication object from CUL JSON."""

        super(Pub, self).__init__()

        self._cul_json = cul_json
        self.title = self._cul_json["title"]
        self.canonical_title = publication.to_canonical(self.title)
        self.cul_id = self._cul_json["article_id"]
        doi = self._cul_json.get("doi")
        if doi:
            doi = publication.to_canonical_doi(doi)
        self.canonical_doi = doi
        self.url = self._cul_json["href"]

        # TODO: Type may not be the most useful. It's "JOUR" for
        # Journal Article and "THES" for thesis.  May not map to BibTeX.
        self.pub_type = self._cul_json.get("type")

        # Authors is a list of "First I. Last"
        author_list = self._cul_json.get("authors")
        if author_list:
            authors = ", ".join(author_list)
            self.set_authors(
                authors,
                self.to_canonical_first_author(author_list[0]))
        else:
            print("Warning: CUL Pub '{0}'".format(self.title), file=sys.stderr)
            print("  Does not have any authors.\n", file=sys.stderr)

        published = self._cul_json.get("published")
        if published:
            self.year = published[0]
        else:
            self.year = "unknown"
        self.tags = self._cul_json["tags"]  # a list
        journal = self._cul_json.get("journal")
        if journal:
            self.canonical_journal = publication.to_canonical(journal)
        else:
            self.canonical_journal = None

        # Entry date in CUL JSON looks like "date": "2016-12-22 00:18:58"
        self.entry_date = self._cul_json.get("date")[0:10]

        return None

    def to_canonical_first_author(self, cul_author_string):
        """Convert a CUL author name to a canonical first author name.

        CUL Author name is
          First M. Last

        Canonical first author is last name of first author.
        """
        if cul_author_string:
            by_dots = cul_author_string[0].split(".")
            if len(by_dots) > 1:
                # Last name is what follows the last period,
                first_author = by_dots[-1]
            else:
                # or if there is no period, then what follows the last space.
                first_author = cul_author_string.split()[-1]
            canonical_first_author = publication.to_canonical(first_author)
        else:
            canonical_first_author = None
        return canonical_first_author


class PubLibrary(publication.PubLibrary):
    """A collection of publications from CiteULike."""

    def __init__(self, cul_json_lib_path, cul_lib_url):
        """Given a file containing a CiteULike JSON export of a library,
        create a publication library containing all the pubs in that library.
        """
        super(PubLibrary, self).__init__()

        self.url = cul_lib_url
        # URL tell us if user or group library.
        self.is_user_lib = False
        self.is_group_lib = False
        url_parts = urllib.parse.urlparse(self.url)
        if url_parts.path.startswith("/user/"):  # "/user/galaxyproject
            self.is_user_lib = True
            self._cul_username = url_parts.path.split("/")[2]
        elif url_parts.path.startswith("/group/"):   # "/group/16008/library"
            self.is_group_lib = True
            self._cul_group_id = url_parts.path.split("/")[2]
        else:
            raise ValueError(
                "Library URL is not recognized as group or user: "
                + self.url)

        cul_file = open(cul_json_lib_path, "r")
        cul_json = json.load(cul_file)  # read it all at once.

        for cul_pub_json in cul_json:
            cul_pub = Pub(cul_pub_json)
            self.add_pub(cul_pub)

        cul_file.close()
        self.num_pubs = len(self._by_canonical_title)

        return None

    def gen_tag_year_url(self, tag, year):
        """Given a tag and a year, generate a URL thot shows all papers with
        that tag published in that year.

        """
        if self.is_user_lib:
            tag_year_url = (
                CUL_BASE_URL
                + "/search/username?search=Search+library&username="
                + self._cul_username
                + "&q="
                + CUL_SEARCH_TAG + tag
                + CUL_SEARCH_LOGICAL_AND
                + CUL_SEARCH_YEAR + year)
        elif self.is_group_lib:
            tag_year_url = (
                CUL_BASE_URL
                + "/search/group?search=Search+library&group_id="
                + self._cul_group_id
                + "&q="
                + CUL_SEARCH_TAG + tag
                + CUL_SEARCH_LOGICAL_AND
                + CUL_SEARCH_YEAR + year)

        return tag_year_url

    def gen_tag_url(self, tag):
        """Given the base URL of a CUL library, e.g., 
        http://www.citeulike.org/group/16008/library

        and a tag used in that library, generate a link to all pubs with that 
        tag.
        """
        if self.is_user_lib:
            tag_url = (
                CUL_BASE_URL
                + "/user/"
                + self._cul_username
                + CUL_TAG_SUFFIX
                + tag)
        elif self.is_group_lib:
            tag_url = (
                CUL_BASE_URL
                + "/group/"
                + self._cul_group_id
                + CUL_TAG_SUFFIX
                + tag)

        return tag_url

    def gen_pub_url_in_lib(self, pub):
        """given a pub in this library, generate a link to it online."""
        
        pub_url = self.url + "/article/" + pub.cul_id
        return pub_url

    
def gen_add_pub_html_link(pub_url):
    """Given the URL of a publication, generate a link to add that pub to
    CiteULike.
    """
    return (
        '<a href="http://www.citeulike.org/posturl?url={0}" '
        + 'target="citeulike-add">Submit pub to CiteULike</a>').format(
            pub_url)             # TODO: Does this need to be URLencoded?



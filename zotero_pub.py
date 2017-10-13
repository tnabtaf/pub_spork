#!/usr/local/bin/python3
"""Zotero Publication objects.

Defines publications from Zotero service.
"""

import csv
import sys
import urllib.parse

import publication

# Zotero URLs
#
# User library
#  https://www.zotero.org/tnabtaf/items
#
# Group Library
#  https://www.zotero.org/groups/1724202/testing_groups/items
#
# Particular pub in a user lib
#  https://www.zotero.org/tnabtaf/items/itemKey/CA6MRM7W
#
# Particular tag in a user library
#  https://www.zotero.org/tnabtaf/items/tag/cloud/
#
# Particular tag in a group library
#  
# AND search for two tags in a user library
#  https://www.zotero.org/tnabtaf/items/tag/cloud/tag/ultimate
#
# AND serach for one tag and one term in Title, creator, year only
#  https://www.zotero.org/tnabtaf/items/q/2015/tag/cloud
#
# AND search for one tag and onoe term in all fields
#  https://www.zotero.org/tnabtaf/items/q/2015/qmode/everything/tag/cloud
#
# search in a user library, Title, creator and year only
#  https://www.zotero.org/tnabtaf/items/q/afgan
#
# search in a user library, Title, all fields
#  https://www.zotero.org/tnabtaf/items/q/afgan/qmode/everything
#
# Does not appear to support AND/OR searches. Can do that through client.
# Group library in CSV format
#  

SERVICE_NAME = "Zotero"

ZOTERO_BASE_URL = "https://www.zotero.org"

# append after user or group to get all papers with a tag.
ZOTERO_TAG_SUFFIX = ""


class Pub(publication.Pub):
    """A publication defined in a Zotero library.

    The definition comes from a CSV export of a library.
    """
    def __init__(self, zot_csv):
        """Create a Zotero publication object from a Zotero CSV entry."""

        super(Pub, self).__init__()

        self._zot_csv = zot_csv
        self.title = self._zot_csv["Title"]
        self.canonical_title = publication.to_canonical(self.title)
        self.zotero_id = self._zot_csv['\ufeff"Key"'] # BOM won't go away
        doi = self._zot_csv.get("DOI")
        if doi:  # should be close to canonical already
            doi = publication.to_canonical_doi(doi)
        self.canonical_doi = doi
        self.url = self._zot_csv["Url"]  # Can be empty

        # Authors is a semicolon separated list of "Last, First I."
        authors = self._zot_csv.get("Author")
        if authors:
            self.set_authors(
                authors,
                self.to_canonical_first_author(authors))
        else:
            print(
                "Warning: Zotero Pub '{0}'".format(self.title),
                file=sys.stderr)
            print("  Does not have any authors.\n", file=sys.stderr)

        self.year = self._zot_csv.get("Publication Year")
        if not self.year:
            self.year = "unknown"
            print(
                "Warning: Zotero Pub '{0}'".format(self.title),
                file=sys.stderr)
            print("  Does not have a publication year.\n", file=sys.stderr)

        # Tags are a semicolon separated list
        self.tags = self._zot_csv["Manual Tags"].split("; ")

        if self._zot_csv["Item Type"] == "journalArticle":
            self.journal_name = self._zot_csv["Publication Title"]
            self.canonical_journal = publication.to_canonical(
                self.journal_name)
        else:
            self.canonical_journal = None

        # Entry date in Zotero CSV looks like "date": "2017-09-14 17:48:40"
        self.entry_date = self._zot_csv.get("Date Added")[0:10]

        return None

    def to_canonical_first_author(self, zot_author_string):
        """Convert a Zotero author list to a canonical first author name.

        A Zotero author list looks like:
          Gloaguen, Yoann; Morton, Fraser; Daly, Rónán; Gurden, Ross

        Canonical first author is last name of first author.
        """
        if zot_author_string:
            last_name = zot_author_string.split(",")[0]
            canonical_first_author = publication.to_canonical(last_name)
        else:
            canonical_first_author = None
        return canonical_first_author
        

class PubLibrary(publication.PubLibrary):
    """A collection of publications from Zotero."""

    def __init__(self, zot_csv_lib_path, zot_lib_url):
        """Given a file containing a Zotero CSV export of a library,
        create a publication library containing all the pubs in that library.
        """
        super(PubLibrary, self).__init__()

        self.url = zot_lib_url
        # URL tell us if user or group library.
        self.is_user_lib = False
        self.is_group_lib = False
        url_parts = urllib.parse.urlparse(self.url)
        # /groups/1724202/testing_groups/items
        if url_parts.path.startswith("/groups/"):
            self.is_group_lib = True
            parts = url_parts.path.split("/")
            self._zot_group_id = parts[2]
            self._zot_group_name = parts[3]
        else: # https://www.zotero.org/tnabtaf/items
            self.is_user_lib = True
            self._zot_username = url_parts.path.split("/")[1]

        zot_file = open(zot_csv_lib_path, "r")
        zot_reader = csv.DictReader(zot_file)

        for zot_pub_csv in zot_reader:
            zot_pub = Pub(zot_pub_csv)
            self.add_pub(zot_pub)

        zot_file.close()
        self.num_pubs = len(self.all_pubs)

        return None

    def gen_tag_url(self, tag):
        """Given a tag, generate the URL that shows all papers with that tag.
        """
        tag_url = self.url + "tag/" + tag

        return tag_url

    def gen_year_url(self, year):
        """Given a year, generate a URL thot shows all papers published in 
        that year.
        
        This can't be done in Zotero.  Return None
        """
        return None

    def gen_tag_year_url(self, tag, year):
        """Given a tag and a year, generate a URL thot shows all papers with
        that tag published in that year.

        This can't be done in Zotero.  Return None.
        """
        return None

    def gen_pub_url_in_lib(self, pub):
        """given a pub in this library, generate a link to it online."""
        
        pub_url = self.url + "/itemKey/" + pub.zotero_id
        return pub_url

def gen_add_pub_html_link(pub_url):
    """Given the URL of a publication, generate a link to add that pub to
    Zotero.  
    """
    return None


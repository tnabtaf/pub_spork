#!/usr/local/bin/python3
"""
Database of known publications.

Known publications are things we have already seen. They can be from a library
of pubs, previous alerts, or a previous version of a known pub database.  They
are typicallly created when processing new alerts.
"""

import csv
import sys

import cul_pub
import publication

STATE_NEW = "new"             # Not in library, and hasn't been curated yet.
STATE_INLIB = "inlib"         # Is in library of papers
STATE_IGNORE = "ignore"       # Looked at, wasn't relevant or can't add
STATE_WAIT = "wait"           # Looked at, but waiting on something to decide
STATE_EXCLUDE = "exclude"     # Pub reported by an exclude aler, meaning, it
                              # is almost certainly a false positive. 

# This state should never get wriiten out. Exists only in memory.
STATE_DONT_KNOW_YET = "dont-know-yet"


# Columns
TITLE = "title"
AUTHORS = "authors"
DOI = "doi"
STATE = "state"
ANNOTATION = "annotation"
QUALIFIER = "qualifier"

COLUMNS = [
    TITLE,                                # Unmunged title
    AUTHORS,                              # In whatever format we get it.
    DOI,                                  # always stored in 10.xxx... format
    STATE,                                # What do we know about this
    ANNOTATION,                           # Main comment / reason
    QUALIFIER,                            # Secondary comment / reason
    ]


class KnownPubDBEntry(object):
    """A single entry in a known pubs database."""

    def __init__(self, row=None):
        """Initialize a single KnownPubDB entry.
        If a row (from a DB) is given, initialize the entry with the values
        in the row.  Row is a dictionary with COLUMNS for keys.
        If no row is given, create an empty entry.
        """
        self._row = row
        if self._row:
            self._canonical_title = publication.to_canonical(self._row[TITLE])
            self.set_doi(self._row[DOI])  # make sure it's in canonical form
        else:
            self._row = {}
            self.set_title(None)  # also sets _canonical_title
            self.set_authors(None)
            self.set_doi(None)
            self.set_state(STATE_DONT_KNOW_YET)
            self.set_annotation("")
            self.set_qualifier("")

        return None

    def set_title(self, title):
        self._row[TITLE] = title
        self._canonical_title = publication.to_canonical(self._row[TITLE])
        return None

    def get_title(self):
        return self._row[TITLE]

    def get_canonical_title(self):
        return self._canonical_title

    def set_authors(self, authors):
        self._row[AUTHORS] = authors
        return None

    def get_authors(self):
        return self._row[AUTHORS]

    def set_doi(self, doi):
        self._row[DOI] = publication.to_canonical_doi(doi)
        return None

    def get_doi(self):
        doi = self._row[DOI]
        if doi is not None and doi == "":
            doi = None
        return doi

    def set_state(self, state):
        self._row[STATE] = state
        return None

    def get_state(self):
        return self._row[STATE]

    def set_annotation(self, annotation):
        self._row[ANNOTATION] = annotation
        return None

    def get_annotation(self):
        return self._row[ANNOTATION]

    def set_qualifier(self, qualifier):
        self._row[QUALIFIER] = qualifier
        return None

    def get_qualifier(self):
        return self._row[QUALIFIER]

    @staticmethod
    def gen_separator_entry():
        """Create an entry that is used as a separator between different parts
        of the database."""
        entry = KnownPubDBEntry()
        entry.set_title("**************** SECTION SEPARATOR ****************")
        entry.set_authors("")
        entry.set_doi("")
        entry.set_state("SEPARATOR")
        entry.set_annotation("")
        entry.set_qualifier("")

        return entry


class KnownPubDB(object):
    """A database of known publications."""

    def __init__(self, known_pubs_file_path=None):
        """Create a database of known pubs.
        If a path is given then initialize the DB.
        If no path is given then create an empty DB.
        """
        self.by_canonical_title = {}
        self.by_canonical_doi = {}
        if known_pubs_file_path:
            tsv_in = open(known_pubs_file_path, "r")
            tsv_reader = csv.DictReader(
                tsv_in, dialect="excel-tab")  # fieldnames=COLUMNS
            for row in tsv_reader:
                db_entry = KnownPubDBEntry(row)
                self.add_known_pub(db_entry)

            tsv_in.close()

        return None

    def add_known_pub(self, known_pub):
        """Given a known pub, add it to the in-memory database."""
        # everything has a title
        canonical_title = known_pub.get_canonical_title()
        self.by_canonical_title[canonical_title] = known_pub
        # not everything has a doi:
        doi = known_pub.get_doi()
        if publication.is_canonical_doi(doi):
            self.by_canonical_doi[doi] = known_pub

        return None

    def get_all_known_pubs(self):
        """Return all known pubs in no particular order"""
        return self.by_canonical_title.values()

    def add_pubs_from_matchups(self, pub_matchups):
        """Add pubs in the list of matchups to the database (in preparation
        for writing out a new version of the database).

        Assumes that pubs in list are not already in known pub db.
        """
        for pub_match in pub_matchups:
            known_pub = KnownPubDBEntry()
            known_pub.set_title(pub_match.get_pub_title())
            known_pub.set_authors(pub_match.get_pub_authors())
            known_pub.set_doi(pub_match.get_pub_doi())
            if pub_match.is_all_excludes():
                known_pub.set_state(STATE_EXCLUDE)
                if not known_pub.get_annotation():
                    known_pub.set_annotation(
                        pub_match.get_first_alert_search())
            else:
                if pub_match.is_lib_pub():
                    known_pub.set_state(STATE_INLIB)
                else:
                    known_pub.set_state(STATE_NEW)
                known_pub.set_annotation("")
                known_pub.set_qualifier("")
            self.add_known_pub(known_pub)

        return None

    def write_db_to_file(self, out_db_path):
        """Given a path to write the DB to, write it out.

        This method writes the DB to a TSV file with this format:
        1) Entries that are new and wiating are listed first, in alphabetical
           order of canonical title
        # 2) A separator is written  NO IT'S NOT.
        3) Everything else is written out.
        """
        db_out = open(out_db_path, "w")
        db_writer = csv.DictWriter(
            db_out, fieldnames=COLUMNS, dialect="excel-tab")
        db_writer.writeheader()

        # walk through library, sorting into two groups, based on state
        active_entries = []
        exclude_entries = []
        past_entries = []
        bizarre_entries = []

        for entry in self.by_canonical_title.values():
            entry_state = entry.get_state()
            if entry_state in [STATE_NEW, STATE_WAIT]:
                active_entries.append(entry)
            elif entry_state in [STATE_EXCLUDE, STATE_IGNORE, STATE_INLIB]:
                past_entries.append(entry)
            else:
                print(
                    ("Warning: Entry with unkown state '{0}' "
                     + "written to DB.").format(entry_state),
                    file=sys.stderr)
                print(
                    "  Title: {0}".format(entry.get_title()),
                    file=sys.stderr)
                print("", file=sys.stderr)
                bizarre_entries.append(entry)

        # separator_entry = KnownPubDBEntry.gen_separator_entry()
        for entry_list in [active_entries, past_entries, bizarre_entries]:
            entry_list.sort(key=lambda entry: entry.get_canonical_title())
            for entry in entry_list:
                db_writer.writerow(entry._row)
            # db_writer.writerow(separator_entry._row)

        return None

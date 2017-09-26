#!/usr/local/bin/python3
"""
Database of known publications.

Known publications are things we have already seen. They can be from a library
of pubs, previous alerts, or a previous version of a known pub database.  They
are typicallly created when processing new alerts.
"""

import bisect                      # sorted lists and binary search
import csv
import sys

import cul_pub
import publication

STATE_NEW = "new"             # Not in library, and hasn't been curated yet.
STATE_INLIB = "inlib"         # Is in library of papers
STATE_IGNORE = "ignore"       # Looked at, wasn't relevant or can't add
STATE_WAIT = "wait"           # Looked at, but waiting on something to decide
STATE_CANT_GUESS = "cant-guess"

# This state should never get wriiten out. Exists only in memory.
STATE_DONT_KNOW_YET = "dont-know-yet"


# Columns
TITLE = "title"
AUTHORS = "authors"
DOI = "doi"
STATE = "state"
ANNOTATION = "annotation"

COLUMNS = [
    TITLE,                                # Unmunged title
    AUTHORS,                              # In whatever format we get it.
    DOI,                                  # always stored in 10.xxx... format
    STATE,                                # What do we know about this
    ANNOTATION                            # and whatever else we have to say
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

    def meld(self, new_pub_info):
        """Given a known pub object that contains potentially new
        information about this pub, meld the new information into this pub.
        """
        my_title = self.get_title()
        if not my_title:
            self.set_title(new_pub_info.get_title())
        elif publication.is_google_truncated_title(my_title):
            # We already have a title, but it's been shortened by Google.
            # If we now have a longer title, use it.
            new_title = new_pub_info.get_title()
            if new_title and len(new_title) > len(my_title):
                self.set_title(new_title)

        if not self.get_authors():
            self.set_authors(new_pub_info.get_authors())
        if not self.get_doi():
            self.set_doi(new_pub_info.get_doi())
        if self.get_annotation() == "":
            # tend to meld older entries onto more recent ones.
            # Thus keep older annotation, if we have it.
            self.set_annotation(new_pub_info.get_annotation())

        # TODO: Figure out if we should be doing something with STATE.
        return None

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

        return entry


class KnownPubDB(object):
    """A database of known publicatoins."""

    def __init__(self, known_pubs_file_path=None):
        """Create a database of known pubs.
        If a path is given then initialize the DB.
        If no path is given then create an empty DB.
        """
        self.by_canonical_title = {}
        self.by_canonical_doi = {}
        self.canonical_titles_sorted = []     # use bisect with this.
        if known_pubs_file_path:
            tsv_in = open(known_pubs_file_path, "r")
            tsv_reader = csv.DictReader(
                tsv_in, dialect="excel-tab")  # fieldnames=COLUMNS
            for row in tsv_reader:
                db_entry = KnownPubDBEntry(row)
                self.add_known_pub(db_entry)

            tsv_in.close()

        return None

    def add_cul_lib_json(self, cul_lib_path):
        """Add the pubs in a CUL Lib to an empty pubs db."""
        # read everything in.
        cul_lib = cul_pub.PubLibrary(cul_lib_path)

        # create a known_pub for every entry
        for pub in cul_lib.allPapers():
            # convert old_entry to happy new entry
            known_pub = KnownPubDBEntry()
            known_pub.set_title(pub.get_title())
            known_pub.set_authors(pub.get_authors())
            known_pub.set_doi(pub.get_doi())
            known_pub.set_annotation("Imported from CUL")
            known_pub.set_state(STATE_INLIB)
            # we are converted.
            self.add_known_pub(known_pub)
        return None

    def add_known_pub(self, known_pub):
        """Given a known pub, add it to the in-memory database."""
        # everything has a title
        canonical_title = known_pub.get_canonical_title()
        self.by_canonical_title[canonical_title] = known_pub
        bisect.insort(self.canonical_titles_sorted, canonical_title)
        # not everything has a doi:
        doi = known_pub.get_doi()
        if publication.is_canonical_doi(doi):
            self.by_canonical_doi[doi] = known_pub

        return None

    def get_by_title(self, title):
        """Given a title string, return the entry for that title.  If no
        entry exists then return None.
        """
        canonical_title = publication.to_canonical(title)
        known_pub = self.by_canonical_title.get(canonical_title)
        if not known_pub:
            if publication.is_google_truncated_title(title):
                # new title is Google truncated.
                canonical_trimmed_title = (
                    publication.trim_google_truncate(canonical_title))

                # Find an item with a longer title
                full_title_i = bisect.bisect_left(
                    self.canonical_titles_sorted, canonical_trimmed_title)
                if (full_title_i != len(self.canonical_titles_sorted)
                    and self.canonical_titles_sorted[full_title_i].startswith(
                        canonical_trimmed_title)):
                    known_pub = self.by_canonical_title[
                        self.canonical_titles_sorted[full_title_i]]

        return known_pub

    def get_all_known_pubs(self):
        """Return all known pubs in no particular oder"""
        return self.by_canonical_title.values()

    def get_match(self, new_pub):
        """Given a known pub object, see if there is already a record for
        that pub in the DB. If there is, return it. If not, return None.
        """
        # what constitutes a match?
        # - DOIs match and titles don't contradict.
        # - One or both DOIs missing, but titles agree.
        doi = new_pub.get_doi()
        matched_pub = self.by_canonical_doi.get(doi)
        if not matched_pub:
            # Well, dang, didn't match on doi.  Try title
            matched_pub = self.by_canonical_title.get(
                new_pub.get_canonical_title())
            if not matched_pub:
                # last chance: if either is Google Truncated
                if (publication.is_google_truncated_title(
                        new_pub.get_title())):
                    # new title is Google truncated.
                    canonical_trimmed_title = (
                        publication.to_canonical(
                            publication.trim_google_truncate(
                                new_pub.get_title())))

                    # Find an item with a longer title'
                    full_title_i = bisect.bisect_left(
                        self.canonical_titles_sorted, canonical_trimmed_title)
                    if full_title_i != len(self.canonical_titles_sorted) and (
                            self.canonical_titles_sorted[
                                full_title_i].startswith(
                                canonical_trimmed_title)):
                        matched_pub = self.by_canonical_title[
                            self.canonical_titles_sorted[full_title_i]]

        return matched_pub

    def meld(self, known_pub_in_db, new_pub_info):
        """Given a known pub in this database, and a known pub object
        (that is not in this database) that contains potentially new
        information about the first known pub, meld the new information
        into the known pub in this db.
        """
        old_canonical_title = known_pub_in_db.get_canonical_title()
        known_pub_in_db.meld(new_pub_info)
        new_canonical_title = known_pub_in_db.get_canonical_title()
        if old_canonical_title != new_canonical_title:
            # Canonical title was changed
            del self.by_canonical_title[old_canonical_title]
            self.by_canonical_title[new_canonical_title] = known_pub_in_db

            # delete the the old entry
            old_i = bisect.bisect_left(
                self.canonical_titles_sorted, old_canonical_title)
            if (old_i != len(self.canonical_titles_sorted)
                and self.canonical_titles_sorted[old_i] ==
                    old_canonical_title):
                del self.canonical_titles_sorted[old_i]
                bisect.insort(
                    self.canonical_titles_sorted, new_canonical_title)
            else:
                raise ValueError(
                    "Not finding prior value in canonical_titles_sorted.\n"
                    + "  " + old_canonical_title)

        doi = known_pub_in_db.get_doi()
        if publication.is_canonical_doi(doi) and (
                doi not in self.by_canonical_doi):
            self.by_canonical_doi[doi] = known_pub_in_db

        return None

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
            if pub_match.is_lib_pub():
                known_pub.set_state(STATE_INLIB)
            else:
                known_pub.set_state(STATE_NEW)
            known_pub.set_annotation("")
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
        past_entries = []
        bizarre_entries = []

        for entry in self.by_canonical_title.values():
            entry_state = entry.get_state()
            if entry_state in [STATE_NEW, STATE_WAIT]:
                active_entries.append(entry)
            elif entry_state in [STATE_IGNORE, STATE_INLIB]:
                past_entries.append(entry)
            else:
                print(
                    ("Warning: Entry with unkown state '{0}' "
                     + "written to DB.").format(entry_state),
                    file=sys.stderr)
                print(
                    "  Title: {0}".format(entry.get_title()),
                    file=sys.stderr)
                if entry_state == STATE_CANT_GUESS:
                    print("  Saving as WAIT state.\n", file=sys.stderr)
                    entry.set_state(STATE_WAIT)
                    active_entries.append(entry)
                else:
                    print("", file=sys.stderr)
                    bizarre_entries.append(entry)

        # separator_entry = KnownPubDBEntry.gen_separator_entry()
        for entry_list in [active_entries, past_entries, bizarre_entries]:
            entry_list.sort(key=lambda entry: entry.get_canonical_title())
            for entry in entry_list:
                db_writer.writerow(entry._row)
            # db_writer.writerow(separator_entry._row)

        return None

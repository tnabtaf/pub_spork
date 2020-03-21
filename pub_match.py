#!/usr/local/bin/python3
"""Tracks matches of pubs from different sources, including
- alerts
- libraries
- known pubs / history (but not yet)
"""

import bisect
import sys

import email_alert_gs
import known_pub_db
import publication


class PubMatch(object):
    """A pub match is a collection of pubs that we believe are all the same
    pub.
    """

    def __init__(self, lib_pub=None, pub_alerts=None):
        """Create a pub_match.  Can contain a library pub and/or
        a list of pub_alerts (which each contain a pub). Can't be empty
        """
        if not (lib_pub or pub_alerts):
            raise AssertionError("Attempt to create an empty pub_match.")

        self._lib_pub = None
        self.canonical_doi = None
        self.canonical_title = None
        self.canonical_first_author = None

        self.set_lib_pub(lib_pub)
        self._pub_alerts = []
        self._known_pub = None
        self.add_pub_alerts(pub_alerts)

        return None

    def is_new(self):
        """Returns true if a pub_match represents a previously unknown pub.

        Previously unknown pubs don't have a library pub - only PubAlerts.
        """
        return (self._lib_pub is None)

    def is_known(self):
        """Returns true if a pub_match represents a previously known pub.

        Previously known pubs have a library pub or a known pub
        """
        return (self._lib_pub is not None or self._known_pub is not None)

    def is_lib_pub(self):
        """Return true if this pub exists in library."""
        return self._lib_pub

    def set_lib_pub(self, lib_pub):
        if lib_pub:
            self._lib_pub = lib_pub
            self.canonical_doi = self._lib_pub.canonical_doi
            self.canonical_title = self._lib_pub.canonical_title
            self.canonical_first_author = self._lib_pub.canonical_first_author
        return None

    def get_lib_pub(self):
        """Return the library pub for this matchup.  Will be None if the
        there is not a matching paper in the library.
        """
        return self._lib_pub

    def add_pub_alert(self, pub_alert):
        """Add a single PubAlert to this matchup's list of pub_alerts."""

        self._pub_alerts.append(pub_alert)

        # if matchup doesn't have canonical info yet, add it from alert.
        # DOI
        if pub_alert.pub.canonical_doi:
            if self.canonical_doi:
                if pub_alert.pub.canonical_doi != self.canonical_doi:
                    print(
                        "DOIs disagree for: "
                        + "{0}".format(self.canonical_title),
                        file=sys.stderr)
                    print(
                        "  DOI 1: {0}".format(self.canonical_doi),
                        file=sys.stderr)
                    print(
                        "  DOI 2: {0}".format(pub_alert.pub.canonical_doi),
                        file=sys.stderr)
            else:  # match doesn't yet have a canonical DOI.
                self.canonical_doi = pub_alert.pub.canonical_doi

        # Title
        if pub_alert.pub.canonical_title and not self.canonical_title:
            # Titles are really noisy, don't check that they are the same.
            # Worried? Don't be. Everything in the pub_alerts list has
            # already been matched on title or DOI.
            self.canonical_title = pub_alert.pub.canonical_title

        # first author
        if pub_alert.pub.canonical_first_author and not (
                self.canonical_first_author):
            # First authors are also really noisy.
            self.canonical_first_author = pub_alert.pub.canonical_first_author
        return self._pub_alerts

    def add_pub_alerts(self, pub_alerts):
        """Add a list of 0, 1, or more pub_alerts to matchup.

        If the matchup does not have canonical DOI, etc yet, then pull it from
        the new alerts.
        """
        if not pub_alerts:
            return self._pub_alerts

        # add pub alerts one at a time.
        for pa in pub_alerts:
            self.add_pub_alert(pa)
        return self._pub_alerts

    def set_known_pub(self, known_pub):
        """Assign a known pub to this match.  This is none if we haven't seen
        the pub before.
        """
        self._known_pub = known_pub

    def get_pub_title(self):
        """Return the (unmunged) title of the publication."""

        # Challenge is that we the canonical title, but not the title.
        title = None
        if self._lib_pub:
            title = self._lib_pub.title
        else:  # have to look in pub_alerts
            for pa in self._pub_alerts:
                if pa.pub.title:
                    title = pa.pub.title
                    break
        return title

    def get_pub_authors(self):
        """Return the (unmunged) list of authors of this pub."""

        authors = None
        if self._lib_pub:
            authors = self._lib_pub.authors
        else:  # have to look in pub_alerts
            for pa in self._pub_alerts:
                if pa.pub.authors:
                    authors = pa.pub.authors
                    break
        return authors

    def get_pub_doi(self):
        """Return the DOI of this pub."""

        doi = None
        if self._lib_pub:
            doi = self._lib_pub.canonical_doi
        if not doi:  # have to look in pub_alerts
            for pa in self._pub_alerts:
                if pa.pub.canonical_doi:
                    doi = pa.pub.canonical_doi
                    break
        return doi

    def get_pub_url(self):
        """Return the URL of the publication in it's native location."""
        if self.is_lib_pub():
            pub_url = self._lib_pub.url
        else:
            pub_url = None
            for pub_alert in self._pub_alerts:
                if pub_alert.pub.url:
                    pub_url = pub_alert.pub.url
                    break
        return pub_url

    def to_html(self, exclude_db):
        """Render the PubMatch in HTML."""

        output = []

        # describe the pub.
        output.append('<p style="font-size: 140%;"><strong>')
        output.append('{0}'.format(self.get_pub_title()))
        output.append('</strong></p>')
        output.append('<p>{0}</p>'.format(self.get_pub_authors()))

        # describe the pub_alerts
        if len(self._pub_alerts) > 0:
            output.append('<p>Alerts for this pub:</p>')
            output.append('<ol>')
            # Want pub_alerts to always come out in the same order.
            # Helps with diff'ing.
            pub_alerts_sorted = sorted(
                self._pub_alerts,
                key=lambda pub_alert: pub_alert.alert.search)
            for pa in pub_alerts_sorted:
                if exclude_db.is_an_exclude_alert(pa.alert):
                    li_style = ' style="background-color: yellow;"'
                else:
                    li_style = ''
                output.append(
                    '<li {0}><strong> {1} </strong>'.format(
                        li_style,
                        pa.alert.get_search_text_with_alert_source()))
                output.append('<ul>')
                if pa.pub.ref:
                    output.append(
                        '<ul><li> {0}</li></ul>'.format(pa.pub.ref))
                if pa.text_from_pub:
                    output.append(
                        '<ul><li> {0}</li></ul>'.format(pa.text_from_pub))
                output.append('</ul></li>')
            output.append('</ol>')
        return '\n'.join(output)


class PubMatchDB(object):
    """A database of PubMatch objects.  Provides direct access to
    individual PubMatch objects.
    """

    def __init__(
            self, pub_library, pub_alerts, known_pubs_db=None,
            ok_dup_titles=None):
        """Create a PubMatch database, given an input publication library, an
        optional db of known pubs, and a list of new pub alerts.
        """
        # Provide quick access via title and DOI
        self._by_canonical_doi = {}
        self._by_canonical_title = {}
        self.canonical_titles_sorted = []     # use bisect with this.

        # Procss duplicate pub titles that should be ignored.
        self._ok_dups_by_canonical_title = set()
        if ok_dup_titles:
            for ok_title in ok_dup_titles:
                self._ok_dups_by_canonical_title.add(
                    publication.to_canonical(ok_title))

        # Create PubMatch's for every entry in the library.
        for lib_pub in pub_library.get_pubs():
            self.add_pub_match(PubMatch(lib_pub=lib_pub))

        # walk through pub_alerts, adding them to exising PubMatch's or
        # creating new ones when needed.
        self.add_pub_alerts(pub_alerts)
        if known_pubs_db:
            self.add_known_pub_info(known_pubs_db)

        return None

    def add_pub_match(self, pub_match):
        """Add a PubMatch entry to the DB."""
        if pub_match.canonical_doi:
            if pub_match.canonical_doi in self._by_canonical_doi:
                print(
                    "Warning: DOI: {0} in library more than once.".format(
                        pub_match.canonical_doi),
                    file=sys.stderr)
                print(
                    "  title: {0}\n".format(pub_match._lib_pub.title),
                    file=sys.stderr)
            self._by_canonical_doi[pub_match.canonical_doi] = pub_match

        if pub_match.canonical_title:
            if (pub_match.canonical_title in self._by_canonical_title
                    and pub_match.canonical_title
                    not in self._ok_dups_by_canonical_title):
                print(
                    "Warning: Title in library more than once.",
                    file=sys.stderr)
                print(
                    "  title: {0}\n".format(pub_match._lib_pub.title),
                    file=sys.stderr)
            self._by_canonical_title[pub_match.canonical_title] = pub_match
            bisect.insort(
                self.canonical_titles_sorted, pub_match.canonical_title)

        return None

    def add_pub_alerts(self, pub_alerts):
        """Add list of pub_alerts: add them to exising PubMatch's or
        create new ones when needed.
        """
        for pa in pub_alerts:
            pub_match = None
            if pa.pub.canonical_doi:
                pub_match = self._by_canonical_doi.get(
                    pa.pub.canonical_doi)
            if not pub_match and pa.pub.canonical_title:
                pub_match = self._by_canonical_title.get(
                    pa.pub.canonical_title)
            # TODO: need to deal with Google truncate here.
            # Need to search pub match DB for shorter version
            # of papers title
            # Not dealing with situation where first title found is the
            # truncated one, and then the longer one is added later.
            # Hmm. to deal with that we need to know the minimum length of a
            # truncated Google title.  Otherwise we'll match is short titles
            # erroneously.
            # Deal with this in high-level else below.
            if (not pub_match and
                    publication.is_google_truncated_title(pa.pub.title)):
                # title from alert is Google truncated.
                # Find an item with a longer title
                full_title_i = bisect.bisect_left(
                    self.canonical_titles_sorted, pa.pub.canonical_title)
                if (full_title_i != len(self.canonical_titles_sorted)
                    and self.canonical_titles_sorted[full_title_i].startswith(
                        pa.pub.canonical_title)):
                    pub_match = self._by_canonical_title[
                        self.canonical_titles_sorted[full_title_i]]
            elif (not pub_match and
                    len(pa.pub.title) >=
                    email_alert_gs.MIN_TRUNCATED_TITLE_LEN):
                # didn't find a match and new alert is not google truncated.
                # But, the new alert has a long title and could be the same
                # as a truncated pub title that we already added in this run.
                # If so, then we already have a pub_match, but it has the
                # short title in it.
                # Look for matching, truncated title
                possible_match_i = bisect.bisect_left(
                    self.canonical_titles_sorted,
                    pa.pub.canonical_title[
                        0:email_alert_gs.MIN_TRUNCATED_TITLE_LEN])
                if (possible_match_i != len(self.canonical_titles_sorted)
                    and
                    self.canonical_titles_sorted[possible_match_i].startswith(
                        pa.pub.canonical_title[
                            0:email_alert_gs.MIN_TRUNCATED_TITLE_LEN])):
                    # we have a match, even though we could be wrong.
                    pub_match = self._by_canonical_title[
                        self.canonical_titles_sorted[possible_match_i]]
                    # update everything to use the long, full title.
                    del self._by_canonical_title[
                        self.canonical_titles_sorted[possible_match_i]]
                    del self.canonical_titles_sorted[possible_match_i]
                    self._by_canonical_title[pa.pub.canonical_title] = (
                        pub_match)
                    bisect.insort(
                        self.canonical_titles_sorted, pa.pub.canonical_title)
                    pub_match.canonical_title = pa.pub.canonical_title
            if pub_match:
                pub_match.add_pub_alert(pa)
            else:
                self.add_pub_match(PubMatch(pub_alerts=[pa]))

        return None

    def add_known_pub_info(self, known_pubs_db):
        """Add known pub DB info to exising PubMatches. If no pubmatch exists
        for a known pub then ignore it.

        if known pub is in the library, set its state to INLIB.
        """
        for known_pub in known_pubs_db.get_all_known_pubs():
            pub_match = None
            doi = known_pub.get_doi()
            canonical_title = known_pub.get_canonical_title()
            if doi:
                pub_match = self._by_canonical_doi.get(doi)
            if not pub_match and canonical_title:
                pub_match = self._by_canonical_title.get(canonical_title)
            if pub_match:
                pub_match.set_known_pub(known_pub)
                if pub_match.is_lib_pub():
                    known_pub.set_state(known_pub_db.STATE_INLIB)

        return None

    def get_matchups_with_alerts_sorted_by_title(self):
        """Return list of all PubMatches that have alerts.
        The list is in canonical title alphabetical order.
        """
        matches_w_alerts = []

        for pm in self._by_canonical_title.values():
            if pm._pub_alerts:
                matches_w_alerts.append(pm)

        # sort them by canonical title.
        return sorted(
            matches_w_alerts,
            key=lambda pub_match: pub_match.canonical_title)

    def matchups_with_pub_alerts_to_html(
            self, exclude_db, additional_info_callback):
        """Generate HTML listing all the matchups that have PubAlerts.
        list them in canonical title order.

        Flag alerts that are excluded in a special color.

        additional_info_callback is a function that expects a PubMatch as an
        argument and is called from this method to generate additional
        information in the generated HTML.
        """
        output = []
        known_count = 0
        new_count = 0
        for pm in self.get_matchups_with_alerts_sorted_by_title():
            if pm.is_known():
                state_text = "Known"
                div_style = "background-color: #dddddd; "
                if pm._known_pub:
                    state = pm._known_pub.get_state()
                    annotation = pm._known_pub.get_annotation()
                    qualifier = pm._known_pub.get_qualifier()
                    state_text += (" ({0}: {1} | {2})".format(
                        state, annotation, qualifier))
                    if state in [
                            known_pub_db.STATE_EXCLUDE,
                            known_pub_db.STATE_INLIB,
                            known_pub_db.STATE_IGNORE]:
                        div_style = (  # deemphasize it
                            "background-color: #cccccc; color: #999999; ")
                if pm._lib_pub:
                    state_text += " (" + ", ".join(pm._lib_pub.tags) + ")"
                known_count += 1
                counter = known_count
            else:                 # It's a previously unknown pub.
                state_text = "New"
                div_style = "background-color: #eeeeff; "
                new_count += 1
                counter = new_count
            output.append(
                '<div style="' + div_style
                + 'border: 1px solid #bbbbbb; '
                + 'margin: 1em 0.5em; '
                + 'padding-left: 1em; padding-right: 1em;">')
            output.append(
                '<p style="font-size: 160%;">{0}. {1}</p>'.format(
                    counter, state_text))
            output.append(pm.to_html(exclude_db))

            # Matchup described; now add additional information
            output += additional_info_callback(pm)

        return '\n'.join(output)

    def get_matchups_without_known_pub(self):
        """Return list of all PubMatches that don't have a known pub.

        That is, return the list of pubs that are new.
        """
        matches_without_known = []

        for pm in self._by_canonical_title.values():
            if not pm._known_pub:
                matches_without_known.append(pm)

        return matches_without_known

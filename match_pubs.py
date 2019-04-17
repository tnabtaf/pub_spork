#!/usr/local/bin/python3
"""Match pubs in a set of alerts with pubs in a library and generate a
processed list of pubs from the alerts.

The processed list is then used to help add pubs to the target library.
"""

import argparse
import urllib.parse

import alert_sources
import email_alert
import lib_types
import known_pub_db
import html_report
import pub_match
import publication

DOT_PROXY_OPTION = "dot"
DASH_PROXY_OPTION = "dash"

PROXY_SEPARATOR_OPTIONS = {
    DOT_PROXY_OPTION: ".",
    DASH_PROXY_OPTION: "-",
    }


# Globals
args = None
lib_module = None
input_lib = None


def get_args():
    """Parse and return the command line arguments."""

    arg_parser = argparse.ArgumentParser(
        description=(
            "Match newly reported pubs with pubs in a library, and/or "
            + "pubs from earlier runs, and generate an actionable report "
            + "that can be used to add the new pubs to a library."))
    arg_parser.add_argument(
        "--libtype", required=True,
        help=(
            "What type of library are we reading in, and will the "
            + "actionable report be used to update. Options are "
            + lib_types.get_lib_types_as_text_list() + "."))
    arg_parser.add_argument(
        "--inputlibpath", required=True,
        help="path to the library")
    arg_parser.add_argument(
        "--onlineliburl", required=True,
        help=(
            "Base URL of the online version of the library. Used to "
            + "generate links."))
    arg_parser.add_argument(
        "--email", required=False,
        help="Email account to pull notifications from")
    arg_parser.add_argument(
        "--mailbox", required=False,
        help=(
            "Optional mailbox within email account to limit notifications "
            + "from."))
    arg_parser.add_argument(
        "--imaphost", required=False,
        help=(
            "Address of --email's IMAP server. For GMail this is "
            + "imap.gmail.com"))
    arg_parser.add_argument(
        "--since", required=True,
        help=("Only look at alerts from after this date."
              + " Format: DD-Mon-YYYY.  Example: 01-Dec-2014."))
    arg_parser.add_argument(
        "--before", required=False,
        help=("Optional. Only look at alerts before this date."
              + " Format: DD-Mon-YYYY.  Example: 01-Jan-2015."))
    arg_parser.add_argument(
        # This is mapped to a list before returning to caller.
        "--sources", required=True,
        help="Which alert sources to process. Is either 'all' or a "
        + "comma-separated list (no spaces) from these sources: "
        + alert_sources.get_alert_sources_as_text_list())
    arg_parser.add_argument(
        "--proxy", required=False,
        help=(
            "string to insert in URLs to access pubs through your paywall. "
            + "For Johns Hopkins, for example, this is: "
            + "'.proxy1.library.jhu.edu'"))
    arg_parser.add_argument(
        "--proxyseparator", required=False,
        help=(
            "Some proxies replace dots in the original pub URL with dashes. "
            + "Default is dot."),
        choices=PROXY_SEPARATOR_OPTIONS.keys(), default=DOT_PROXY_OPTION)
    arg_parser.add_argument(
        "--customsearchurl", required=False,
        help=(
            "URL to use for custom searches.  The title of the publication "
            + "will be added to the end of this URL. "
            + "For Johns Hopkins, for example, this is: "
            + "'https://catalyst.library.jhu.edu/"
            + "?utf8=%E2%9C%93&search_field=title&'"))
    # TODO: This should accept multiple custom search URLs in a
    # comma separated list.
    # TODO: should also accept search URL strings where title can be
    # embedded in the string.

    arg_parser.add_argument(
        "--knownpubsin", required=False,
        help=(
            "Read in curation history (likely) from previous run. Tells you "
            + "what you've seen before."))
    arg_parser.add_argument(
        "--knownpubsout", required=False,
        help="Create a history of this run in TSV format as well.")

    arg_parser.add_argument(
        "--okduplicatetitles", required=False,
        help=(
            "Text file containing duplicate titles that have been reviewed "
            + "and are in fact not duplicate titles.  These will not get "
            + "reported as duplicates."))
    arg_parser.add_argument(
        "--curationpage", required=True,
        help="Where to put the HTML page listing all the pubs.")

    """
    arg_parser.add_argument(
        "--verify1stauthors", required=False,
        action="store_true",
        help="When we have a paper from more than one source, check that" +
             " the two sources have the same first author.  This is noisy.")
    """

    args = arg_parser.parse_args()

    # split comma separated list of sources
    args.sources = args.sources.split(",")

    return args


def get_pub_proxy_url(pub_url, proxy, proxy_separator):
    """Given the URL to a pub in it's native habitat, return a URL that links
    to the pub through the given proxy.

    If the pub's URL is say:
      "https://thisandthat.org/paper/etc"
    This this function will return
      "https://thisandthat.org." + proxy + "/paper/etc"
      or
      "https://thisandthat-org." + proxy + "/paper/etc"

    if the pub does not have a URL, then None is returned.
    """
    if pub_url:
        url_parts = pub_url.split("/")
        url_parts[2] = url_parts[2].replace(".", proxy_separator)
        proxy_url = (
            "/".join(url_parts[0:3]) + proxy + "/" + "/".join(url_parts[3:]))
    else:
        proxy_url = None

    return proxy_url


def pub_match_link_list_html(pub_match):
    """Generate a list of links in HTML format for a PubMatch that can be
    used to help curate it.

    This is used as a callback from routines that print information about
    a pub_match.  It's here because this module has most of the knowledge
    about what goes in those links.
    """
    global lib_module, args, input_lib

    output = []
    output.append('<p>Links</p>')
    output.append('<ul>')

    pub_url = publication.get_potentially_redirected_url(
        pub_match.get_pub_url())
    if pub_match.is_new():
        if pub_url:
            # generate link to add pub to library
            add_link = lib_module.gen_add_pub_html_link(pub_url)
            if add_link:  # not all libraries support URLs to add a pub.
                output.append('<li> {0} </li>'.format(add_link))
    elif pub_match.is_lib_pub():
        # Pub is already in library.  Link to that entry.
        output.append(
            '<li> <a href="{0}" target="zot"> See pub at {1}</a></li>'.format(
                input_lib.gen_pub_url_in_lib(
                    pub_match.get_lib_pub()), lib_module.SERVICE_NAME))
    if pub_url:
        # link to pub in its native habitat.
        output.append(
            '<li> <a href="{0}" target="nativepub">See pub</a></li>'.format(
                pub_url))

    if args.proxy and pub_url:
        # link to pub behind proxy.
        output.append(
            ('<li> <a href="{0}" target="proxypub">'
             + 'See pub via proxy</a></li>').format(
                 get_pub_proxy_url(
                     pub_url, args.proxy,
                     PROXY_SEPARATOR_OPTIONS[args.proxyseparator])))

    # Search for pub in several places
    pub_title = pub_match.get_pub_title()
    pub_title_urlencoded = urllib.parse.urlencode({"q": pub_title})

    if args.customsearchurl:
        # search for title at custom search site
        custom_search_site = "/".join(args.customsearchurl.split("/")[0:3])
        output.append(
            ('<li> <a href="{0}" target="custom-search">'
             + 'Search for pub at {1} </a></li>').format(
                 args.customsearchurl + pub_title_urlencoded,
                 custom_search_site))

    # search for title at Google
    output.append(
        ('<li> <a href="https://www.google.com/search?q={0}" '
         + 'target="googletitlesearch" />Search Google</a></li>').format(
             pub_title))

    # search for title at Google Scholar
    output.append(
        ('<li> <a href="https://scholar.google.com/scholar?q={0}" '
         + ' target="googlescholarsearch" />'
         + 'Search Google Scholar</a></li>').format(pub_title))

    # search PubMed
    output.append(
        ('<li> <a href="https://www.ncbi.nlm.nih.gov/pubmed/?term={0}" '
         + 'target="pubmedtitlesearch" /a>Search Pubmed</a></li>').format(
             pub_title))

    output.append('</ul>')
    output.append('</div>')

    return output


def match_pubs(command_line_args):
    """Match up pubs across all provided sources."""
    global lib_module, input_lib, args
    args = command_line_args
    lib_module = lib_types.get_lib_module(args.libtype)
    input_lib = lib_module.PubLibrary(args.inputlibpath, args.onlineliburl)

    # Get the annotation history database.  This includes pubs we added to the
    # library, pubs we decided to ignore, and pubs, we are still deciding on.
    known_pubs_db = None
    if args.knownpubsin:
        known_pubs_db = known_pub_db.KnownPubDB(args.knownpubsin)

    # Get all alerts
    pub_alerts = []

    # Open connection to alert source.
    email_connection = None
    if args.email:
        email_connection = email_alert.AlertSource(
            account=args.email, imaphost=args.imaphost)

    # go through each source and pull in all alerts.
    sources = args.sources
    if sources[0] == 'all':
        sources = alert_sources.ALERT_SOURCES

    for source in sources:
        source_module = alert_sources.get_alert_source_module(source)
        if source_module.IS_EMAIL_SOURCE:
            connection = email_connection
        else:
            connection = None
        connection.module = source_module

        # get every pub_alert from that source
        pub_alerts += (
            connection.get_pub_alerts(
                connection.module.SENDERS, mailbox=args.mailbox,
                since=args.since, before=args.before))

    ok_dup_titles = []    # List of titles that it's ok to have duplicates of.
    if command_line_args.okduplicatetitles:
        dup_titles_file = open(command_line_args.okduplicatetitles, 'r')
        for title in dup_titles_file:
            ok_dup_titles.append(title)
        dup_titles_file.close()

    # now have library, a list of pubs we have seen before, and new pub alerts
    # to match against each other.  Create a matchup DB.
    pub_matchups = pub_match.PubMatchDB(
        pub_library=input_lib, pub_alerts=pub_alerts,
        known_pubs_db=known_pubs_db, ok_dup_titles=ok_dup_titles)

    # Print out any matchups that have new pub_alerts
    curation_page = open(command_line_args.curationpage, 'w')
    curation_page.write(html_report.gen_header())
    curation_page.write(
        pub_matchups.matchups_with_pub_alerts_to_html(
            pub_match_link_list_html))
    curation_page.write(html_report.gen_footer())
    curation_page.close()

    if args.knownpubsout:
        # update known pubs DB to include and pubs we didn't know about before.
        # What didn't we know about before?  Anything without a known pub.

        if not known_pubs_db:
            known_pubs_db = known_pub_db.KnownPubDB()
        new_pubs = pub_matchups.get_matchups_without_known_pub()
        known_pubs_db.add_pubs_from_matchups(new_pubs)
        known_pubs_db.write_db_to_file(args.knownpubsout)

    return None


# MAIN
if __name__ == '__main__':
    command_line_args = get_args()
    match_pubs(command_line_args)

# And we be done.

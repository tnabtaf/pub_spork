#!/usr/local/bin/python3
"""PubSpork is a utility that helps you manage and track publications.  

It was created by @tnabtaf to help track papers that reference 
@galaxyproject.  However, it should be useful to manage any pubs that
reference anything.

See README.md for more.
"""

import argparse

import alert_sources
import lib_types
import report_formats

import generate_lib_report
import match_pubs

def get_args():
    """Parse and return the command line arguments."""

    arg_parser = argparse.ArgumentParser(
        description=(
            "PubSpork helps manage and track publications. "
            + "It contains two main functions: "
            + "1) Supporting curation of newly reported publications. "
            + "2) Library reporting. "
            + "**Supporting Curation**: "
            + "The --match function is used to combine: " 
            + "  a) a DB of publications we have already looked at. "
            + "  b) a library (currently in Zotero or CiteULike) of pubs "
            + "     that have already been identified as relevant. "
            + "  c) A set of publication alerts. "
            + "into an HTML page containing all newly report publications "
            + "and links to those publications to help curate them. "
            + "**Library Reporting**: "
            + "The --report function generated the selected library report."))

    arg_parser.add_argument(
        "--match", required=False, action="store_true",
        help=(
            "Match newly reported pubs with each other and with optional "
            + "libraries of already curated pubs. Generates an HTML page "
            + "that to use to curate the new pubs.")) 
    arg_parser.add_argument(
        "--report", required=False, action="store_true",
        help=(
            "Generate a library report."))

    common_args = arg_parser.add_argument_group(
        title="Common arguments", description=None)
    common_args.add_argument(
        "--libtype", required=True,
        help=(
            "What type of of 'already accepted pubs' library are we reading "
            + "in and updating? Options are "
            + lib_types.get_lib_types_as_text_list() + "."))
    common_args.add_argument(
        "--inputlibpath", required=True,
        help=(
            "Path to the library of already accepted pubs. This is typically "
            + "exported from the library service."))
    common_args.add_argument(
        "--onlineliburl", required=True,
        help=(
            "Base URL of the online version of the library of already "
            + "accepted pubs. Used to generate links."))

    match_args = arg_parser.add_argument_group(
        title="Match arguments", description=None)
    match_args.add_argument(
        "--email", required=False,
        help=(
            "Email account to pull new pub alerts from."))
    match_args.add_argument(
        "--mailbox", required=False,
        help=(
            "Optional mailbox within email account to limit notifications "
            + "from."))
    match_args.add_argument(
        "--imaphost", required=False,
        help=(
            "Address of --email's IMAP server. For GMail this is "
            + "imap.gmail.com."))
    match_args.add_argument(
        "--since", required=False,
        help=(
            "Only look at alerts from after this date. "
            + "Format: DD-Mmm-YYYY. Example: 01-Dec-2014."))
    match_args.add_argument(
        "--before", required=False,
        help=(
            "Optional. Only look at alerts before this date. "
            + "Format: DD-Mmm-YYYY.  Example: 01-Jan-2015."))
    match_args.add_argument(
        "--sources", required=False,
        help=(
            "Which alert sources to process. Is either 'all' or a "
            + "comma-separated list (no spaces) from these sources: "
            + alert_sources.get_alert_sources_as_text_list()))
    match_args.add_argument(
        "--proxy", required=False,
        help=(
            "String to insert in URLs to access pubs through your paywall. "
            + "For Johns Hopkins, for example, this is: "
            + "'.proxy1.library.jhu.edu'"))
    match_args.add_argument(
        "--customsearchurl", required=False,
        help=(
            "URL to use for custom searches at your institution.  The title "
            + "of the publication will be added to the end of this URL."))
    match_args.add_argument(
        "--knownpubsin", required=False,
        help=(
            "Path to existing known pubs DB. This is the list of publications "
            + "you have already looked at. Typically generated from the "
            + "previous PubSpork run. In TSV format."))
    match_args.add_argument(
        "--knownpubsout", required=False,
        help="Where to put the new known pubs DB (in TSV format).")
    match_args.add_argument(
        "--okduplicatetitles", required=False,
        help=(
            "Text file containing duplicate titles that have been reviewed "
            + "and are in fact not duplicate titles.  These will not get "
            + "reported as duplicates."))

    report_args = arg_parser.add_argument_group(
        title="Report arguments", description=None)
    report_args.add_argument(
        "--reportformat", required=False,
        help=(
            "What format to generate the report in. Options are "
            + report_formats.get_formats_as_text_list()
            + "."))
    arg_parser.add_argument(
        "--year", required=False, action="store_true",
        help="Produce table showing number of papers published each year.")
    report_args.add_argument(
        "--tagyear", required=False, action="store_true",
        help=(
            "Produce table showing number of papers with each tag, "
            + "each year."))
    report_args.add_argument(
        "--yeartag", required=False, action="store_true",
        help=(
            "Produce table showing number of papers with each year, "
            + "each tag."))
    report_args.add_argument(
        "--journalyear", required=False, action="store_true",
        help=(
            "Produce table showing number of papers in different journals, "
            + "each year."))
    report_args.add_argument(
        "--tagcountdaterange", required=False, action="store_true",
        help=(
            "Produce table showing number of papers that were tagged with "
            + "each tag during a given time period. --entrystartdate and "
            + "--entryenddate parameters are required if --tagcountdaterange "
            + "is specified."))
    report_args.add_argument(
        "--entrystartdate", required=False,
        help=(
            "--tagcountdaterange will report on papers with entry dates "
            + "greater than or equal to this date. Example: 2016-12-29. "))
    report_args.add_argument(
        "--entryenddate", required=False,
        help=(
            "--tagcountdaterange will report on papers with entry dates "
            + "less than or equal to this date. Example: 2017-01-29. "))
    report_args.add_argument(
        "--onlythesetags", required=False,
        help=(
            "Can either generate a report about all tags in the library, "
            + "or, only about a subset of tags. If this parameter is given "
            + "then only the tags listed in this file will be reported on. "
            + "List one tag per line."))

    
    args = arg_parser.parse_args()

    if args.match:
        # split comma separated list of sources
        args.sources = args.sources.split(",")

    return args

args = get_args()

if args.match:
     match_pubs.match_pubs(args)
elif args.report:
    generate_lib_report.generate_lib_report(args)

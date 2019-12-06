#!/usr/local/bin/python3
"""Generate reports about a given library."""

import argparse
import collections

import lib_types
import report_formats


def gen_year_report(lib, format_module):
    """Generate table with one row per year, and another column showing the
    number of papers published that year.

    return report as a text string.
    """
    report = format_module.gen_year_report(lib, lib.get_years())

    return(u"".join(report))


def gen_journal_report(lib, format_module):
    """Generate table with one row per journal and a column showing the
    number of pubs printed in that journal.

    return report as a text string.
    """
    report = format_module.gen_journal_report(lib)

    return(u"".join(report))


def gen_tag_year_report(lib, format_module):
    """Generate table with one row per year, and one column per tag.
    Each cell shows the number of papers a tag was attached to that year.

    return report as a text string.
    """
    # Preprocess. Need to know order of tags and years.
    # Count number of papers with each tag
    n_papers_w_tag = {}
    for tag in lib.get_tags():
        n_papers_w_tag[tag] = len(lib.get_pubs(tag=tag))

    # sort tags by paper count, max first
    tags_in_count_order = [
        tag for tag in sorted(
            n_papers_w_tag.keys(),
            key=lambda key_value: - n_papers_w_tag[key_value])]

    report = format_module.gen_tag_year_report(
        lib, tags_in_count_order, n_papers_w_tag, lib.get_years())

    return(u"".join(report))


def gen_tag_count_date_range_report(
        lib, format_module,
        num_tag_column_groups,
        entry_start_date, entry_end_date):

    """Generate a table with with each entry showing the tag name,
    and the number of papers tagged with that tag during the given date range.
    Each cell shows the number of papers a tag was attached to that year.

    Return report as a text string.
    """

    # Preprocess. Need to know order of tags
    tags = lib.get_tags()
    # Count number of papers with each tag
    n_papers_w_tag = {}
    for tag in tags:
        n_papers_w_tag[tag] = len(
            lib.get_pubs(
                tag=tag,
                start_entry_date=entry_start_date,
                end_entry_date=entry_end_date))

    # sort tags by paper count, max first, then alphabetical
    tags_in_count_order = [
        tag for tag in
        sorted(
            n_papers_w_tag.keys(),
            key=lambda key_value: (
                "{0} {1}".format(
                    str(1000000 - n_papers_w_tag[key_value]).zfill(7),
                    key_value.lower())))]

    # time for an ordered dict?  With tags in count order?  I think so.
    tags_ord_dict = collections.OrderedDict()
    for tag in tags_in_count_order:
        tags_ord_dict[tag] = n_papers_w_tag[tag]

    # get total # of papers during time range
    n_total_papers = len(lib.get_pubs(
        start_entry_date=entry_start_date, end_entry_date=entry_end_date))
    report = format_module.gen_tag_count_date_range_report(
        tags_ord_dict, n_total_papers, lib,
        num_tag_column_groups,
        entry_start_date, entry_end_date)

    return u"".join(report)


def get_args():
    """
    Parse command line arguments.
    """
    arg_parser = argparse.ArgumentParser(
        description="Generate reports for a publication library.")
    arg_parser.add_argument(
        "--libtype", required=True,
        help=(
            "What type of library are we reading in, and generating "
            + "the report for. Options are "
            + lib_types.get_lib_types_as_text_list()
            + "."))
    arg_parser.add_argument(
        "--inputlibpath", required=True,
        help="path to the library")
    arg_parser.add_argument(
        "--onlineliburl", required=True,
        help=(
            "Base URL of the online version of the library. Used to "
            + "generate links in reports."))
    arg_parser.add_argument(
        "--reportformat", required=True,
        help=(
            "What format generate the report in. Options are "
            + report_formats.get_formats_as_text_list()
            + "."))
    arg_parser.add_argument(
        "--journal", required=False, action="store_true",
        help="Produce table showing number of papers in different journals.")
    arg_parser.add_argument(
        "--year", required=False, action="store_true",
        help="Produce table showing number of papers published each year.")
    arg_parser.add_argument(
        "--tagyear", required=False, action="store_true",
        help=(
            "Produce table showing number of papers with each tag, "
            + "each year."))
    arg_parser.add_argument(
        "--yeartag", required=False, action="store_true",
        help=(
            "Produce table showing number of papers with each year, "
            + "each tag."))
    arg_parser.add_argument(
        "--tagcountdaterange", required=False, action="store_true",
        help=(
            "Produce table showing number of papers that were tagged with "
            + "each tag during a given time perioud. --entrystartdate and "
            + "--entryenddate parameters are required if --tagcountdaterange "
            + "is specified."))
    arg_parser.add_argument(
        "--entrystartdate", required=False,
        help=(
            "--tagcountdaterange will report on papers with entry dates "
            + "greater than or equal to this date. Example: 2016-12-29"))
    arg_parser.add_argument(
        "--entryenddate", required=False,
        help=(
            "--tagcountdaterange will report on papers with entry dates "
            + "less than or equal to this date. Example: 2017-01-29"))
    arg_parser.add_argument(
        "--onlythesetags", required=False,
        help=(
            "Can either generate a report about all tags in the library, "
            + "or, only about a subset of tags. If this parameter is given "
            + "then only the tags listed in this file will be reported on. "
            + "List one tag per line."))
    arg_parser.add_argument(
        "--numtagcolumngroups", required=False, type=int, default=4,
        help=(
            "Specifies how many tags (and their counts) should be listed "
            + "in each row of a tag report. Default is 4."))

    return(arg_parser.parse_args())


def generate_lib_report(args):

    lib_module = lib_types.get_lib_module(args.libtype)
    input_lib = lib_module.PubLibrary(args.inputlibpath, args.onlineliburl)

    # Setup fast access to lib on anything we might report on.
    input_lib.prep_for_reports(args.onlythesetags)

    # What format should the report be in?
    format_module = report_formats.get_format_module(args.reportformat)

    # Generate each report that was requested.
    if args.journal:
        print(gen_journal_report(input_lib, format_module))

    if args.year:
        print(gen_year_report(input_lib, format_module))

    if args.tagyear:
        print(gen_tag_year_report(input_lib, format_module))

    if args.tagcountdaterange:
        print(gen_tag_count_date_range_report(
            input_lib, format_module,
            args.numtagcolumngroups,
            args.entrystartdate, args.entryenddate))

    return None


# MAIN
if __name__ == '__main__':
    command_line_args = get_args()
    generate_lib_report(command_line_args)

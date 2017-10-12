#!/usr/local/bin/python3
"""Support for library reports in Markdown format.

Since there is a lot we can't directly in Markdown format, this module
falls back on the html_report module when necessary.
"""

import math

import html_report

N_TAG_COLUMN_GROUPS = 4   # create report with n tags and n counts across

def gen_header():
    """Generate a header for Markdown.  Markdown does not have a header."""
    return ""


def gen_footer():
    """Generate a footer for Markdown.  Markdown does not have a footer."""
    return ""

def gen_year_report(lib, years_ordered):
    """Generate a year report showing the number of published papers in each
    year passed in.

    If you want a color scale then call the HTML version of this routine.
    """
    report = []
    # Header
    report.append("| Year | # |\n")
    report.append("| ----: | ----: |\n")

    # Years
    n_papers_across_years = 0
    for year in years_ordered:
        n_papers_this_year = len(lib.get_pubs(year=year))
        n_papers_across_years += n_papers_this_year
        report.append('| {0} | {1} |\n'.format(year, n_papers_this_year))

    # Total
    report.append('| Total | {0} |\n'.format(n_papers_across_years))
        
    return report

def gen_tag_year_report(lib, tags_ordered, n_papers_w_tag, years_ordered):
    """Generate a tagyear report in Markdown format.

    HA! This is all HTML.

    TODO: Combine tags_ordered and n_papers_w_tag into an ordered dictionary
    """
    return html_report.gen_tag_year_report(
        lib, tags_ordered, n_papers_w_tag, years_ordered,
        actually_markdown=True)

def gen_tag_count_date_range_report(tags_in_count_order, n_total_papers,
                                    lib, start_date, end_date):
    """Generate a table with with each entry showing the tag name,
    and the number of papers tagged with that tag during the given date range.
    Each cell shows the number of papers a tag was attached to that generate.
    """
    # numbers per tag
    tag_markup = []
    for tag, n_papers in tags_in_count_order.items():
        if n_papers > 0:
            tag_markup.append(
                '| {0} | [{1}]({2}) | '.format(
                    n_papers, tag,
                    lib.gen_tag_url(tag)))

    # Have markup for individual tags; now decide how many go in each column
    n_tags_to_report = len(tag_markup)
    n_tags_per_col = int(math.ceil(n_tags_to_report / N_TAG_COLUMN_GROUPS))

    report = []              # now have everything we need; generate report

    # generate header
    report.append(
        '\n{0}  papers added between {1} and {2}\n\n'.format(
            n_total_papers, start_date, end_date))

    header_line = []
    for col_group in range(N_TAG_COLUMN_GROUPS):
        report.append(
            '| # | Tag | ')
        header_line.append('| ---: | --- |')
        if col_group < N_TAG_COLUMN_GROUPS - 1:
            header_line.append(' --- ')
    report.append("\n")
    report.append("".join(header_line) + "\n")

    # add tags & counts
    for row_idx in range(n_tags_per_col):
        for col_group in range(N_TAG_COLUMN_GROUPS):
            tagIdx = (row_idx * N_TAG_COLUMN_GROUPS) + col_group
            if tagIdx < n_tags_to_report:
                report.append(tag_markup[tagIdx])
            else:
                report.append('| | | ')
        report.append('\n')
 
    return(u"".join(report))

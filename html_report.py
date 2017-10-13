#!/usr/local/bin/python3
"""Support for library reports in HTML format."""

import math

# This specifies a white (low numbers) to greeen (high numbers) spectrum
RED_RANGE = [0x58, 0xff]
GREEN_RANGE = [0xc0, 0xff]
BLUE_RANGE = [0x58, 0xff]

RED_SPREAD = math.fabs(RED_RANGE[1] - RED_RANGE[0])
GREEN_SPREAD = math.fabs(GREEN_RANGE[1] - GREEN_RANGE[0])
BLUE_SPREAD = math.fabs(BLUE_RANGE[1] - BLUE_RANGE[0])

RED_MAX = max(RED_RANGE)
GREEN_MAX = max(GREEN_RANGE)
BLUE_MAX = max(BLUE_RANGE)

N_TAG_COLUMN_GROUPS = 4   # create report with n tags and n counts across


def gen_header():
    """Create an HTML header."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE html '
        + 'PUBLIC "-//W3C//DTD XHTML 1.1//EN" '
        + '"http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">'
        + '<html xmlns="http://www.w3.org/1999/xhtml"> '
        + '<head><meta '
        + 'http-equiv="Content-Type" content="text/html; charset=utf-8"/> '
        + '</head> <body>')


def gen_footer():
    """Create an HTML footr."""
    return '</body></html>'


def gen_count_style(count, max_count):
    """Bigger counts get more color.

    Color scheme is set above to go exponentially from white at low numbers
    to maximum color at high numbers.
    """
    if count == 0:
        percent = 0
    else:
        percent = math.log(count+1, max_count+1)
    red = int(round(RED_MAX - RED_SPREAD*percent))
    green = int(round(GREEN_MAX - GREEN_SPREAD*percent))
    blue = int(round(BLUE_MAX - BLUE_SPREAD*percent))

    color = "{0:2x}{1:2x}{2:2x}".format(red, green, blue)
    style = ' style="text-align: right; background-color: #' + color + ';" '

    return style


def gen_year_report(
        lib, years_ordered, actually_markdown=False):
    """Generate a year report, for the given years, in HTML format.
    """
    report = []
    if not actually_markdown:
        # Generate header.
        report.append(gen_header())
    report.append('<table class="table">\n')
    report.append('  <tr>\n')
    report.append('    <th> Year </th>\n')
    report.append('    <th> # </th>\n')
    report.append('  </tr>\n')

    # Years
    n_papers_across_years = 0
    n_papers_this_year = {}
    for year in years_ordered:
        n_papers_this_year[year] = len(lib.get_pubs(year=year))
        n_papers_across_years += n_papers_this_year[year]

    for year in years_ordered:
        style = gen_count_style(
            n_papers_this_year[year], n_papers_across_years)
        report.append('  <tr>\n')
        report.append('    <td> {0} </td>\n'.format(year))
        report.append('    <td {0}> {1} </td>\n'.format(
                style, n_papers_this_year[year]))
        report.append('  </tr>\n')

    # Total
    style = gen_count_style(n_papers_across_years, n_papers_across_years)
    report.append('  <tr>\n')
    report.append('    <td class="text-right"> Total </td>\n')
    report.append(
        '    <td {0}> {1} </td>\n'.format(
            style, n_papers_across_years))
    report.append('  </tr>\n')

    if not actually_markdown:
        report.append(gen_footer())

    return report

def gen_journal_report(lib, actually_markdown=False):
    """Generate a report listing all journals, ranked by number of pubs,
    in HTML format.
    """
    report = []
    if not actually_markdown:
        # Generate header.
        report.append(gen_header())
    report.append('<table class="table">\n')
    report.append('  <tr>\n')
    report.append('    <th> Rank </th>\n')
    report.append('    <th> Journal </th>\n')
    report.append('    <th> # </th>\n')
    report.append('  </tr>\n')

    rank = 0
    jrnl_idx = 0
    n_prior_pubs = 0
    for jrnl_pubs in lib.journal_pubs_rank:
        jrnl_idx += 1
        n_current_pubs = len(jrnl_pubs)
        if n_prior_pubs != n_current_pubs:
            rank = jrnl_idx
            n_prior_pubs = n_current_pubs
        report.append('  <tr>\n')
        report.append('    <td> {0} </td>\n'.format(rank))
        report.append('    <td> {0} </td>\n'.format(jrnl_pubs[0].journal_name))
        report.append('    <td style="text-align: right;"> {0} </td>\n'.format(
            n_current_pubs))

    return report

def gen_tag_year_report(
        lib, tags_ordered, n_papers_w_tag, years_ordered,
        actually_markdown=False):
    """Generate a tagyear report in HTML format.

    TODO: Combine tags_ordered and n_papers_w_tag into an ordered dictionary
    """
    report = []
    if not actually_markdown:
        # Generate header.
        report.append(gen_header())
    report.append('<table class="table">\n')
    report.append('  <tr>\n')
    report.append('    <th> Year </th>\n')
    for tag in tags_ordered:
        report.append(
            '    <th> <a href="'
            + lib.gen_tag_url(tag)
            + '">' + tag + '</a> </th>\n')
    report.append('    <th> # </th>\n')
    report.append('  </tr>\n')

    # generate numbers of papers with tag per year
    all_papers_count = len(lib)
    for year in years_ordered:
        report.append('  <tr>\n')
        n_papers_this_year = len(lib.get_pubs(year=year))
        report.append('    <th> ' + year + ' </th>\n')
        for tag in tags_ordered:
            papers_for_tag_year = lib.get_pubs(tag=tag, year=year)
            if papers_for_tag_year:
                n_papers_tag_year = len(papers_for_tag_year)
                style = gen_count_style(
                    n_papers_tag_year, all_papers_count)
                tag_year_url = lib.gen_tag_year_url(tag, year)
                if tag_year_url:
                    count_html = (
                        '<a href="{0}"> {1} </a>'.format(
                            tag_year_url, n_papers_tag_year))
                else:
                    count_html = "{0}".format(n_papers_tag_year)
            else:
                style = ""
                count_html = ""
            report.append('    <td ' + style + '> ' + count_html + ' </td>\n')
        year_count_style = gen_count_style(
            n_papers_this_year, all_papers_count)
        year_url = lib.gen_year_url(year)
        if year_url:
            report.append(
                '    <td {0}> <a href="{1}"> {2} </a></td>\n'.format(
                    year_count_style, year_url, n_papers_this_year))
        else:
            report.append(
                '    <td {0}> {1} </td>\n'.format(
                    year_count_style, n_papers_this_year))

        report.append('  </tr>\n')

    # generate total line at bottom
    report.append('  <tr>\n')
    report.append('    <th> Total </th>\n')
    for tag in tags_ordered:
        tag_count_style = gen_count_style(
            n_papers_w_tag[tag], all_papers_count)
        report.append(
            '    <th ' + tag_count_style + '> '
            + '<a href="' + lib.gen_tag_url(tag) + '">'
            + str(n_papers_w_tag[tag]) + '</a> </th>\n')

    all_papers_style = gen_count_style(all_papers_count, all_papers_count)
    report.append('    <th ' + all_papers_style + '> '
                  + str(all_papers_count) + ' </th>\n')
    report.append('  </tr>\n')
    report.append('</table>\n')
    if not actually_markdown:
        report.append(gen_footer())

    return report

def gen_tag_count_date_range_report(tags_in_count_order, n_total_papers,
                                    lib, start_date, end_date):
    """Generate a table with with each entry showing the tag name,
    and the number of papers tagged with that tag during the given date range.
    Each cell shows the number of papers a tag was attached to that generate.

    However, HTML format is not yet supported for this report, so just throw
    an error.
    """
    raise NotImplementedError (
        "gen_tag_count_date_range_report not yet implemented for report "
        + "format HTML")

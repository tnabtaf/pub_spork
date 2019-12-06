#!/usr/local/bin/python3
"""Support for library reports as a list of bootstrap buttons.

Bootstrap is basically HTML + Bootstrap.
"""

import html_report


def gen_header():
    """Generate a header for Bootstrap.  Use HTML header."""
    return html_report.gen_header()


def gen_footer():
    """Generate a footer for Bootstrap.  Use HTML footer."""
    return ""


def gen_year_report(lib, years_ordered):
    """Generate a year report showing the number of published papers in each
    year passed in.

    If you want a color scale then call the HTML version of this routine.
    """
    tag_markup = []
    # Header

    # Years
    n_papers_across_years = 0
    for year in years_ordered:
        n_papers_across_years += len(lib.get_pubs(year=year))

    for year in years_ordered:
        n_papers_this_year = len(lib.get_pubs(year=year))
        tag_markup.append(
            '<div class="btn" '
            + html_report.gen_count_style(
                n_papers_this_year, n_papers_across_years)
            + '> {0} : <strong>{1}</strong></div>\n'.format(
                n_papers_this_year, year))

    # Total
    tag_markup.append(
        '<div class="btn" '
        + html_report.gen_count_style(
            n_papers_across_years, n_papers_across_years)
        + '> {0} : <strong>Total</strong></div>'.format(n_papers_across_years))

    tag_markup.append('\n')

    return " ".join(tag_markup)


def gen_journal_report(lib):
    """Generate a report showing the number of published papers in each journal
    """
    report = []

    total_pubs_in_journals = 0
    for jrnl_pubs in lib.journal_pubs_rank:
        total_pubs_in_journals += len(jrnl_pubs)

    jrnl_idx = 0
    n_prior_pubs = 0
    for jrnl_pubs in lib.journal_pubs_rank:
        jrnl_idx += 1
        n_current_pubs = len(jrnl_pubs)
        if n_prior_pubs != n_current_pubs:
            n_prior_pubs = n_current_pubs
        report.append(
            '<div class="btn" '
            + html_report.gen_count_style(
                n_current_pubs, total_pubs_in_journals)
            + '> {0} : <strong>{1}</strong></div>\n'.format(
                n_current_pubs, jrnl_pubs[0].journal_name))
    report.append('\n')
    return " ".join(report)


def gen_tag_year_report(lib, tags_ordered, n_papers_w_tag, years_ordered):
    """
    Generate a tagyear report in Markdown format.

    Can't do this with buttons. Nope. This report is a table. Full stop.
    """
    return "Can't generate a gen_tag_year_report in bootstrap-buttons format."


def gen_tag_count_date_range_report(tags_in_count_order, n_total_papers,
                                    lib, num_tag_column_groups,
                                    start_date, end_date):
    """
    Generate a list of Bootstrap buttons with with each entry showing the
    tag name preceded by the number of papers tagged with that tag during
    the given date range.

    num_tag_column_groups is ignored.
    """

    # numbers per tag
    tag_markup = []
    for tag, n_papers in tags_in_count_order.items():
        if n_papers > 0:
            tag_markup.append(
                '<a class="btn" '
                + html_report.gen_count_style(n_papers, n_total_papers)
                + 'href="{0}"> {1} : <strong>{2}</strong></a>\n'.format(
                    lib.gen_tag_url(tag, True), n_papers, tag))
    tag_markup.append('\n')

    return(" ".join(tag_markup))

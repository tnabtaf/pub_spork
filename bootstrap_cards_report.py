#!/usr/local/bin/python3
"""Support for library reports as a list of bootstrap cards.

Bootstrap is basically HTML + Bootstrap.
"""

import html_report


def gen_header():
    """
    Generate a header for Bootstrap Cards. Use HTML header,
    followed by a Bootstrap Card-deck 
    """
    header = []
    header.append(html_report.gen_header())
    header.append('\n<div class="card-deck">\n')

    return("".join(header))


def gen_footer():
    """Generate a footer for Bootstrap.  Use HTML footer."""
    footer = []
    footer.append("</div>\n")
    footer.append(html_report.gen_footer())

    return("".join(footer))


def gen_year_report(lib, years_ordered):
    """Generate a year report showing the number of published papers in each
    year passed in.

    If you want a color scale then call the HTML version of this routine.
    """
    return "Can't generate a gen_year_report in bootstrap-cards format."


def gen_journal_report(lib):
    """Generate a report showing the number of published papers in each journal
    """
    return "Can't generate a gen_journal_report in bootstrap-cards format."


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
    return(
        "Can't generate a gen_tag_count_date_report in bootstrap-cards format.")


def gen_pubs_date_range_report(lib, entry_start_date, entry_end_date):
    """
    Generate a Bootstrap card deck listing pubs in the library.
    """
    tags = lib.get_tags()
    pubs = set()
    for tag in tags:
        pubs = pubs.union(
            set(
                lib.get_pubs(
                    tag=tag,
                    start_entry_date=entry_start_date,
                    end_entry_date=entry_end_date)))

    pubs_report = []
    pubs_report.append(gen_header())
    for pub in pubs:
        # create a card header
        pubs_report.append(
            '<div class="card border-info" '
            + 'style="min-width: 16rem; max-width: 24rem">\n')
        pubs_report.append('<div class="card-header">')
        pubs_report.append('[' + pub.title + '](' + pub.url + ')')
        pubs_report.append('</div>\n\n')
        pubs_report.append(pub.authors)

        if pub.journal_name:
            pubs_report.append(', *' + pub.journal_name + '*')
        if pub.ref:
            pubs_report.append(', ' + pub.ref)

        if pub.canonical_doi:
            pubs_report.append(
                '. doi: [' + pub.canonical_doi + '](https://doi.org/'
                + pub.canonical_doi + ')')
        
        pubs_report.append('\n</div>\n\n')

    pubs_report.append(gen_footer())

    return(u"".join(pubs_report))



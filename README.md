# PubSpork:

## A utensil for tracking (and avoiding retracking) publications and publication alerts

**PubSpork** helps manage and track publications and publication alerts. It has two main functions:

1. Supporting curation of newly reported publications.
1. Library reporting.

**[Table of Contents](http://tableofcontent.eu)**

<!-- Table of contents generated generated by http://tableofcontent.eu -->

- [Terminology](#terminology)
  - [Pub Alert](#pub-alert)
  - [Data Stores](#data-stores)
    - [Relevant Pubs Library](#relevant-pubs-library)
    - [Known Pubs Database](#known-pubs-database)
- [Arguments](#arguments)
- [Supporting Curation (`--match`)](#supporting-curation-match)
  - [Example: Match, with all inputs and outputs](#example-match-with-all-inputs-and-outputs)
    - [Inputs](#inputs)
  - [Outputs](#outputs)
  - [How is my relevant pubs lib updated?](#how-is-my-relevant-pubs-lib-updated)
    - [CiteULike](#citeulike)
      - [What if CiteULike utterly fails to preload any metadata?](#what-if-citeulike-utterly-fails-to-preload-any-metadata)
      - [What if the pub's website does not support RIS or BibTeX export?](#what-if-the-pubs-website-does-not-support-ris-or-bibtex-export)
    - [Zotero](#zotero)
      - [Setting up Zotero](#setting-up-zotero)
        - [Get a Zotero account](#get-a-zotero-account)
        - [Install the Zotero client on your computer](#install-the-zotero-client-on-your-computer)
        - [Connect your Zotero desktop client to your Zotero account.](#connect-your-zotero-desktop-client-to-your-zotero-account)
        - [Install the Zotero Connector in your web browser](#install-the-zotero-connector-in-your-web-browser)
      - [Adding publications to Zotero](#adding-publications-to-zotero)
  - [How is my *known pubs DB* updated?](#how-is-my-known-pubs-db-updated)
    - [Manually updating the *known pubs DB*](#manually-updating-the-known-pubs-db)
- [Reporting](#reporting)

# Terminology

## Pub Alert

A pub alert is an email from a service or web site that reports publications that match some search criteria you have set up with that service / website.

Alerts could also be RSS feeds, etc, but PubSpork does not yet support any of those.

## Data Stores

There are two distinct data stores for PubSpork.  Keeping track of which is which is key to understanding the PubSpork big picture.

### Relevant Pubs Library

This is a collection of publications that we have already looked at and determined to be relevant to our our interests.  The *relevant pubs lib* is stored online, in a reference manager such as CiteULike or Zotero.

The end goal of PubSpork is to help you create your *relevant pubs lib*.

### Known Pubs Database

PubSpork keeps track of *every pub that has ever been reported in a pub alert* in a *Known Pubs DB*.

Not all pubs that are reported to us in alerts are relevant to our interests.  The *known pubs DB* helps us avoid looking at irrelevant (and relevant, but already added) pubs over and over, every time we run PubSpork.


# Arguments

```
pub_spork.py --help

optional arguments:
  -h, --help            show this help message and exit
  --match               Match newly reported pubs with each other and with
                        optional libraries of already curated pubs. Generates
                        an HTML page that to use to curate the new pubs.
  --report              Generate a library report.

Common arguments:
  --libtype LIBTYPE     What type of of 'already accepted pubs' library are we
                        reading in and updating? Options are citeulike-json,
                        and zotero-csv.
  --inputlibpath INPUTLIBPATH
                        Path to the library of already accepted pubs. This is
                        typically exported from the library service.
  --onlineliburl ONLINELIBURL
                        Base URL of the online version of the library of
                        already accepted pubs. Used to generate links.

Match arguments:
  --email EMAIL         Email account to pull new pub alerts from.
  --mailbox MAILBOX     Optional mailbox within email account to limit
                        notifications from.
  --imaphost IMAPHOST   Address of --email's IMAP server. For GMail this is
                        imap.gmail.com.
  --since SINCE         Only look at alerts from after this date. Format: DD-
                        Mmm-YYYY. Example: 01-Dec-2014.
  --before BEFORE       Optional. Only look at alerts before this date.
                        Format: DD-Mmm-YYYY. Example: 01-Jan-2015.
  --sources SOURCES     Which alert sources to process. Is either 'all' or a
                        comma-separated list (no spaces) from these sources:
                        webofscience-email, sciencedirect-email, myncbi-email,
                        wiley-email, and googlescholar-email
  --proxy PROXY         String to insert in URLs to access pubs through your
                        paywall. For Johns Hopkins, for example, this is:
                        '.proxy1.library.jhu.edu'
  --customsearchurl CUSTOMSEARCHURL
                        URL to use for custom searches at your institution.
                        The title of the publication will be added to the end
                        of this URL.
  --knownpubsin KNOWNPUBSIN
                        Path to existing known pubs DB. This is the list of
                        publications you have already looked at. Typically
                        generated from the previous PubSpork run. In TSV
                        format.
  --knownpubsout KNOWNPUBSOUT
                        Where to put the new known pubs DB (in TSV format).

Report arguments:
  --reportformat REPORTFORMAT
                        What format to generate the report in. Options are
                        markdown, and html.
  --tagyear             Produce table showing number of papers with each tag,
                        each year.
  --yeartag             Produce table showing number of papers with each year,
                        each tag.
  --journalyear         Produce table showing number of papers in different
                        journals, each year.
  --tagcountdaterange   Produce table showing number of papers that were
                        tagged with each tag during a given time period.
                        --entrystartdate and --entryenddate parameters are
                        required if --tagcountdaterange is specified.
  --entrystartdate ENTRYSTARTDATE
                        --tagcountdaterange will report on papers with entry
                        dates greater than or equal to this date. Example:
                        2016-12-29.
  --entryenddate ENTRYENDDATE
                        --tagcountdaterange will report on papers with entry
                        dates less than or equal to this date. Example:
                        2017-01-29.
```

# Supporting Curation (`--match`)

The `--match` function is used to combine:

- a *known pubs DB* (ones we have already looked at), stored in a TSV file (and created by PubSpork)
- a library (currently in Zotero or CiteULike) of pubs that have already been identified as relevant.
- A set of publication alerts of newly reported publications

into

1. an HTML page containing all newly report publications
and links to those publications to help curate them
1. An updated *known pubs DB*.

The goals are two-fold

- Keep track of relevant pubs in a selected online citation manager service (e.g., CiteULike, Zotero)
- Avoid looking at any publication (to see if it is relevant) more than once.
   - This requires also keeping track of *irrelevant* publications.


## Example: Match, with all inputs and outputs

```
/usr/local/bin/python3 pub_spork/pub_spork.py \
    --match \
    --libtype zotero-csv \
    --inputlibpath Zotero_libs/Zotero_lib_20170917.csv \
    --onlineliburl https://www.zotero.org/groups/1724202/testing_groups/items \
    --email youraccount@gmail.com \
    --mailbox Papers \
    --imaphost imap.gmail.com \
    --since 23-Aug-2017 \
    --before 19-Sep-2017 \
    --sources all \
    --customsearchurl 'https://catalyst.library.jhu.edu/?utf8=%E2%9C%93&search_field=title&' \
    --proxy .proxy1.library.jhu.edu \
    --knownpubsin KnownPubDBs/known_pubs_db_20170830.tsv \
    --knownpubsout KnownPubDBs/known_pubs_db_20170918.z.tsv
```

### Inputs

This example takes as input:

- New publication email alerts:
  - sent the GMail account youraccount@gmail.com (`--email`, `--imaphost`)
  - between August 24 and September 18, 2017 (`--since`, `--before`)
  - from only the mailbox "Papers" (`--mailbox`)
  - from all supported email alert sources (`--sources`)
    - (Currently) Web of Science, ScienceDirect, MyNCBI, Wiley Online Library, and Google Scholar.
- A library of publications we have already identified as being of interest:
- Library is from Zotero in CSV format, and is available locally (`--libtype`, `--inputlibpath`)
- A *known pubs DB* with pubs we have already looked at (`--knownpubdbin`)
  - This is in TSV format and was likely produced by the previous run of `pub_spork.py`

## Outputs

- An HTML page listing all newly reported publications
  - This is sent to `stdout`
  - It will contain links to
    - Pubs that have already been added to your library (`--onlineliburl`)
    - Pub searches at a custom URL, typically in your institution's library (`--customsearchurl`)
    - The paper itself, Google Scholar, Google, etc.
  - This report can be used to help update both
    - Your *relevant pubs lib* (in this case, your library in Zotero)
    - Your TSV *known pubs DB*.
- An updated TSV *known pubs DB*.
  - This lists all the publications we have ever looked at, including ones that turned out to be irrelevant. 
  - This is a combination of
    - The previous version of the *known pubs DB*
    - The publications in your *relevant pubs lib* (in this case from Zotero)
    - Newly reported publications.


## How is my relevant pubs lib updated?

Your *relevant pubs lib* is kept in a reference manager like CiteULike or Zotero.  One of the key goals of PubSpork is to help you create this library.

How publications are added depends on the reference manager:

### CiteULike

First, you'll need to have a CiteULike account.  Set that up, and then make sure you are logged in before you start to walk through the generated HTML page.

For CiteULike libraries, the generated HTML page will include an "Submit to CiteULike" link for any publication that PubSpork does not think is already in your CiteULike library.  Clicking on this link submits the publication's URL to CiteULike and CiteULike does its best to prepopulate a new publication form with as much metadata as it can.

It's now your job to assign any tags and a priority to new paper.

#### What if CiteULike utterly fails to preload any metadata?

This happens more than you would like it to.  What are your options?

In preferred order:

**1. Submit a different URL**

PubSpork submits papers to CiteULike by submitting a URL. PubSpork uses a DOI url if it can find one.  Otherwise it uses the direct URL of the publication.

If the PubSpork submit fails, *click* on **MyCiteULike** &rarr; **Post URL** and try submitting the the pub's DOI URL and/or direct URL.

**2. Submit a pub ID**

The **Post URL** form also supports submitting DOIs (doi:10.xxxx), PubMed IDs (pmid:nnnnnnn), and ISBNs (isbn:nnnnnnn).  Try these, if you have them.  (And a **Search PubMed** link is in the generated HTML page for every new pub.)

**3. Import BibTeX or RIS for the publication**

CiteULike allows you to directly import RIS or BibTeX and many websites support exporting a citation to the publication in one of both of these formats.  To do this, navigate to:

- if you are adding pubs to just your personal library:
  - **MyCiteULike** &rarr; **Import**
- if you re adding pubs to a CiteULike group:
  - **MyCiteULike** &rarr; **Groups** &rarr;  *your group's library page* &rarr;
    **Group:** *your group's name* &rarr;  **Import**

and then paste the RIS or BibTeX into the form and submit it.  Note that the item may require some manual editing of keywords after entering.


#### What if the pub's website does not support RIS or BibTeX export?

Then fall back on Google Scholar.  Use the Search Google Scholar link in the generated HTML to find the pub in Google Scholar.  Every pub in Google Scholar has a cite link that can be used to
generate minimal BibTeX for the publication.


### Zotero

To add a paper to Zotero, follow the link in the generated HTML page to the paper itself.  If the paper is relevant, then click on the *Zotero Connector* button in your browser.

*Wait, what?*  If you are using Zotero to manage publications then you'll need to do a couple of things.

1. Get a Zotero account.
1. Install the Zotero client on your laptop.
1. Connect your Zotero desktop client to your Zotero account.
1. Install the Zotero Connector in your web browser

#### Setting up Zotero

##### Get a Zotero account 

If you don't already have a Zotero account, you'll need to [set one up](https://www.zotero.org/user/register/). You'll need to confirm your account through your email.  You can use the free account: you won't need any storage for this work as we don't store PDFs in the Galaxy Group.

##### Install the Zotero client on your computer

To add publications you'll need to [download and install](https://www.zotero.org/download/) the Zotero Client.  The client is available for Mac, Linux, and Windows.

##### Connect your Zotero desktop client to your Zotero account.

This is in **Preferences** in your client.

##### Install the Zotero Connector in your web browser

The Zotero Connect adds a button to your browser's menu to send the publication you are currently viewing to the Zotero client on your computer.  The Connector automatically imports a wealth of metadata from most publishers.

(You can also enter information manually, or import BibTeX, but that's a bad default option.)

The [Zotero Connector](https://www.zotero.org/download/) is available for for Chrome, Firefox, Safari, and Opera.  A [bookmarklet](https://www.zotero.org/downloadbookmarklet) is also available for other browsers, tablets, and phones.

#### Adding publications to Zotero

Clicking on the Zotero Connector in your web browser sends the publication on that page to your desktop Zotero client.  It then does the best job it can at prepopulating the pub's metadata and then automatically adds it to your Zotero library.

At this point you can add tags if you want to.

Meanwhile, Zotero is automatically syncing any updates you make in the client back to the online version of your library back at Zotero.org.

## How is my *known pubs DB* updated?

The *known pubs DB* contains every publication you have ever looked at, including the irrelevant ones.  It is used to help generate the HTML page used in curation, and to help avoid looking at any paper more than once.

It is updated in two ways:

- By running PubSpork with `--match`.  This does a couple of things
  - Adds entries for any publications that were reported for the first time.
  - Updates or adds entries for every publications in your *relevant pubs lib* to indicate that we know about them, and that they have already been processed.
- Manually by you, while you are curating relevant papers. using a spreadsheet program

### Manually updating the *known pubs DB*

This may be the most tedious and error prone part of this process. I hope to replace this with generated JavaScript that produces buttons in the HTML report that automatically update the database, but we aren't there yet.

To manually update the *known pubs DB*:

- Open the TSV file in a spreadsheet program.  LibreOffice does well with TSV format.
- As you walk through the generated HTML page, some publications will be added to your *relevant pubs lib*, but some of the newly reported publications will be irrelevant (especially if you have a project name like Galaxy or R).  In order to avoid looking at this publication again next time:
  - Find the irrelevant publication in the spreadsheet.
  - Set the `state` column to `ignore`
  - Optionally add a comment to the annotation column about why the pub is irrelevant

# Reporting

The `--report` function generated the selected library report.

...

"""
Orchestration for downloading paper metadata and downloading the pdf. Also,
storage and debugging of failed requests.
"""

import os
import random
from StringIO import StringIO
import logging
log = logging.getLogger("paperbot.orchestrate")

import requests
import pdfparanoia

from logstuff import loghijack
from paper import Paper

from storage import (
    store,
    store_json,
    store_logs,
)

from ezproxy import EZPROXY_CONFIG
from httptools import run_url_fixers

from htmltools import (
    parse_html,
    populate_metadata_from_tree,
)

from libgen import (
    make_libgen_doi_url,
    check_libgen_has_paper,
    upload_to_libgen,
)

USER_AGENT = os.environ.get("USER_AGENT", "pdf-defense-force-" + ("%0.2x" % random.getrandbits(8)))

DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
}

def is_response_pdf(response):
    """
    Determines if the response contains a pdf.
    """
    return "pdf" in response.headers["content-type"]

def remove_watermarks(pdfcontent):
    """
    Use pdfparanoia to remove watermarks from the pdf.
    """
    log.debug("Removing pdf watermarks.")
    pdfcontent = pdfparanoia.scrub(StringIO(pdfontent))
    return pdfcontent

def iterdownload(url, paper, headers=DEFAULT_HEADERS, ezproxy_config=EZPROXY_CONFIG):
    """
    Download the content at the remote url. Use a variety of methods. Not all
    methods are always necessary. Sometimes none of the methods will return the
    desired content.
    """
    # list of responses
    paper.history = []

    # attempt to get without using ezproxy
    log.debug("Attempting HTTP GET {}".format(url))
    response = requests.get(url, headers=headers)
    paper.history.append(response)
    yield (url, response)

    for ezproxyconf in ezproxy_config:
        ezproxyurl = ezproxyconf["url"]

        # POSTable data to login to this ezproxy
        proxydata = ezproxyconf["data"]

        # construct url based on ezproxy url plus desired url
        attempturl = ezproxyurl + url

        # ezproxy attempt
        log.debug("Attempting ezproxy HTTP {}".format(attempturl))
        response = requests.post(attempturl, data=proxydata, headers=headers)
        paper.history.append(response)

        # maybe this response is acceptable?
        yield (attempturl, response)

def download(url, paper=None):
    """
    Main entry point for executing paperbot's primary function, paper fetching.
    The given url may be to a pdf file, which should be archived, or it may be
    to an academic publisher's website which points to a paper. The paper needs
    to be downloaded and the metadata should be stored.

    Returns a tuple of (paper, json_path, pdf_path, logpath).

    :param url: url to fetch and examine
    :type url: str
    """
    # store logs in tempfile
    (templogpath, loghandler) = loghijack()

    if paper is None:
        paper = Paper.create({})

    # clean up url if necessary
    url = run_url_fixers(url)

    # whether or not metadata has already been populated
    populated_metadata = False

    for (url2, response) in iterdownload(url, paper=paper):
        if is_response_pdf(response):
            log.debug("Got pdf.")
            pdfcontent = remove_watermarks(response.content)
            paper.pdf = pdfcontent
            store(paper)
            break
        else:
            paper.html = response.content

            # Was not pdf. Attempt to parse the HTML based on normal expected
            # HTML elements. The HTML elements may say that the actual pdf url
            # is something else. If this happens, then attempt to download that
            # pdf url instead and then break out of this loop.

            # no reason to get same metadata on every iteration of loop
            if not populated_metadata:
                tree = parse_html(response.content)

                # most publishers show paper metadata in html in same way because ?
                populate_metadata_from_tree(tree, paper)

                # TODO: better way to check if populate_metadata_from_tree did
                # anything useful?
                if paper.title in [None, ""]:
                    log.debug("# TODO: parse metadata from html using plugins here")
                else:
                    populated_metadata = True

            # can't try anything else if the url is still bad
            if paper.pdf_url in [None, ""]:
                continue

            if paper.pdf_url == url:
                # pdf_url is same as original url, no pdf found yet. This
                # happens when the pdf url is correct, but the publisher is
                # returning html instead. And the html happens to reference the
                # url that was originally requested in the first place. Argh.
                continue
            else:
                log.debug("Switching activity to pdf_url {}".format(paper.pdf_url))

                # paper pdf is stored at a different url. Attempt to fetch that
                # url now. Only do this if pdf_url != url because otherwise
                # this will be an endless loop.
                for (url3, response2) in iterdownload(paper.pdf_url, paper=paper):
                    if is_response_pdf(response2):
                        log.debug("Got pdf on second-level page.")
                        pdfcontent = remove_watermarks(response.content)
                        paper.pdf = pdfcontent
                        store(paper)
                        break
                else:
                    log.debug("Couldn't download pdf from {}".format(paper.pdf_url))

                break

    # was pdf downloaded?
    if (hasattr(paper, "pdf") and paper.pdf not in [None, ""]) or os.path.exists(paper.file_path_pdf):
        fetched = True
    else:
        fetched = False

    hasdoi = (paper.doi not in [None, ""])

    if hasdoi:
        # check if libgen has this paper already
        libgenhas = check_libgen_has_paper(paper.doi)

        if fetched and not libgenhas:
            # upload if libgen doesn't already have it
            upload_to_libgen(paper.file_path_pdf, paper.doi)
        elif not fetched and libgenhas:
            urldoi = make_libgen_doi_url(paper.doi)

            # get from libgen
            log.debug("Haven't yet fetched paper. Have doi. Also, libgenhas.")
            log.debug("HTTP GET {}".format(urldoi))
            response = requests.get(urldoi, headers=DEFAULT_HEADERS)

            if is_pdf_response(response):
                log.debug("Got pdf from libgen.")

                # skip pdfparanoia because it's from libgen
                pdfcontent = response.content
                paper.pdf = pdfcontent

                store(paper)

                fetched = True
            else:
                log.debug("libgen lied about haspdf :(")
    else:
        log.debug("Don't know doi, can't check if libgen has this paper.")
        libgenhas = None

    # store(paper) usually handles json but in case of failure there needs to
    # be an explicit save of paper metadata.
    if not fetched:
        store_json(paper)

    # move logs into position
    logpath = store_logs(paper, templogpath)

    # remove loghandler from logger
    mainlogger = logging.getLogger("paperbot")
    mainlogger.handlers.remove(loghandler)

    return (paper, paper.file_path_json, paper.file_path_pdf, logpath)

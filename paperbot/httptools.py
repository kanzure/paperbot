"""
Utilities related to HTTP requests.
"""

import logging
log = logging.getLogger("paperbot.httptools")

from urllib import (
    unquote,
    quote_plus,
)

import requests


def run_url_fixers(url):
    """
    Clean up some common url problems.
    """
    log.debug("Running possible fixes on url: {}".format(url))

    origurl = url
    url = fix_ieee_login_url(url)
    url = fix_jstor_pdf_url(url)

    if origurl != url:
        log.debug("Fixed url to: {}".format(url))

    return url


def is_same_url(url1, url2):
    """
    Normalize the given urls and check whether or not they are referencing the
    same resource.
    """
    log.debug("Comparing two urls:\nurl1: {}\nurl2: {}".format(url1, url2))
    url1 = run_url_fixers(url1)
    url2 = run_url_fixers(url2)
    return url1 == url2


def fix_ieee_login_url(url):
    """
    Fixes urls point to login.jsp on IEEE Xplore. When someone browses to the
    abstracts page on IEEE Xplore, they are sometimes sent to the login.jsp
    page, and then this link is given to paperbot. The actual link is based on
    the arnumber.

    example:
    http://ieeexplore.ieee.org/xpl/login.jsp?tp=&arnumber=806324&url=http%3A%2F%2Fieeexplore.ieee.org%2Fxpls%2Fabs_all.jsp%3Farnumber%3D806324
    """
    if "ieeexplore.ieee.org/xpl/login.jsp" in url:
        if "arnumber=" in url:
            parts = url.split("arnumber=")

            # i guess the url might not look like the example in the docstring
            if "&" in parts[1]:
                arnumber = parts[1].split("&")[0]
            else:
                arnumber = parts[1]

            return "http://ieeexplore.ieee.org/xpl/articleDetails.jsp?arnumber={}".format(arnumber)

    # default case when things go wrong
    return url


def fix_jstor_pdf_url(url):
    """
    Fixes urls pointing to jstor pdfs.
    """
    if "jstor.org/" in url:
        if ".pdf" in url and "?acceptTC=true" not in url:
            url += "?acceptTC=true"
    return url

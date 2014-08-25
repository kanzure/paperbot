"""
Check libgen for content. Upload to libgen.
"""

import requests
import logging

from htmltools import parse_html

from httptools import (
    quote_plus,
)

log = logging.getLogger("paperbot.libgen")

def make_libgen_doi_url(doi):
    """
    Make libgen url based on DOI.
    """
    return "http://libgen.org/scimag/get.php?doi={}".format(quote_plus(doi))

def check_libgen_has_paper(doi):
    """
    Check if libgen has a copy of this paper.
    """
    log.debug("check_libgen_has_paper doi {}".format(doi))

    # figure out where libgen would be storing it
    url = make_libgen_doi_url(doi)

    # knock on libgen server
    paper_uri = requests.head(url)

    if paper_uri.status_code == 200:
        return True
    else:
        return False

def build_libgen_auth_fragment():
    """
    Construct authentication header for another request.
    """
    # found on some libgen forum maybe?
    authfragment = requests.auth.HTTPBasicAuth("genesis", "upload")
    return authfragment

def upload_to_libgen(paperpath, doi):
    """
    Store the paper on libgen.
    """
    # need to provide some credentials to libgen
    authfragment = build_libgen_auth_fragment()

    files = {
        "uploadedfile": ("derp.pdf", paperpath),
    }

    data = {
        "doi": doi,
    }

    kwargs = {
        "auth": authfragment,
        "files": files,
        "data": data,
    }

    log.debug("Uploading to libgen doi {} path {}".format(doi, paperpath))
    response = requests.post("http://libgen.org/scimag/librarian/form.php", **kwargs)

    # parse returned html
    tree = parse_html(response)

    # build dict with all named fields from html
    formp = dict(map(lambda x: (x.get("name"), x.get("value")), tree.xpath("//input[@name]")))

    log.debug("Submitting form back to libgen.")
    response = requests.get("http://libgen.org/scimag/librarian/register.php", data=formp, auth=authfragment)

    urldoi = make_libgen_doi_url(doi)
    log.debug("Completed libgen upload: {}".format(urldoi))

    return urldoi

from StringIO import StringIO
import lxml.etree

from paper import meta_attribute_mapping

import logging
log = logging.getLogger("paperbot.htmlstuff")

def is_html(response):
    """
    Check if a python-requests Response object contains a text/html response.
    """
    return "text/html" in response.headers["content-type"]

def parse_html(content):
    """
    lxml.etree from html text

    :param content: html text
    :type content: str or StringIO
    """
    log.debug("parse_html")
    if not isinstance(content, StringIO):
        content = StringIO(content)
    parser = lxml.etree.HTMLParser()
    tree = lxml.etree.parse(content, parser)
    return tree

def extract_meta_content(tree, meta_name):
    content = tree.xpath("//meta[@name='" + meta_name + "']/@content")[0]
    return content

def get_citation_title(tree):
    """
    Return the <meta name="citation_title"> content attribute.
    """
    citation_title = extract_meta_content(tree, "citation_title")
    return citation_title

def get_citation_pdf_url(tree):
    citation_pdf_url = extract_meta_content(tree, "citation_pdf_url")
    return citation_pdf_url

def extract_metadata(tree, meta_attribute_mapping=meta_attribute_mapping):
    """
    Extract common metadata from the HTML document.

    :rtype: dict
    """
    output = {}

    for (metakey, paperkey) in meta_attribute_mapping.iteritems():
        try:
            value = extract_meta_content(tree, metakey)
        except:
            log.debug("Couldn't find {metakey} in the html.".format(metakey=metakey))
        else:
            log.debug("Found {metakey} with value {value}".format(value=value))
            output[paperkey] = value

    return output

def populate_metadata_from_tree(tree, paper, meta_attribute_mapping=meta_attribute_mapping):
    """
    Update paper metadata based on data from parsing the html tree.
    """
    data = extract_metadata(tree, meta_attribute_mapping=meta_attribute_mapping)

    for (key, value) in data.iteritems():
        log.debug("metadata | {key} => {value}".format(key=key, value=value))
        setattr(paper, key, value)

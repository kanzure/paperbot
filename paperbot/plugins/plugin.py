"""
Basic plugin system for different scrapers.
"""

import logging
log = logging.getLogger("paperbot.plugins.plugin")


class Plugin(object):
    """
    Pluggable system for loading different scrapers for different publishers.
    """

    @staticmethod
    def check_url(url):
        """
        Check the url to determine if this plugin handles the url.

        :rtype: bool
        """
        raise NotImplementedError()

    @staticmethod
    def scrape(url, tree, pdfmeta):
        """
        Extract additional metadata about the paper from the page, including
        its pdf url. Returns pdfmeta.

        :param url: url where page content is from
        :param tree: lxml.etree (parsed html)
        :param pdfmeta: a Paper model representing extracted data
        :type pdfmeta: Paper
        :rtype: Paper
        """
        raise NotImplementedError()

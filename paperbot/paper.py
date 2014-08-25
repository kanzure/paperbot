"""
Generic model of a paper.
"""

from modelo import Model
import modelo.trait.trait_types as field

# Mapping between HTML meta attribute names and variables on the Paper model.
meta_attribute_mapping = {
    "citation_journal_title": "journal_title",
    "citation_journal_abbrev": "journal_abbrev",
    "citation_issn": "journal_issn",
    "citation_publisher": "publisher",
    "citation_title": "title",
    "citation_online_date": "online_publication_date",
    "citation_publication_date": "publication_date",
    "citation_volume": "journal_volume",
    "citation_issue": "journal_issue",
    "citation_firstpage": "pagenumber",
    "citation_doi": "doi",
    "citation_abstract_html_url": "url",
    "citation_pdf_url": "pdf_url",
    "citation_language": "language",
}

class Paper(Model):
    """
    Represents collected information about a paper.
    """

    title = field.String()
    doi = field.String()

    abstract = field.String()
    keywords = field.List(field.String())

    # url directly to the pdf from the publisher
    pdf_url = field.String()

    # publisher url
    url = field.String()

    # where the pdf is stored on this server
    file_path_pdf = field.String()

    # where metadata is stored about the paper
    file_path_json = field.String()

    publication_date = field.String()
    online_publication_date = field.String()

    authors = field.List(field.String())

    journal_title = field.String()
    journal_abbrev = field.String()
    journal_volume = field.String()
    journal_issue = field.String()
    journal_issn = field.String()
    pagenumber = field.String()

    publisher = field.String()

    # html from page before downloading pdf
    html = field.String()

    # paper hasn't been stored yet
    stored = field.Bool(default=False)

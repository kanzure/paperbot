"""
Store a paper to the file system.
"""

import os
import json
import random
import hashlib
import shutil

import logging
log = logging.getLogger("paperbot.storage")

DEFAULT_STORAGE_PATH = "/home/bryan/public_html/papers2/paperbot/"
if not os.path.exists(DEFAULT_STORAGE_PATH):
    DEFAULT_STORAGE_PATH = "/tmp/"
STORAGE_PATH = os.environ.get("STORAGE_PATH", DEFAULT_STORAGE_PATH)


def make_random_string(bits=128):
    """
    Make a random string suitable as a filename.
    """
    return "%0.2x" % random.getrandbits(bits)


def make_hash(content):
    """
    Calculate md5 sum of the content.
    """
    md5sum = hashlib.md5()
    md5sum.update(content)
    return md5sum.hexdigest()


def make_pdf_filename(paper, pdfcontent=None):
    """
    Construct a filename for the pdf of this paper.
    """
    if paper.title in ["", None]:
        if pdfcontent:
            paper.title = make_hash(pdfcontent)
        else:
            paper.title = make_random_string()

    pdf_filename = "{}.pdf".format(paper.title)

    # don't create directories
    pdf_filename = pdf_filename.replace("/", "_")

    return pdf_filename


def make_full_path(filename, storage_path=STORAGE_PATH):
    """
    Construct a full path including the filename.
    """
    return os.path.join(storage_path, filename)


def store_json(paper, storage_path=STORAGE_PATH):
    """
    Store paper metadata somewhere.
    """
    if not paper.file_path_json or paper.file_path_json in [None, ""]:
        name = make_random_string()
        filename = name + ".json"
        jsonpath = make_full_path(filename, storage_path=storage_path)
    else:
        jsonpath = paper.file_path_json

    # may be a new path, store it
    paper.file_path_json = jsonpath

    # convert dict data to json
    output = json.dumps(paper.to_dict())

    log.debug("Storing paper metadata to {}".format(jsonpath))
    with open(jsonpath, "w") as jsonfile:
        jsonfile.write(output)

    return jsonpath


def store_logs(paper, templogpath):
    """
    Store logs near other paper files. Return the path.
    """
    jsonpath = paper.file_path_json
    filename = jsonpath[0:-5]

    # compute the desired log file path
    desiredpath = os.path.abspath(filename + ".log")

    # move the log file into position
    log.debug("Moving log from {} to {}".format(templogpath, desiredpath))
    shutil.move(templogpath, desiredpath)

    return desiredpath


def store(paper, pdfcontent=None):
    """
    Save a paper to the file system.

    Returns a tuple of (json_path, pdf_path).
    """
    log.debug("Storing the paper.")

    if pdfcontent is None:
        pdfcontent = paper.pdf

    pdf_filename = make_pdf_filename(paper, pdfcontent)
    pdf_path = make_full_path(pdf_filename)
    paper.file_path_pdf = pdf_path

    with open(pdf_path, "w") as pdfdoc:
        log.debug("Storing pdf to {}".format(pdf_filename))
        pdfdoc.write(pdfcontent)

    json_filename = pdf_filename + ".json"
    json_path = make_full_path(json_filename)
    paper.file_path_json = json_path
    jsondata = json.dumps(paper.to_dict())

    paper.stored = True

    with open(json_path, "w") as jsondoc:
        log.debug("Storing paper metadata at {}".format(json_filename))
        jsondoc.write(jsondata)

    return (json_path, pdf_path)

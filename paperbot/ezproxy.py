"""
Use some ezproxy urls and credentials.
"""

import os
import json
import logging
log = logging.getLogger("paperbot.ezproxy")

# This directory stories json files that each contain information about a
# unique ezproxy endpoint that could be tried.
EZPROXY_DIR = os.environ.get(
    "EZPROXY_DIR",
    os.path.abspath(
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "../ezproxy"
        )
    )
)

# Default ezproxy config is empty because none of the files have been loaded yet.
EZPROXY_CONFIG = {}

def load_ezproxy_config(ezproxy_dir=EZPROXY_DIR):
    """
    Load ezproxy config from json files. These files contain information such
    as the ezproxy url template, username, password, and possibly other
    details.
    """
    if not os.path.exists(ezproxy_dir):
        log.debug("Not loading ezproxy configs because EZPROXY_DIR doesn't exist: {}".format(ezproxy_dir))
        return {}

    # blank the existing ezproxy configs
    EZPROXY_CONFIG = {}

    # look at the directory to see config files
    filenames = os.listdir(ezproxy_dir)

    for filename in filenames:
        # ignore filenames that can't have .json
        badcondition1 = (len(filename) <= len(".json"))

        # ignore non-json files
        badcondition2 = (".json" not in filename[-5:])

        if badcondition1 or badcondition2:
            log.debug("Not loading file from EZPROXY_DIR: {}".format(filename))
            continue
        else:
            log.debug("Loading ezproxy file: {}".format(filename))

        # name of ezproxy is given by filename
        name = filename[0:-5]

        # get abspath to this json file
        realpath = os.path.abspath(os.path.join(ezproxy_dir, filename))

        # open up the file to read ezproxy config
        with open(realpath, "r") as configfile:
            config = configfile.read()

        # parse config as json
        ezconfig = json.loads(config)

        # dump in some extra data why not
        ezconfig.update({
            "name": name,
            "realpath": realpath,
        })

        # store this config for later
        EZPROXY_CONFIG[name] = ezconfig

    return EZPROXY_CONFIG

# default action is dothings
load_ezproxy_config()

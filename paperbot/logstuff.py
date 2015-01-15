import tempfile
import logging


def setup_logging():
    """
    Setup default logging handler to avoid "No handler found" warnings.
    """
    try:  # python 2.7+
        from logging import NullHandler
    except ImportError:
        class NullHandler(logging.Handler):
            def emit(self, record):
                pass
    finally:
        logging.getLogger("paperbot").addHandler(NullHandler())

    # this might be rude to enforce?
    logging.basicConfig(format='%(levelname)s:%(message)s',
                        level=logging.DEBUG)


def loghijack():
    """
    Hijack the logs for paperbot to go straight to a temporary file. The logs
    should still also be going to whatever other places have been configured.
    """
    logpath = tempfile.mktemp()

    logger = logging.getLogger("paperbot")
    fh = logging.FileHandler(logpath)
    logger.addHandler(fh)

    return (logpath, fh)

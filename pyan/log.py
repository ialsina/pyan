import logging
import socket

def setup_logging(verbose=False, very_verbose=False, file=None):

    # TODO: use an int argument for verbosity
    logger = logging.getLogger()

    if very_verbose:
        logger.setLevel(logging.DEBUG)

    elif verbose:
        logger.setLevel(logging.INFO)

    else:
        logger.setLevel(logging.WARN)

    logger.addHandler(logging.StreamHandler())

    if file:
        handler = logging.FileHandler(file)
        logger.addHandler(handler)


def host_log_adapter(logger):
    hostname = {"hostname": socket.gethostname()}
    return logging.LoggerAdapter(logger, hostname)

logger = host_log_adapter(logging.getLogger())


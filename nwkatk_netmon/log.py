import sys
import logging

log = logging.getLogger(__name__)
log.addHandler(logging.StreamHandler(stream=sys.stdout))
log.handlers[0].setFormatter(
    logging.Formatter(fmt="%(asctime)s %(levelname)s: %(message)s")
)
# log.setLevel(logging.INFO)

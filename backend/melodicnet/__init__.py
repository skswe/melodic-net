import logging

from . import core, dataparser, encoding, globals, models, utils
from .core import MelodicNet
from .dataparser import DataParser, MIDIUtils
from .encoding import (
    ManyHotChords,
    OneHotEvents,
    OneHotEventsCD,
    OneHotEventsWithOD,
    SingleEvents,
    SingleEventsWithoutOD,
    SingleNotes,
)

root_logger = logging.getLogger("melodicnet")
root_logger.setLevel(logging.INFO)
root_logger.addHandler(logging.StreamHandler())
root_logger.handlers[0].setFormatter(globals.LOGGING_FORMATTER)

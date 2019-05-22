import logging


logger = logging.getLogger(__name__)


from .default_config import *

try:
    from mop_general_config import *
except ImportError:
    logger.info("No general config found")

try:
    from mop_project_config import *
except ImportError:
    logger.info("No project config found")


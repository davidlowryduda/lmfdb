from lmfdb.utils import make_logger
typed_data_logger = make_logger("typed_data_logger", hl=True)

from . import type_generation
assert type_generation
from . import standard_types
assert standard_types
from . import artin_types
assert artin_types

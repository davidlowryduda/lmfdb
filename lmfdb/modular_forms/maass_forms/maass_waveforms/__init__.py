# -*- coding: utf-8 -*-

from lmfdb.utils import make_logger
from flask import Blueprint

MWF = "mwf"  # Maass waveforms
mwf = Blueprint(MWF, __name__, template_folder="views/templates", static_folder="views/static")
mwf_logger = make_logger(mwf)

from . import backend
assert backend
from . import views
assert views

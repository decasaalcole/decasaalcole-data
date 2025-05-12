from typing import NamedTuple
import os

CARTOCIUDAD_PROVINCES_IDS = {
    "alicante": 9106,
    "castellon": 9088,
    "valencia": 9129,
}

DEFAULTS = {
    "working_dir": os.getcwd(),
    "province": "all",
    "force": False,
    "threads": 3,
}

STREET_NUMBERS_FIELDS = [
    "id_porpk",
    "codigo_postal",
    "tipo_vial",
    "poblacion",
]

CLUSTERING_PARAMETERS = {
    "eps": 250,
    "min_samples": 20,
    "metric": "euclidean",
}

class Config(NamedTuple):
    """
    Application configuration
    """

    working_dir: str = DEFAULTS["working_dir"]
    province: str = DEFAULTS["province"]
    force: bool = DEFAULTS["force"]
    threads: int = DEFAULTS["threads"]

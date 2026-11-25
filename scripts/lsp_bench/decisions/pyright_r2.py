"""Screening decisions: pyright, second-round sheet pyright_r2_00.txt.

Run line: imported by decisions/__init__.py, not run directly.
"""
from typing import Dict, Tuple

SERVER = "pyright"

KEEP: Dict[int, Tuple[str, str, str, str]] = {
    641: ("R4", "B", "Accepting the auto-import completion for Column inserts 'from sqlalchemy-stubs.sql.schema import Column', naming the stubs package directory, which is not a valid module path.", "completion: install sqlalchemy and sqlalchemy-stubs, complete 'Colum', accept the auto-import; check new errors"),
}

REJECT: Dict[str, Tuple[int, ...]] = {
    "type": (678, 2164, 3441, 5065, 6850, 10766),
    "crash": (1279, 3433, 4535, 9740),
    "display": (9562,),
}

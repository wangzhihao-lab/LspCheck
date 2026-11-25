"""Screening decisions: rust-analyzer, issues added by the recall audit (recall_audit.INCLUDE).

Run line: imported by decisions/__init__.py, not run directly.
"""
from typing import Dict, Tuple

SERVER = "rust-analyzer"

KEEP: Dict[int, Tuple[str, str, str, str]] = {
    14841: ("R3", "A", "In format!(\"{} {} {}\", a, vec![2, 3], a), go to definition on the first a reaches the local, but on the second a it lands inside the vec! expansion.", "def-consistency: definition from each occurrence of a must give the same target"),
}

REJECT: Dict[str, Tuple[int, ...]] = {}

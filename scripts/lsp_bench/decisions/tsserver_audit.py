"""Screening decisions: tsserver, issues added by the recall audit (recall_audit.INCLUDE).

Run line: imported by decisions/__init__.py, not run directly.
"""
from typing import Dict, Tuple

SERVER = "tsserver"

KEEP: Dict[int, Tuple[str, str, str, str]] = {
    57498: ("R4", "A", "Applying the fix-all 'Delete all unused declarations' removes nothing when an unused function refers to itself, although deleting that single declaration works.", "quickfix: noUnusedLocals, self-recursive unused function; apply fix-all unused; the unused diagnostic must disappear"),
    44374: ("R4", "B", "With importModuleSpecifierEnding set to js, module-path string completions still insert the '.ts' extension, and an import path ending in '.ts' is an error before TypeScript 5.0.", "completion: set preference importModuleSpecifierEnding=js, accept a relative path completion in an import; count errors"),
}

REJECT: Dict[str, Tuple[int, ...]] = {}

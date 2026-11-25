"""Specification probe for the benchmark ground truth: edit_text_differs.

Some reported wrong edits still parse, and the server suppresses the error they cause (for
example gopls hides type errors in files with parse errors), so edit_breaks_syntax and
edit_leaves_diagnostic cannot see them. For those, the issue or the fix's regression test
states the expected output text, and this probe compares the offered edit's result with it.

This is a specification check used only to establish the ground truth of a case (the
reported behavior on the pre-fix build, and its absence on the post-fix build, which must
produce exactly the expected text). It is not one of the tool's oracles: cases that use it
are reported separately when measuring what the ground-truth-free oracles detect.

params: {"edit": <edit spec, see probes_derived.py>,
         "expected": {"path", "text", "source"}}  # source: "issue body" or "<test file>@<fix sha>"

Run line: imported by probes.py; not run directly.
"""

from __future__ import annotations

from typing import Any, List, Mapping, Sequence

from .probes import Answers, Probe, ProbeResult, absent, invalid, present, register_probe
from .probes_derived import _edit, changed_lines, check_edit


def _lf(text: Any) -> str:
    return str(text).replace("\r\n", "\n")


@register_probe("edit_text_differs")
class EditTextDiffers(Probe):
    """Present iff the offered edit's result for expected.path differs from expected.text
    (line endings compared as LF)."""

    def queries(self, params: Mapping[str, Any]) -> Mapping[str, List[Any]]:
        return {"case": []}

    def validate(self, params: Mapping[str, Any], ops: Sequence[Any]) -> List[str]:
        e = params.get("expected")
        ok = isinstance(e, dict) and e.get("path") and isinstance(e.get("text"), str) and e.get("source")
        bad = [] if ok else ["expected: {path, text, source} (the fixed output and where it comes from)"]
        return check_edit(params.get("edit")) + bad

    def decide(self, params: Mapping[str, Any], answers: Answers) -> ProbeResult:
        e, bad = _edit(params, answers)
        if bad:
            return bad
        exp = params["expected"]
        got = (e.get("texts_after") or {}).get(exp["path"])
        if got is None:
            return invalid(f"the edit {e.get('chosen')!r} does not change {exp['path']}")
        ev = {"chosen": e.get("chosen"), "changed": changed_lines(e), "source": exp["source"]}
        if _lf(got) != _lf(exp["text"]):
            return present(f"{e.get('chosen')!r} differs from the expected text", **ev)
        return absent(f"{e.get('chosen')!r} gives the expected text", **ev)


__all__ = ["EditTextDiffers"]

"""Prepare the second lsptest corpus batch with the frozen first-batch pipeline.

A wrapper around scripts/lsptest/prepare_corpus.py (frozen, imported unchanged).
Before any other module of the package scripts/lsptest/corpus/ is imported, the
path constants of corpus/common.py are pointed at the second batch:

  CORPUS_JSON -> data/lsptest/corpus_v2.json
  OUT_JSON    -> data/lsptest/corpus_v2_prepared.json
  OUT_MD      -> data/lsptest/corpus_v2_prepared.md
  LOG_DIR     -> data/lsptest/logs/prepare_corpus_v2

The other modules bind these names with `from .common import X` at import time,
and some functions carry them as default arguments; so the package is built by
hand (common.py first, patched, then the package __init__ that imports the rest),
and every function default still equal to an old path is replaced. A final check
fails the run if any module global or default still holds an old path. Clone and
probe directories (temp/corpus, temp/corpus_probe) are shared with the first batch
(entries are named owner__repo@sha12). All command-line options and their
defaults are those of prepare_corpus.py.

Run line: python3 -I scripts/paper/corpus2/prepare_corpus2.py [prepare_corpus.py options]
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
import os
import sys
import types
from typing import Dict

sys.dont_write_bytecode = True
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
LSPTEST = os.path.join(REPO, "scripts", "lsptest")
PKG_DIR = os.path.join(LSPTEST, "corpus")
DATA = os.path.join(REPO, "data", "lsptest")
NEW_PATHS: Dict[str, str] = {
    "CORPUS_JSON": os.path.join(DATA, "corpus_v2.json"),
    "OUT_JSON": os.path.join(DATA, "corpus_v2_prepared.json"),
    "OUT_MD": os.path.join(DATA, "corpus_v2_prepared.md"),
    "LOG_DIR": os.path.join(DATA, "logs", "prepare_corpus_v2"),
}

logger = logging.getLogger(__name__)


def _patch_defaults(fn: object, old_to_new: Dict[str, str]) -> None:
    """Replace default argument values equal to an old path (positional and keyword-only)."""
    defaults = getattr(fn, "__defaults__", None)
    if defaults:
        fn.__defaults__ = tuple(old_to_new.get(d, d) if isinstance(d, str) else d  # type: ignore[attr-defined]
                                for d in defaults)
    kw = getattr(fn, "__kwdefaults__", None)
    if kw:
        fn.__kwdefaults__ = {k: old_to_new.get(v, v) if isinstance(v, str) else v  # type: ignore[attr-defined]
                             for k, v in kw.items()}


def _patch_module(mod: types.ModuleType, old_to_new: Dict[str, str]) -> None:
    """Patch globals and function / class-__init__ defaults of one module."""
    for name, val in list(vars(mod).items()):
        if isinstance(val, str) and val in old_to_new:
            setattr(mod, name, old_to_new[val])
        elif isinstance(val, types.FunctionType):
            _patch_defaults(val, old_to_new)
        elif isinstance(val, type):
            _patch_defaults(getattr(val, "__init__", None), old_to_new)


def _residual_old_paths(old_to_new: Dict[str, str]) -> list[str]:
    """Places in the loaded corpus modules that still hold an old path."""
    left: list[str] = []
    for mname, mod in sys.modules.items():
        if not (mname == "corpus" or mname.startswith("corpus.")):
            continue
        for name, val in vars(mod).items():
            if isinstance(val, str) and val in old_to_new:
                left.append(f"{mname}.{name}")
            fns = [val] if isinstance(val, types.FunctionType) else (
                [getattr(val, "__init__", None)] if isinstance(val, type) else [])
            for fn in fns:
                vals = list(getattr(fn, "__defaults__", None) or ()) + list(
                    (getattr(fn, "__kwdefaults__", None) or {}).values())
                if any(isinstance(v, str) and v in old_to_new for v in vals):
                    left.append(f"{mname}.{name} (default argument)")
        # dataclass field defaults are also kept on the class
        for name, val in vars(mod).items():
            fields = getattr(val, "__dataclass_fields__", None) if isinstance(val, type) else None
            for fname, fld in (fields or {}).items():
                if isinstance(fld.default, str) and fld.default in old_to_new:
                    left.append(f"{mname}.{name}.{fname} (dataclass field)")
    return left


def load_patched_package() -> types.ModuleType:
    """Import scripts/lsptest/corpus with common.py's paths pointed at the second batch."""
    if LSPTEST not in sys.path:
        sys.path.insert(0, LSPTEST)
    if "corpus" in sys.modules:
        raise RuntimeError("package 'corpus' already imported; the paths can no longer be patched safely")
    spec = importlib.util.spec_from_file_location("corpus", os.path.join(PKG_DIR, "__init__.py"),
                                                  submodule_search_locations=[PKG_DIR])
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load package from {PKG_DIR}")
    pkg = importlib.util.module_from_spec(spec)
    sys.modules["corpus"] = pkg
    common = importlib.import_module("corpus.common")  # runs common.py only
    old_to_new = {getattr(common, k): v for k, v in NEW_PATHS.items()}
    _patch_module(common, old_to_new)
    for k, v in NEW_PATHS.items():
        assert getattr(common, k) == v, k
    spec.loader.exec_module(pkg)  # imports clone_deps, probe, records, report against patched common
    for mname, mod in list(sys.modules.items()):
        if mname == "corpus" or mname.startswith("corpus."):
            _patch_module(mod, old_to_new)
            for val in list(vars(mod).values()):
                fields = getattr(val, "__dataclass_fields__", None) if isinstance(val, type) else None
                for fld in (fields or {}).values():
                    if isinstance(fld.default, str) and fld.default in old_to_new:
                        fld.default = old_to_new[fld.default]
    left = _residual_old_paths(old_to_new)
    if left:
        raise RuntimeError(f"old first-batch paths still bound in: {left}")
    return pkg


def main() -> None:
    """Patch the package, then run the frozen prepare_corpus.main() with the same arguments."""
    load_patched_package()
    import prepare_corpus  # noqa: E402  (frozen command line; its `from corpus import ...` sees the patch)

    for k, v in NEW_PATHS.items():
        if hasattr(prepare_corpus, k) and getattr(prepare_corpus, k) != v:
            raise RuntimeError(f"prepare_corpus.{k} is not patched")
    logging.getLogger(__name__).info("second batch: %s", NEW_PATHS)
    prepare_corpus.main()


if __name__ == "__main__":
    main()

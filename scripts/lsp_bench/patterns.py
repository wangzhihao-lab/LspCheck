"""Keyword patterns used to retrieve candidate issues per oracle class.

Two kinds of pattern:
  * single: one regex; a match anywhere in the searched text counts;
  * pair: a feature regex and a symptom regex that must both match within
    ``PAIR_WINDOW`` characters of each other (feature ... symptom or the
    reverse), which keeps broad feature words ("completion", "format") from
    retrieving every issue that merely mentions the feature.

Label rules retrieve on issue labels alone (tracker-specific area labels).
All regexes are applied case-insensitively to lower-cased text. The searched
text is: title, cleaned body, and the subjects of backfilled fix commits
(pyright, gopls); the source of every hit is recorded as title/body/fix/label.

Run line: imported by mine_candidates.py, not run directly.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Pattern, Sequence, Tuple

PAIR_WINDOW = 220


@dataclass(frozen=True)
class KeywordPattern:
    """A named retrieval pattern for one oracle class."""

    pid: str
    oracle: str
    regex: Pattern[str]
    symptom: Optional[Pattern[str]] = None


def _c(expr: str) -> Pattern[str]:
    return re.compile(expr, re.I)


_NEG = r"(does ?n[o']?t|do ?n[o']?t|did ?n[o']?t|is ?n[o']?t|are ?n[o']?t|was ?n[o']?t|not|never|won'?t|fails? to|failed to|no longer)"

SINGLE: List[Tuple[str, str, str]] = [
    # R1 history independence
    ("R1", "r1.stale", r"\bstale\b|\boutdated\b|\bout[- ]of[- ]date\b|\bout[- ]of[- ]sync\b|\bdesync\w*|\bde-?synchroni[sz]\w*|\bnot in sync\b"),
    ("R1", "r1.not_refreshed", _NEG + r"\s+(get\s+|be\s+|being\s+)?(updat|refresh|re-?evaluat|re-?analy[sz]|recomput|re-?comput|reload|re-?check|re-?validat|invalidat|clear|pick(ed)? up|re-?index|reflect)\w*"),
    ("R1", "r1.restart", r"\b(restart|re-?start|reload|re-?open|re-?launch)\w*\b|\bclos(e|ing) and (re-?)?open\w*"),
    ("R1", "r1.undo", r"\bundo(ing|ne)?\b|\bctrl\s*\+?\s*z\b|\brevert(ing|ed)?\s+(the\s+|my\s+|a\s+)?(change|edit|modification)"),
    ("R1", "r1.persist", r"\b(errors?|diagnostics?|warnings?|squiggl\w*|highlight\w*|hints?|problems?)\s+(still\s+)?(persist|remain|stay|stick|linger)\w*|\bstill\s+(shows?|showing|shown|reported|reports?|reporting|present|there|appears?|displayed|flagged|underlined|highlighted|marked)\b|\bghost\b|\bphantom\b|\bleftover\b|\blingering\b"),
    ("R1", "r1.lsp_notif", r"\bdid_?(change|close|open|save|changewatchedfiles|changeconfiguration|changeworkspacefolders|renamefiles|createfiles|deletefiles)\b|\bfile ?watch\w*|\bwatched ?files?\b"),
    ("R1", "r1.file_ops", r"\b(creat|delet|remov|renam|mov)(e|es|ed|ing)\s+(a\s+|the\s+|an\s+|new\s+|another\s+|some\s+)*(file|files|module|modules|package|packages|crate|crates|directory|directories|folder|folders|stub|stubs)\b|\b(file|files|module|package|crate|directory|folder)s?\s+(is\s+|are\s+|was\s+|were\s+|gets?\s+|got\s+)?(created|deleted|removed|renamed|moved)\b|\bnew(ly)? (created|added) (file|module|package|crate)"),
    ("R1", "r1.config_change", r"\b(chang|updat|edit|modif|toggl|switch)(e|es|ed|ing)\s+(the\s+|my\s+|a\s+|any\s+)?(config|configuration|settings?|pyrightconfig|pyproject|tsconfig|jsconfig|cargo\.toml|go\.mod|go\.work|go\.sum|build ?tags?|build ?flags|features|interpreter|python ?path|venv|workspace ?folders?)\b|\b(pyrightconfig\.json|pyproject\.toml|tsconfig(\.json)?|jsconfig(\.json)?|cargo\.toml|go\.mod|go\.work)\s+(file\s+)?(is\s+|are\s+|was\s+|gets?\s+)?(chang|updat|edit|modif)\w*|didchangeconfiguration|didchangeworkspacefolders"),
    ("R1", "r1.after_edit", r"\b(after|once|whenever)\s+(i\s+|you\s+|the user\s+|we\s+)?(then\s+)?(edit|type|typing|chang|delet|remov|renam|clos|sav|paste|modif|insert|comment|uncomment)\w*\b"),
    ("R1", "r1.cache", r"\bcache[sd]?\b|\bcaching\b|\binvalidat\w*"),
    ("R1", "r1.incremental", r"\bincremental\w*|\bsynchroni[sz]\w*|\btext ?document ?sync\w*|\bcontent ?changes\b|\bdocument versions?\b"),
    ("R1", "r1.goes_away", r"\b(goes away|go away|disappears?|disappeared|vanish\w*|fixe[sd] itself|resolves? itself)\b.{0,60}\b(restart\w*|reload\w*|reopen\w*|re-open\w*|clos\w*|sav\w*|touch\w*|retyp\w*|re-typ\w*|refresh\w*)"),
    ("R1", "r1.order_dependent", r"\border[- ]dependen\w*|\bevaluation order\b|\border of (evaluation|analysis|checking)\b|\bdepend\w* on (the )?(evaluation |analysis |checking )?order\b|\bnon-?deterministic\w*|\binconsistent(ly)?\s+(results?|behaviou?r|errors?|diagnostics?|types?)\b"),
    ("R1", "r1.mode_switch", r"\b(switch|toggl|chang)\w*\s+(\w+\s+){0,3}modes?\b|\bdiagnostic ?mode\b|\bopenfilesonly\b|\bworkspace mode\b"),
    ("R1", "r1.flaky", r"\bflicker\w*|\bintermittent\w*|\brandom(ly)?\b|\bsometimes\b|\brace condition\w*|\bnon-?deterministic\w*|\bflaky\b"),
    # R2 handle validity
    ("R2", "r2.resolve", r"(completion ?item|code ?action|inlay ?hint|code ?lens|document ?link|workspace ?symbol)s?\s*/\s*resolve|\bresolve ?(provider|request|support|method)\b|\bresolv(e|ing|ed)\s+(the\s+|a\s+|an\s+)?(completion|code ?action|quick ?fix|inlay|item|hint|lens)|\blazy (resolv|comput)\w*"),
    ("R2", "r2.semtok_delta", r"semantic ?tokens?\b.{0,60}\b(delta|edits?|result ?id)\b|\b(delta|full/delta)\b.{0,60}semantic"),
    ("R2", "r2.result_id", r"\b(previous)?result_?id\b"),
    ("R2", "r2.content_modified", r"content ?modified|-32801|\brequest (was )?cancel+ed\b|\b(document|file|content|text) (has |had )?(been )?changed (since|before|in the meantime|meanwhile)"),
    ("R2", "r2.stale_handle", r"\b(code ?actions?|quick ?fix(es)?|completions?|completion items?|inlay hints?|code ?lens(es)?)\b.{0,80}\b(stale|outdated|old|previous|earlier)\s+(version|position|range|offset|document|content|text|state|snapshot)"),
    ("R2", "r2.out_of_range", r"\bout of (range|bounds)\b|\boutofrange\b|\bbeyond (the )?end\b|\binvalid (position|range|offset|line|location|span)\b|\bbad (position|offset|range)\b|\b(position|offset)\b.{0,30}\b(exceeds|past the end|beyond)\b"),
    # R3 route equivalence
    ("R3", "r3.pull_push", r"\bpull (model|mode|diagnostics?)\b|textdocument/diagnostic|workspace/diagnostic|diagnostic ?provider|\bpush (model|mode|diagnostics?)\b|\bpublish ?diagnostics\b"),
    ("R3", "r3.semtok_range", r"semantic ?tokens?\s*/\s*range|\brange\b.{0,40}\bsemantic ?tokens?|semantic ?tokens?\b.{0,40}\brange\b"),
    ("R3", "r3.highlight_refs", r"document ?highlights?|\bhighlight(s|ed|ing)?\s+(of\s+)?(all\s+)?(references|occurrences|usages|related)\b|\boccurrences?\b.{0,60}\bhighlight\w*|\bhighlight\w*.{0,60}\boccurrences?\b"),
    ("R3", "r3.hover_vs_other", r"\b(reveal_type|hover)\b.{0,80}\b(inconsisten\w*|differ\w*|mismatch\w*|disagree\w*)\b"),
    # R4 edit validity (single)
    ("R4", "r4.organize_imports", r"\bimports? organi[sz]ation\b|\borgani[sz]ing imports\b|\bfix(ing)? imports\b|\borgani[sz]e ?imports?\b|\bsort ?imports?\b|\bremove unused imports?\b|\bgoimports\b|\bimport (sorting|ordering|grouping)\b|\bsource\.organizeimports\b"),
    ("R4", "r4.analyzer_fix", r"\b(analysis|analyzers?|modernize|modernizers?|simplif\w+|fillstruct|fillreturns|stubmethods|unusedparams|unusedvariable|infertypeargs|nonewvars|noresultvalues|undeclaredname)\b[:/ ].{0,120}\b(fix(es)?|suggest\w*|rewrit\w*|transform\w*|offers?|produc\w*|generat\w*|invalid|incorrect|wrong|bug|breaks?|broken)\b"),
    ("R4", "r4.idempotent", r"\bidempot\w*|\bnot stable\b.{0,40}\bformat|\bformat\w*.{0,60}\b(each|every) time\b"),
    # R5 semantics-preserving transformations
    ("R5", "r5.blank_lines", r"\b(blank|empty|extra|additional)\s+lines?\b|\bnewlines?\b|\bline ?breaks?\b"),
    ("R5", "r5.comments", r"\b(add|adding|added|insert|inserting|inserted|preceding|leading|trailing|line|block)\s+comments?\b|\bcomments?\s+(above|before|after|between|preceding|at the (top|start|beginning|end))\b|\bdocstrings?\b|\bdoc ?comments?\b"),
    ("R5", "r5.whitespace", r"\btrailing (white)?spaces?\b|\bwhitespace\b|\btab (character|stop|width|size)s?\b|\btabs\b|\bspaces vs\.? tabs\b"),
    ("R5", "r5.encoding", r"\bcrlf\b|\\r\\n|\bline ?endings?\b|\bcarriage returns?\b|\butf-?(8|16|32)\b|\bunicode\b|\bemojis?\b|\bnon-?ascii\b|\bmulti-?byte\b|\bsurrogate\w*|\bwide char\w*|\bcjk\b|\bchinese\b|\bjapanese\b|\bkorean\b|\bcyrillic\b|\bbyte order mark\b|\bposition ?encoding\b|\bcode ?units?\b|\butf16\b|\bgrapheme\w*"),
    ("R5", "r5.offset", r"\boff[- ]by[- ](one|1)\b|\b(wrong|incorrect|shifted|misplaced|misaligned)\s+(position|range|line|column|location|span|offset|start|end|place)s?\b|\b(position|range|column|offset|span|location|line number)s?\s+(is|are|was|were|seems?|appears?)\s+(wrong|off|incorrect|shifted|misaligned)\b|\bpoints? to (the )?wrong\b|\bhighlight\w* (the )?wrong\b"),
    ("R5", "r5.file_edge", r"\b(first|last) line\b|\b(end|beginning|start|top|bottom) of (the )?(file|document|buffer)\b|\beof\b|\bno (trailing )?newline\b|\bwithout (a )?(trailing )?newline\b|\bempty file\b"),
]

_QF_FEATURE = r"\b(quick ?fix(es)?|quickfix|code ?actions?|codeaction|suggested ?fix(es)?|auto-?fix\w*|assists?|fill ?struct|fillstruct|fill (switch|returns?)|implement (interface|missing|methods|members)|add missing \w+|modernize\w*|stubmethods|infer (return )?type|add (# ?)?type: ?ignore|remove unused \w+|unused (import|variable|parameter)s?|add (explicit )?(type|return)\w*|\bfix(es)? (is |was )?(applied|offered|suggested))\b"
_QF_SYMPTOM = r"\b((invalid|incorrect|wrong|bad|broken|buggy|unsafe) (fix|fixes|suggestions?|suggested fix|rewrites?|transformations?|replacements?|edits?)|results? in (an? )?(error|compile error|compilation error|build error|type error)|causes? (an? )?(error|compile error|build failure)|fails? to (compile|build)|bug in (the )?[\w.]+ (transformation|fix|rewrite|modernizer)|not equivalent|syntax errors?|parse errors?|invalid (code|syntax|go|rust|python|typescript|javascript|program|source)|(does|did) ?n[o']?t (compile|build|parse)|won'?t compile|non-?compil\w*|no longer compiles?|compil(e|ation|er) (error|fail)\w*|type errors?|broken|breaks?|broke|produc\w* (invalid|incorrect|wrong|broken|bad|erroneous)|generat\w* (invalid|incorrect|wrong|broken|bad)|introduc\w* (an? |new )?(error|bug|problem|compile)\w*|remov\w* (the |a |needed|necessary|used|required|code|comments?|all)|delet\w* (the |a |needed|necessary|used|required|code|comments?|all)|dropped|duplicat\w*|twice|doubled|extra (paren\w*|brace|bracket|semicolon|comma|newline|space|import|char\w*|text|lines?)|missing (paren\w*|brace|bracket|semicolon|comma|newline|imports?)|unbalanced|mangl\w*|corrupt\w*|garbl\w*|clobber\w*|overwrit\w*|wrong (position|place|location|range|offset|indentation|file|line)|does ?n[o']?t (fix|remove|resolve|clear)|still (reports?|shows?|there|present)|new (error|diagnostic|warning)s?|another (error|diagnostic)|incorrect (edits?|code|fix|insert\w*)|invalid edits?|bad edits?)\b"
_FMT_FEATURE = r"\b(on-?type|semicolon insertion|auto-?(insert\w*|clos\w*)|typing (a |an |the )?\S{1,3} (inserts?|adds?)|format(ting|ter|s|ted)?|gofmt|gofumpt|rustfmt|prettier|on ?type ?formatting|range ?formatting|indent(ation|ing|s)?|re-?indent\w*)\b"
_FMT_SYMPTOM = r"\b(idempot\w*|twice|each time|every time|repeated\w*|again and again|keeps? (adding|removing|indenting|inserting|moving|growing|increasing|shifting)|more and more|accumulat\w*|remov(es|ed|ing)|delet(es|ed|ing)|eats?|eating|swallow\w*|lost|loses?|dropped|chang\w* (the )?(code|semantics?|meaning|behaviou?r|program)|breaks?|broken|broke|syntax errors?|invalid|corrupt\w*|duplicat\w*|insert\w* (an? )?(extra|additional|spurious|unexpected)|comments? (is |are |get |gets )?(moved|removed|deleted|lost|misplaced)|non-?whitespace)\b"
_COMP_FEATURE = r"\b(completions?|complet(e|ing|ed)\b|auto-?complet\w*|suggestions?|snippets?|intellisense|text ?edits?|insert ?text|additional ?text ?edits?|postfix)\b"
_COMP_SYMPTOM = r"\b(broken|breaks?|broke|invalid|completes? (to|as|into) [\"'`&*(\w]|results? in|insert\w* .{0,40}(wrong|extra|twice|duplicate|incorrect|invalid|unexpected)|replac\w* .{0,40}(wrong|too much|too little|the rest|following|next|previous|incorrect|extra|entire|whole)|overwrit\w*|duplicat\w*|doubl(e|ed|es|ing)\b|twice|extra (paren\w*|brace|bracket|dot|char\w*|colon|comma|quote|space|text|angle|semicolon)|missing (paren\w*|brace|bracket|dot|colon|comma|quote|semicolon)|syntax errors?|invalid (code|syntax)|eats?|eating|swallow\w*|clobber\w*|wrong (range|position|text|insert\w*|place|edits?)|incorrect (range|position|text|insert\w*|edits?)|unexpected (text|character|token)|compile errors?|(does|did) ?n[o']?t compile|replace ?range|insert ?range|leftover|left over|garbage|removes? (the |existing )?(text|code|character|word))\b"
_AUTOIMP_FEATURE = r"\b(auto-?imports?|add(ed|s|ing)? (an? |the )?(missing )?imports?|imports? (is |are |was |were |gets? )?(added|inserted|generated)|import (suggestion|completion|fix|code ?action|quick ?fix)s?|missing imports?)\b"
_AUTOIMP_SYMPTOM = r"\b(wrong|incorrect|invalid|duplicat\w*|twice|breaks?|broken|syntax|position|place|relative|unresolved|cannot (find|resolve)|not (found|resolved)|circular|self-?import|itself)\b"
_NAV_FEATURE = r"\b(go ?to ?definition|goto ?definition|go-to-definition|jump to definition|find (all )?references|references|document ?highlight|type ?definition|go ?to ?implementation|implementations?|call hierarchy|hover)\b"
_NAV_SYMPTOM = r"\b(inconsisten\w*|differ\w*|mismatch\w*|disagree\w*|only (works|when|from|on|for|if)|works (on|for|from|in|with|when)\b.{0,60}\bbut|but not\b|from (the )?(declaration|definition|usage|call ?site|import|other)|some (references|usages|occurrences)|missing (some |the )?(references|occurrences|usages|results)|incomplete|partial (results|list))\b"
_ERRPOS_FEATURE = r"\b(diagnostics?|errors?|warnings?|squiggl\w*|hover|definition|highlight\w*|semantic tokens?|inlay hints?|code ?lens)\b"
_ERRPOS_SYMPTOM = r"\b(after|below|above|following) (a |an |the )?(comment|blank line|empty line|docstring|newline|multi-?line)\b"

PAIRS: List[Tuple[str, str, str, str]] = [
    ("R4", "r4.quickfix_breaks", _QF_FEATURE, _QF_SYMPTOM),
    ("R4", "r4.format_changes", _FMT_FEATURE, _FMT_SYMPTOM),
    ("R4", "r4.completion_insert", _COMP_FEATURE, _COMP_SYMPTOM),
    ("R4", "r4.autoimport_wrong", _AUTOIMP_FEATURE, _AUTOIMP_SYMPTOM),
    ("R3", "r3.nav_inconsistent", _NAV_FEATURE, _NAV_SYMPTOM),
    ("R5", "r5.layout_dependent", _ERRPOS_FEATURE, _ERRPOS_SYMPTOM),
]

LABEL_RULES: Dict[str, List[Tuple[str, str]]] = {
    "tsserver": [
        ("Domain: LS: Quick Fixes", "R4"), ("Domain: Formatter", "R4"),
        ("Domain: LS: Auto-import", "R4"), ("Domain: LS: Organize Imports", "R4"),
        ("Domain: LS: TSServer", "R1"), ("Domain: LS: Symbol Navigation", "R3"),
    ],
    "rust-analyzer": [
        ("A-vfs", "R1"), ("A-salsa", "R1"), ("A-flycheck", "R1"), ("A-config", "R1"),
        ("A-project-model", "R1"), ("A-lsp", "R1"), ("A-highlighting", "R3"),
        ("A-assists", "R4"), ("A-diagnostics", "R4"),
    ],
    "gopls": [
        ("gopls/incremental", "R1"), ("gopls/metadata", "R1"), ("gopls/workspace", "R1"),
        ("gopls/imports", "R4"), ("gopls/file-corruption", "R4"), ("gopls/analysis", "R4"),
    ],
    "pyright": [],
}

# Revisions made after recall audit 1 (see recall_audit.py); the regexes above
# are the round-2 versions.
ROUND2_CHANGES: Dict[str, str] = {
    "r4.organize_imports": "added 'import(s) organization', 'organizing imports', 'fix(ing) imports'",
    "r4.quickfix_breaks": "symptoms added: invalid/incorrect/wrong/bad/broken fix, suggestion, rewrite, transformation or edit; "
                          "'results in an error', 'causes an error', 'fails to compile', 'bug in <x> transformation', 'not equivalent'",
    "r4.completion_insert": "symptoms added: broken, breaks, invalid, 'completes to <text>', 'results in'",
    "r4.format_changes": "features added: on-type, semicolon insertion, auto-insert/auto-close, 'typing <c> inserts/adds'",
    "r4.analyzer_fix": "new: an analyzer, modernizer or gopls fixer name followed within 120 characters by fix, suggest, "
                       "rewrite, transform, offers, produces, generates, invalid, incorrect, wrong, bug or broken",
}

ALL_PATTERNS: List[KeywordPattern] = [
    KeywordPattern(pid=pid, oracle=o, regex=_c(rx)) for o, pid, rx in SINGLE
] + [KeywordPattern(pid=pid, oracle=o, regex=_c(f), symptom=_c(s)) for o, pid, f, s in PAIRS]


def _pair_hit(pat: KeywordPattern, text: str) -> Optional[str]:
    assert pat.symptom is not None
    for m in pat.regex.finditer(text):
        lo = max(0, m.start() - PAIR_WINDOW)
        hi = min(len(text), m.end() + PAIR_WINDOW)
        s = pat.symptom.search(text, lo, hi)
        if s is not None:
            a, b = min(m.start(), s.start()), max(m.end(), s.end())
            return text[a:b]
    return None


def match_text(sources: Sequence[Tuple[str, str]]) -> List[Tuple[str, str, str, str]]:
    """Return (oracle, pattern_id, source, matched_snippet) for every pattern hit."""
    hits: List[Tuple[str, str, str, str]] = []
    for pat in ALL_PATTERNS:
        for src, text in sources:
            if not text:
                continue
            if pat.symptom is None:
                m = pat.regex.search(text)
                snippet = m.group(0) if m else None
            else:
                snippet = _pair_hit(pat, text)
            if snippet is not None:
                hits.append((pat.oracle, pat.pid, src, " ".join(snippet.split())[:80]))
                break
    return hits


def match_labels(server: str, labels: Sequence[str]) -> List[Tuple[str, str, str, str]]:
    """Return label-rule hits as (oracle, pattern_id, 'label', label)."""
    wanted = dict(LABEL_RULES.get(server, []))
    return [(wanted[lab], "label:" + lab, "label", lab) for lab in labels if lab in wanted]

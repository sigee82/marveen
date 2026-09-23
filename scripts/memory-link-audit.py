#!/usr/bin/env python3
"""Audit [[wikilink]] references in the agent memory directory.

A naive "file does not exist -> broken" check conflates three different things,
and only one of them is a defect:

  MEMORY        the link resolves to a memory file (by filename or by its
                frontmatter `name:` field -- both forms are used in practice)
  MEMORY-SZEKCIO  the link resolves to a `## <slug>` section heading inside a
                topic collector. Consolidation merges a memory file into a
                collector and KEEPS its original slug as the heading, exactly
                so existing links keep resolving -- so this is a hit, not a
                defect. Measured 2026-09-15: 688 of 911 "unresolved" targets
                were of this kind, and the count grows with every
                consolidation round, not with any breakage.
  SKILL / TASK  a valid cross-namespace reference to ~/.claude/skills/<n> or
                ~/.claude/scheduled-tasks/<n>. NOT broken. Existence is
                CHECKED here, never assumed from a hand-maintained list.
  ARTIFACT      prose that merely looks like a wikilink: POSIX character
                classes ([[:space:]]), placeholders ([[link]]), phrases.
  UNRESOLVED    none of the above -- the real repair queue.

COMPARING TWO RUNS: use the NAME SETS, not the counts. The vault is written while
this script runs -- saving a memory mid-session adds files and links -- so two
CORRECT runs minutes apart legitimately differ in their totals. Measured
2026-09-16: two runs 20 minutes apart differed by one memory and two link
occurrences purely because three new memories had been written in between, and for
a moment that looked like a regression in a refactor. If you need to compare code
versions, run BOTH against the same snapshot (git show <sha>:<file>) rather than
against a number written down earlier.

A heading match tolerates hyphen/underscore drift (`a-b` vs `a_b`), which is
pure spelling, but NEVER strips the type prefix: `feedback_x` and
`reference_x` are different memories, so a prefix-blind match could resolve a
link to the wrong one. Prefix-only candidates go to their own SZEKCIO-PREFIX?
bucket for a human to look at -- not silently resolved, not dumped into the
repair queue.

Also reports name/filename drift, because a rename has to keep the filename,
the `name:` field and every [[link]] in sync; if they drift, the mixed-form
links that exist today get regenerated.

Usage: python3 scripts/memory-link-audit.py [memory_dir]

Findings never change the exit code -- this is a report, not a gate. An
unreadable or missing directory DOES fail loudly, on purpose: a silent empty
report reads as "all clean", which is the one failure this tool must not have.
"""
import os
import re
import sys

# Derive the project slug from this file's own location rather than hardcoding
# it: a wrong path here would fail silently -- an empty report reads as "all
# clean". The slug replaces both "/" and "." with "-", so a hidden directory
# yields a double dash, matching how the config tree names projects.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SLUG = _ROOT.replace("/", "-").replace(".", "-")
# The memory vault lives under ~/.claude, NOT under the project tree. An earlier
# version pointed at <project>/.channels-config/... -- a directory that does not
# exist on this machine, so the script crashed with FileNotFoundError whenever it
# ran without an explicit argument (measured 2026-09-11, reported by signal).
# Both candidates are listed so a future move is a one-line change, and the
# chosen one is the first that actually exists: a silently wrong base is the
# failure mode this file's own comment warns about.
_CANDIDATES = [
    os.path.join(os.path.expanduser("~/.claude"), "projects", _SLUG, "memory"),
    os.path.join(_ROOT, ".channels-config", "projects", _SLUG, "memory"),
]
DEFAULT_DIR = next((c for c in _CANDIDATES if os.path.isdir(c)), _CANDIDATES[0])
SKILL_DIRS = [
    os.path.expanduser("~/.claude/skills"),
    os.path.expanduser("~/.claude/scheduled-tasks"),
]

WIKILINK = re.compile(r"\[\[([^\]]+)\]\]")
# Inline code spans. NOT allowed to cross a newline: a single stray backtick
# would otherwise swallow the rest of the file and silently empty the repair
# queue -- the failure mode would look like "nothing to fix".
CODE_SPAN = re.compile(r"`[^`\n]*`")
NAME_FIELD = re.compile(r"^name:\s*(.*?)\s*$", re.MULTILINE)
SECTION = re.compile(r"^#{2,}\s+(\S+)\s*$", re.MULTILINE)
TYPE_PREFIXES = ("feedback_", "reference_", "project_", "topic_")


def spelling(target):
    """Hyphen/underscore drift is spelling, not identity."""
    return target.replace("-", "_").lower()


def without_type_prefix(target):
    t = spelling(target)
    for prefix in TYPE_PREFIXES:
        if t.startswith(prefix):
            return t[len(prefix):]
    return t


def is_artifact(target, in_code):
    """Prose that only looks like a link. Deliberately conservative: anything
    matching here is dropped from the repair queue, so keep it narrow.

    THE POSIX BRANCH IS BACK, AND THIS PARAGRAPH IS THE REASON -- read it before
    removing it again (merge with upstream, 2026-09-23).

    It was removed here under "one branch for one class": the POSIX test (target
    starts or ends with ":", for [[:space:]]) looked like a second mechanism next
    to the code-span rule, and the vault's only [[:space:]] sat inside backticks,
    so the bucket counts were identical without it. That measurement was correct
    and it is still correct. It just answers a question about THE VAULT'S CURRENT
    CONTENTS, not about the rule: "a case the vault does not have" is a fact that
    any future memory can falsify, and nothing would announce it.

    Two things decided it the other way:
      1. The two are not one question in two mechanisms. `[[:space:]]` and a
         backtick span are different SYNTAXES; the code-span rule asks "is this
         quoted?", the POSIX rule asks "is this a character class?". A POSIX class
         is not a memory slug under any spelling, quoted or not.
      2. The stated consequence is worse than it reads. UNRESOLVED is the repair
         queue, so the tool would be asking the author to add backticks to PROSE
         to satisfy the linter -- the same "checker that teaches its own override"
         shape that code_spans() below exists to remove.

    Upstream's scripts/__tests__/memory-link-audit.test.py pins the restored
    behaviour, so this is no longer a preference either way: removing the branch
    now turns that suite red.

    AND THE SAME ANSWER FOR THE "!" MARKER, so nobody re-adds a branch for it: the
    vault marks some example links with a leading "!" (a convention from
    2026-08-18). It needs NO branch here -- both "!nev" occurrences sit inside
    backticks, so this rule already covers them. The marker still appears in two
    places in the vault; it is harmless, but it is NOT the mechanism. If you are
    reading this while about to special-case "!", that is the branch this docstring
    exists to prevent."""
    if in_code:
        return True  # an example of the syntax, not a use of it
    if target.startswith(":") or target.endswith(":"):
        return True  # POSIX character class, e.g. [[:space:]] -- see the docstring
    if " " in target:
        return True  # phrases are never memory slugs
    return target in {"link", "name", "their-name"}


def code_spans(body):
    """Character ranges covered by inline `code`.

    WHY THIS EXISTS: three of the nine entries in the repair queue were never
    links -- a regex example and two pieces of documentation that happen to
    contain [[...]] inside backticks. They can never be "fixed", so the queue
    permanently held three items everyone had to remember were expected. That is
    the false-alarm shape: a checker that teaches its own override.

    Measured on the whole vault before writing this (2026-09-16): 2193 [[...]]
    occurrences, of which exactly 4 sit inside a backtick span -- and those 4 are
    precisely the three false positives. No resolving link is inside backticks,
    and the three have zero occurrences outside them. One rule, no side effects.

    LIMIT, stated: only INLINE spans. A [[link]] inside a fenced ``` block is not
    covered, because the vault has none and a fence rule would need multi-line
    state. If one ever appears, it lands in UNRESOLVED -- loudly, not silently.
    """
    return [m.span() for m in CODE_SPAN.finditer(body)]


def in_code_span(pos, spans):
    return any(a <= pos < b for a, b in spans)


def is_index_file(fname):
    """Index files carry the loaded-at-startup pointer list, not a memory. They
    have no frontmatter by design, so the name/filename drift check must skip
    them -- otherwise every index shows up as "name: (hianyzik)" forever.

    This used to be a single hardcoded `fname == "MEMORY.md"`. When the index
    was split in two (MEMORY.md + MEMORY-korabbi.md, because the loader
    truncates around 24 KB), the second file was not covered, and the audit
    reported a permanent drift of 1 -- measured 2026-09-11, reported by signal.
    A rule written for one name does not protect its siblings, so match the
    FAMILY, not the instance.
    """
    return fname == "MEMORY.md" or fname.startswith("MEMORY-")


def load(memory_dir):
    """Return (stems, name-field -> stem, section anchors, drift, skipped).

    `sections` maps a consolidated slug to the collector that now holds it,
    under two keys: the spelling-normalised slug, and the same with the type
    prefix removed. The two are kept apart so the caller can resolve the first
    and merely FLAG the second -- see the module docstring.

    The whole file is read for headings (not just the 2 KB frontmatter window)
    because a collector holds dozens of merged slugs throughout its body.

    The skipped list is returned so the report can NAME what it dropped. A
    silent exclusion is the same defect class it was written to fix: a real
    memory whose filename happened to start with "MEMORY-" would vanish from
    `stems`, and every [[link]] to it would then surface as UNRESOLVED -- a
    swallowed file masquerading as a broken link. Anything nothing points at
    would disappear without a trace.
    """
    stems, by_name, drift, skipped = set(), {}, [], []
    exact, prefixless = {}, {}
    for fname in sorted(os.listdir(memory_dir)):
        if not fname.endswith(".md"):
            continue
        if is_index_file(fname):
            skipped.append(fname)
            continue
        stem = fname[:-3]
        stems.add(stem)
        with open(os.path.join(memory_dir, fname), encoding="utf-8") as fh:
            text = fh.read()
        m = NAME_FIELD.search(text[:2048])
        declared = m.group(1).strip().strip('"').strip("'") if m else ""
        if declared:
            by_name.setdefault(declared, stem)
        if declared != stem:
            drift.append((fname, declared or "(hianyzik)"))
        for heading in SECTION.findall(text):
            exact.setdefault(spelling(heading), fname)
            prefixless.setdefault(without_type_prefix(heading), fname)
    return stems, by_name, (exact, prefixless), drift, skipped


def main():
    memory_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DIR
    stems, by_name, (sections, sections_prefixless), drift, skipped = load(memory_dir)

    skills = set()
    for root in SKILL_DIRS:
        if os.path.isdir(root):
            skills |= {d for d in os.listdir(root)
                       if os.path.isdir(os.path.join(root, d))}

    buckets = {k: {} for k in
               ("MEMORY", "MEMORY-NEV", "MEMORY-SZEKCIO", "SKILL/TASK",
                "ARTIFACT", "SZEKCIO-PREFIX?", "UNRESOLVED")}
    for fname in sorted(os.listdir(memory_dir)):
        if not fname.endswith(".md"):
            continue
        with open(os.path.join(memory_dir, fname), encoding="utf-8") as fh:
            body = fh.read()
        spans = code_spans(body)
        for m in WIKILINK.finditer(body):
            t = m.group(1).strip()
            if is_artifact(t, in_code_span(m.start(), spans)):
                cls = "ARTIFACT"
            elif t in stems:
                cls = "MEMORY"
            elif t.endswith(".md") and t[:-3] in stems:
                cls = "UNRESOLVED"  # .md suffix inside a wikilink is a defect
            elif t in by_name:
                cls = "MEMORY-NEV"
            elif spelling(t) in sections:
                cls = "MEMORY-SZEKCIO"
            elif t in skills:
                cls = "SKILL/TASK"
            elif without_type_prefix(t) in sections_prefixless:
                cls = "SZEKCIO-PREFIX?"
            else:
                cls = "UNRESOLVED"
            buckets[cls].setdefault(t, []).append(fname)

    print(f"INDEX-FAJLKENT KIHAGYVA: {len(skipped)} -> {', '.join(skipped) if skipped else '(egy sem)'}")
    print(f"memoria-fajlok: {len(stems)}   skill/task nevek: {len(skills)}")
    for cls in ("MEMORY", "MEMORY-NEV", "MEMORY-SZEKCIO", "SKILL/TASK",
                "ARTIFACT", "SZEKCIO-PREFIX?", "UNRESOLVED"):
        hits = buckets[cls]
        total = sum(len(v) for v in hits.values())
        print(f"\n{cls}: {len(hits)} egyedi / {total} elofordulas")
        if cls in ("MEMORY", "MEMORY-SZEKCIO", "ARTIFACT"):
            continue
        for target in sorted(hits):
            where = ", ".join(sorted(set(hits[target]))[:3])
            print(f"  {target}  <- {where}")

    print(f"\nNEV/FAJLNEV ELTERES: {len(drift)}")
    for fname, declared in drift:
        print(f"  {fname}  name: {declared}")
    print("\nJAVITANDO = az UNRESOLVED csoport. A SKILL/TASK ervenyes "
          "kereszthivatkozas, az ARTIFACT proza, a MEMORY-SZEKCIO pedig "
          "beolvasztott emlek, ami szekciofejleckent a helyen van.")
    print("A SZEKCIO-PREFIX? csoport EMBERI dontest kivan: a cel csak a tipus"
          "-prefix elhagyasaval talal szekciot, es a prefix jelentest hordoz.")


if __name__ == "__main__":
    main()

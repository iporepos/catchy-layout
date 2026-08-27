#!/usr/bin/env python3
# =========================================================================
# transform_manuscript.py -- convert a manuscript chapter into a book chapter
# -------------------------------------------------------------------------
# v1: DEFAULTS ONLY. No JSON sidecar yet -- every figure and every boxmain
# is written out with explicit [L][t] (full two-column width, top of page)
# so the values are visible in the output file and can be hand-edited
# afterwards. A later version can read a per-figure/per-box JSON sidecar
# to fill in S/M and t/b instead of always L/t.
#
# Usage:
#   python transform_manuscript.py chapter01_v202601_manuscript.tex
#   python transform_manuscript.py chapter00_v202601_manuscript.tex -o chapter00.tex --preface
#
# Preface (chapter 0) is auto-detected from "\setcounter{chapter}{-1}" in
# the manuscript's mockup preamble; override with --preface / --no-preface.
#
# What it does:
#   - Drops the manuscript-only wrapper: \documentclass, \input{config},
#     \setcounter{chapter}{...}, \boxcolor, \begin{document} ... \end{document}.
#   - \chapter{Title}                  -> \startchapter{Title}
#                                          (\startchapterstar{Title} if preface)
#   - \openingimage{label}{caption} +
#     \inthischapter{spoiler}          -> \chaptercover{label}{caption}{spoiler}
#                                          (omitted entirely for the preface)
#   - \begin{boxskills}...\end{boxskills} near the top is lifted out and
#     passed as the \chapterfirstpage{...} argument ({} for the preface, or
#     if no boxskills block is found)
#   - \figplaceholder{label}{name}{caption}
#                                       -> \figplaceholder[L][t]{label}{name}{caption}
#   - \begin{boxmain}[keys]{theme}{title}
#                                       -> \begin{boxmain}[L][t][keys]{theme}{title}
#   - \newpage immediately before \begin{boxmessages} or \section*{Homework...}
#                                       -> \chapterhardbreak
#   - Everything else (\boxfigplaceholder, \boxbiofigplaceholder, \boxbio,
#     \begin{workedexample}, tables, \Cref, \authornote, ...) is left as-is:
#     same command/environment names and signatures in config.tex.
# =========================================================================

import argparse
import re
import sys


# -------------------------------------------------------------------------
# Small balanced-group reader (handles nested braces/brackets, e.g. captions
# containing \textit{...} or math). Regex alone can't do this safely.
# -------------------------------------------------------------------------
def skip_ws(text, i):
    while i < len(text) and text[i] in " \t\r\n":
        i += 1
    return i


def read_group(text, i, open_ch, close_ch):
    """text[i] must be open_ch. Returns (inner_content, index_after_close)."""
    assert text[i] == open_ch, f"expected {open_ch!r} at {i}, got {text[i:i+20]!r}"
    depth = 1
    j = i + 1
    while depth > 0:
        if j >= len(text):
            raise ValueError(f"unbalanced {open_ch!r}{close_ch!r} starting at {i}")
        if text[j] == open_ch:
            depth += 1
        elif text[j] == close_ch:
            depth -= 1
        j += 1
    return text[i + 1:j - 1], j


def find_group_after(text, i, open_ch, close_ch):
    """Skip whitespace from i, then read a group. i must land on open_ch."""
    i = skip_ws(text, i)
    return read_group(text, i, open_ch, close_ch)


# -------------------------------------------------------------------------
# Generic "insert leading optional-arg defaults" for commands like
# \figplaceholder{a}{b}{c} -> \figplaceholder[L][t]{a}{b}{c}.
# Calls that already carry explicit [..] are left untouched (idempotent).
# -------------------------------------------------------------------------
def add_defaults_to_command(text, cmd, n_mandatory, defaults):
    pattern = re.compile(r"\\" + re.escape(cmd) + r"(?![A-Za-z])")
    out = []
    i = 0
    while True:
        m = pattern.search(text, i)
        if not m:
            out.append(text[i:])
            break
        out.append(text[i:m.start()])
        k = skip_ws(text, m.end())
        if k < len(text) and text[k] == "[":
            # Already has explicit optional args -- leave the call untouched.
            out.append(text[m.start():m.end()])
            i = m.end()
            continue
        pos = k
        args = []
        ok = True
        for _ in range(n_mandatory):
            pos = skip_ws(text, pos)
            if pos >= len(text) or text[pos] != "{":
                ok = False
                break
            content, pos = read_group(text, pos, "{", "}")
            args.append(content)
        if not ok:
            out.append(text[m.start():m.end()])
            i = m.end()
            continue
        braces = "".join("{%s}" % a for a in args)
        out.append("\\" + cmd + defaults + braces)
        i = pos
    return "".join(out)


# -------------------------------------------------------------------------
# \begin{boxmain}[keys]{theme}{title} -> \begin{boxmain}[L][t][keys]{theme}{title}
# (boxmain's own optional key group, e.g. [label=...], becomes the THIRD
# optional argument in the book version -- size and placement are new
# leading slots, see config.tex sec. 10.)
# -------------------------------------------------------------------------
def add_defaults_to_boxmain(text):
    pattern = re.compile(r"\\begin\{boxmain\}")
    out = []
    i = 0
    while True:
        m = pattern.search(text, i)
        if not m:
            out.append(text[i:])
            break
        out.append(text[i:m.start()])
        pos = m.end()
        keys = ""
        if pos < len(text) and text[pos] == "[":
            keys, pos = read_group(text, pos, "[", "]")
        theme, pos = find_group_after(text, pos, "{", "}")
        title, pos = find_group_after(text, pos, "{", "}")
        out.append("\\begin{boxmain}[L][t][%s]{%s}{%s}" % (keys, theme, title))
        i = pos
    return "".join(out)


# -------------------------------------------------------------------------
# Extract a single command's arguments and remove the whole call from the
# text. Returns (list_of_args_or_None, new_text). Only the FIRST match is
# used (openingimage/inthischapter/chapter each appear once per chapter).
# -------------------------------------------------------------------------
def extract_command(text, cmd, n_mandatory):
    pattern = re.compile(r"\\" + re.escape(cmd) + r"(?![A-Za-z])")
    m = pattern.search(text)
    if not m:
        return None, text
    pos = m.end()
    args = []
    for _ in range(n_mandatory):
        pos = skip_ws(text, pos)
        content, pos = read_group(text, pos, "{", "}")
        args.append(content)
    return args, text[:m.start()] + text[pos:]


def extract_boxskills(text):
    r"""Find \begin{boxskills}...\end{boxskills}, optionally preceded by a
    lone \newpage, and remove it. Returns (inner_content_or_None, new_text)."""
    pattern = re.compile(
        r"(?:\\newpage\s*\n?\s*)?\\begin\{boxskills\}(.*?)\\end\{boxskills\}",
        re.DOTALL,
    )
    m = pattern.search(text)
    if not m:
        return None, text
    return m.group(1).strip("\n"), text[:m.start()] + text[m.end():]


def strip_manuscript_wrapper(text):
    r"""Drop everything before \begin{document} and the trailing \end{document}."""
    m = re.search(r"\\begin\{document\}", text)
    if m:
        text = text[m.end():]
    text = re.sub(r"\\end\{document\}\s*\Z", "", text, flags=re.DOTALL)
    return text


def strip_first_thispagestyle(text):
    r"""Remove the first \thispagestyle{...} (and a lone preceding editorial
    comment line), as seen right after \chapter{...} in the manuscript."""
    # (kept simple: just drop the first thispagestyle line + one leading
    # comment-only line directly above it, if present)
    m = re.search(r"\\thispagestyle\{[^}]*\}\s*\n?", text)
    if not m:
        return text
    start = m.start()
    # look back for a single comment-only line immediately above
    before = text[:start]
    cm = re.search(r"[ \t]*%[^\n]*\n[ \t]*\Z", before)
    if cm:
        start = cm.start()
    return text[:start] + text[m.end():]


def convert_newpage_before(text, target_pattern):
    return re.sub(
        r"\\newpage(\s*\n(?:[ \t]*%[^\n]*\n)*\s*)(?=" + target_pattern + r")",
        r"\\chapterhardbreak\1",
        text,
    )


# -------------------------------------------------------------------------
# Main transform
# -------------------------------------------------------------------------
def transform(text, preface):
    text = strip_manuscript_wrapper(text)

    title_args, text = extract_command(text, "chapter", 1)
    if title_args is None:
        raise ValueError(r"no \chapter{...} found in manuscript file")
    title = title_args[0]

    text = strip_first_thispagestyle(text)

    cover_label = cover_caption = spoiler = None
    if not preface:
        img_args, text = extract_command(text, "openingimage", 2)
        if img_args is not None:
            cover_label, cover_caption = img_args
        spoiler_args, text = extract_command(text, "inthischapter", 1)
        if spoiler_args is not None:
            spoiler = spoiler_args[0]

    skills_content, text = extract_boxskills(text)
    if skills_content is None:
        skills_content = ""

    text = add_defaults_to_command(text, "figplaceholder", 3, "[L][t]")
    text = add_defaults_to_boxmain(text)

    text = convert_newpage_before(text, r"\\begin\{boxmessages\}")
    text = convert_newpage_before(text, r"\\section\*\{Homework")

    text = text.strip("\n") + "\n"

    header_lines = []
    if preface:
        header_lines.append(r"\startchapterstar{%s}" % title)
        # No \chaptercover for the preface (config.tex skips the skills box
        # below \bookfirstdecoratedchapter regardless), but \chapterfirstpage{}
        # is still required -- it prints the title/number row.
        header_lines.append(r"\chapterfirstpage{}")
    else:
        header_lines.append(r"\startchapter{%s}" % title)
        header_lines.append(
            r"% \chaptershortname{...}   %% optional: else falls back to full title"
        )
        if cover_label is not None and spoiler is not None:
            header_lines.append(
                r"\chaptercover{%s}{%s}{%s}" % (cover_label, cover_caption, spoiler)
            )
        header_lines.append(r"\chapterfirstpage{%s}" % skills_content)

    return "\n".join(header_lines) + "\n\n" + text


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("infile")
    ap.add_argument("-o", "--outfile", default=None)
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--preface", dest="preface", action="store_true", default=None)
    group.add_argument("--no-preface", dest="preface", action="store_false")
    args = ap.parse_args()

    with open(args.infile, "r", encoding="utf-8") as f:
        src = f.read()

    preface = args.preface
    if preface is None:
        preface = bool(re.search(r"\\setcounter\{chapter\}\{-1\}", src))

    out = transform(src, preface)

    if args.outfile:
        with open(args.outfile, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"wrote {args.outfile} (preface={preface})", file=sys.stderr)
    else:
        sys.stdout.write(out)


if __name__ == "__main__":
    main()
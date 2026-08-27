#!/usr/bin/env python3
# =========================================================================
# transform_manuscript.py -- convert a manuscript chapter into a book chapter
# -------------------------------------------------------------------------
# v2: figure SIZE (S/M/L) can now be looked up from a figure catalog JSON,
# via a "width" -> "size" mapping, instead of always defaulting to L.
# Everything else (box sizing, placement, captions/credits) is still a
# fixed default -- boxmain stays [L][t], every figure placement stays [t].
# Captions/credits from the catalog are not consumed yet.
#
# Two ways to run it:
#
#   (a) plain CLI, no catalog -- every figure defaults to L (old behaviour):
#         python transform_manuscript.py chapter01_v202601_manuscript.tex -o chapter01.tex
#
#   (b) master config JSON -- drives input/output/catalog/width-mapping in
#       one place, and looks up each figure's real size by its label:
#         python transform_manuscript.py --config config.json
#
#       config.json:
#       {
#         "input_file": "chapter01_v202601_manuscript.tex",
#         "output_file": "chapter01.tex",
#         "catalog_file": "catalog.json",
#         "width_mapping": {
#           "172 mm": "L",
#           "126 mm": "M",
#           "83.5 mm": "S"
#         }
#       }
#
#       catalog.json is a list of chapter entries, each optionally with a
#       "figures" list AND/OR a "boxes" list, both shaped the same way:
#       [{"metadata": {"label": ..., "width": ..., ...}}, ...]. Figures are
#       looked up by their own label (\figplaceholder's 1st argument);
#       boxes are looked up by the "label=..." key inside \boxmain's own
#       [...] (e.g. \begin{boxmain}[label=C01-box-gauges]{...}{...}).
#       Only "label" and "width" are read for now; caption/credits/etc. are
#       ignored (future work). If a catalog has no "boxes" list at all,
#       boxmain calls just default to L, same as if no catalog were given
#       (no per-box warnings) -- so you can catalog figures and boxes on
#       separate schedules without noisy output.
#
#       CLI flags (-o, --catalog, --preface/--no-preface, a positional
#       infile) always override the matching config.json value if given.
#
# Preserving hand-tuned positions across re-runs:
#   Once you've hand-edited a generated chapter's [size][t/b] tags in
#   Overleaf, re-running this script on an updated manuscript would
#   normally wipe those edits out. To avoid that: if the output file
#   ALREADY EXISTS, its current [size][t/b] values are read back (keyed by
#   figure label / the box's own "label=..." key) and written to a sidecar
#   "<output_file>_positions.json" BEFORE anything is overwritten. That
#   sidecar then wins over the catalog/defaults for every label it
#   contains; labels it doesn't know about (new figures/boxes from a
#   manuscript update, or no sidecar at all) just fall through to the
#   normal catalog/default resolution. So the day-to-day flow is:
#     1. run once to generate chapter01.tex
#     2. hand-tune sizes/placements directly in chapter01.tex in Overleaf
#     3. manuscript gets updated -> re-run with the same output_file
#        -> your edits are snapshotted and re-applied automatically;
#           only genuinely new figures/boxes fall back to defaults.
#   The sidecar is plain JSON, e.g. {"C01-mtx-titicaca": {"size": "S",
#   "placement": "b"}, ...} -- safe to inspect or hand-edit directly too.
#
# Preface (chapter 0) is auto-detected from "\setcounter{chapter}{-1}" in
# the manuscript's mockup preamble unless overridden by --preface/
# --no-preface or a "preface" key in config.json.
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
#                                       -> \figplaceholder[SIZE][t]{label}{name}{caption}
#                                          SIZE comes from the catalog's "figures"
#                                          when one is given, else always L.
#   - \begin{boxmain}[keys]{theme}{title}
#                                       -> \begin{boxmain}[SIZE][t][keys]{theme}{title}
#                                          SIZE comes from the catalog's "boxes",
#                                          matched via the "label=..." key inside
#                                          [keys], else always L.
#   - \newpage immediately before \begin{boxmessages} or \section*{Homework...}
#                                       -> \chapterhardbreak
#   - Everything else (\boxfigplaceholder, \boxbiofigplaceholder, \boxbio,
#     \begin{workedexample}, tables, \Cref, \authornote, ...) is left as-is:
#     same command/environment names and signatures in config.tex.
# =========================================================================

import argparse
import json
import os
import re
import sys

# Fallback mapping used when a catalog is supplied without its own
# "width_mapping" -- matches the book's actual column geometry
# (parameters.tex: 83.5mm column, 172mm full text width, 126mm M-figure).
DEFAULT_WIDTH_MAPPING = {
    "172 mm": "L",
    "126 mm": "M",
    "83.5 mm": "S",
}


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
# Figure/box catalog: label -> width string, read from a JSON catalog file.
# Structure: a list of chapter entries, each with a "figures" list and/or
# a "boxes" list of {"metadata": {"label": ..., "width": ..., ...}}. Only
# label/width matter here; caption/credits/etc. are ignored for now.
# Returns None (not {}) if the given section doesn't appear anywhere in the
# catalog, so callers can tell "not cataloged yet" apart from "cataloged
# but this one label is missing" and skip the per-item warning noise.
# -------------------------------------------------------------------------
def load_catalog_section(catalog_path, section):
    with open(catalog_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    widths = {}
    section_seen = False
    for chapter in data:
        if section in chapter:
            section_seen = True
        for item in chapter.get(section, []) or []:
            meta = item.get("metadata", {}) or {}
            label = meta.get("label")
            width = meta.get("width")
            if label:
                widths[label] = width
    return widths if section_seen else None


def normalize_width(width):
    return re.sub(r"\s+", "", str(width)).lower()


def resolve_size(kind, label, widths, width_mapping, warnings):
    """widths=None means "no catalog for this kind at all" -> always L, silently.
    kind is just for the warning text ("figure" / "box")."""
    if widths is None:
        return "L"
    width = widths.get(label)
    if not width:
        warnings.append(f"no catalog entry for {kind} '{label}' -> defaulting to L")
        return "L"
    norm = normalize_width(width)
    for key, size in width_mapping.items():
        if normalize_width(key) == norm:
            return size
    warnings.append(
        f"width '{width}' for {kind} '{label}' not in width_mapping -> defaulting to L"
    )
    return "L"


# -------------------------------------------------------------------------
# \figplaceholder{label}{name}{caption} -> \figplaceholder[SIZE][t]{...}
# SIZE is looked up per-label from the catalog (widths=None -> always L).
# Calls that already carry explicit [..] are left untouched (idempotent).
# -------------------------------------------------------------------------
def insert_figplaceholder_sizes(text, widths, width_mapping, positions=None):
    pattern = re.compile(r"\\figplaceholder(?![A-Za-z])")
    out = []
    warnings = []
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
        for _ in range(3):
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
        label = args[0].strip()
        saved = (positions or {}).get(label)
        if saved:
            size = saved.get("size", "L")
            placement = saved.get("placement", "t")
        else:
            size = resolve_size("figure", label, widths, width_mapping, warnings)
            placement = "t"
        braces = "".join("{%s}" % a for a in args)
        out.append("\\figplaceholder[%s][%s]" % (size, placement) + braces)
        i = pos
    return "".join(out), warnings


# -------------------------------------------------------------------------
# \begin{boxmain}[keys]{theme}{title} -> \begin{boxmain}[SIZE][t][keys]{theme}{title}
# (boxmain's own optional key group, e.g. [label=...], becomes the THIRD
# optional argument in the book version -- size and placement are new
# leading slots, see config.tex sec. 10.) SIZE is looked up in the catalog
# by the box's own "label=..." key, same as figures are looked up by their
# first mandatory argument. boxmain only meaningfully takes S or L (a
# mapped "M" would silently render as L in config.tex) -- widths=None means
# "no box catalog at all" -> always L, silently.
# -------------------------------------------------------------------------
def extract_label_from_keys(keys):
    m = re.search(r"\blabel\s*=\s*([^,\]]+)", keys)
    return m.group(1).strip() if m else None


def add_defaults_to_boxmain(text, widths, width_mapping, positions=None):
    pattern = re.compile(r"\\begin\{boxmain\}")
    out = []
    warnings = []
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
        label = extract_label_from_keys(keys)
        saved = (positions or {}).get(label) if label else None
        if saved:
            size = saved.get("size", "L")
            placement = saved.get("placement", "t")
        elif label is not None:
            size = resolve_size("box", label, widths, width_mapping, warnings)
            placement = "t"
        else:
            if widths is not None:
                warnings.append(
                    "boxmain call with theme '%s' has no label=... key -> "
                    "cannot look up its size, defaulting to L" % theme
                )
            size = "L"
            placement = "t"
        out.append("\\begin{boxmain}[%s][%s][%s]{%s}{%s}" % (size, placement, keys, theme, title))
        i = pos
    return "".join(out), warnings


# -------------------------------------------------------------------------
# Position sidecar: read back the [size][placement] currently sitting in an
# already-transformed book chapter file, keyed by label (figure label, or
# the box's own "label=..." key). Used to preserve hand-tuned positioning
# across re-runs of the transform (e.g. after a manuscript update) -- see
# main()'s "if outfile exists, snapshot it before overwriting" step.
# Tolerant of missing/odd brackets (falls back to L/t for that one entry)
# since this reads a file a person may have hand-edited.
# -------------------------------------------------------------------------
def extract_positions(text):
    positions = {}

    pattern = re.compile(r"\\figplaceholder(?![A-Za-z])")
    i = 0
    while True:
        m = pattern.search(text, i)
        if not m:
            break
        pos = m.end()
        size, placement = "L", "t"
        pos2 = skip_ws(text, pos)
        if pos2 < len(text) and text[pos2] == "[":
            size, pos2 = read_group(text, pos2, "[", "]")
            pos3 = skip_ws(text, pos2)
            if pos3 < len(text) and text[pos3] == "[":
                placement, pos2 = read_group(text, pos3, "[", "]")
        pos = pos2
        args = []
        ok = True
        for _ in range(3):
            pos = skip_ws(text, pos)
            if pos >= len(text) or text[pos] != "{":
                ok = False
                break
            content, pos = read_group(text, pos, "{", "}")
            args.append(content)
        if ok:
            positions[args[0].strip()] = {"size": size.strip(), "placement": placement.strip()}
            i = pos
        else:
            i = m.end()

    pattern = re.compile(r"\\begin\{boxmain\}")
    i = 0
    while True:
        m = pattern.search(text, i)
        if not m:
            break
        pos = m.end()
        size, placement, keys = "L", "t", ""
        if pos < len(text) and text[pos] == "[":
            size, pos = read_group(text, pos, "[", "]")
            pos2 = skip_ws(text, pos)
            if pos2 < len(text) and text[pos2] == "[":
                placement, pos2 = read_group(text, pos2, "[", "]")
                pos3 = skip_ws(text, pos2)
                if pos3 < len(text) and text[pos3] == "[":
                    keys, pos2 = read_group(text, pos3, "[", "]")
                pos = pos2
        theme, pos = find_group_after(text, pos, "{", "}")
        title, pos = find_group_after(text, pos, "{", "}")
        label = extract_label_from_keys(keys)
        if label:
            positions[label] = {"size": size.strip(), "placement": placement.strip()}
        i = pos
    return positions


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
def transform(text, preface, fig_widths=None, box_widths=None, width_mapping=None, positions=None):
    if width_mapping is None:
        width_mapping = DEFAULT_WIDTH_MAPPING

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

    text, fig_warnings = insert_figplaceholder_sizes(text, fig_widths, width_mapping, positions)
    text, box_warnings = add_defaults_to_boxmain(text, box_widths, width_mapping, positions)

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

    return "\n".join(header_lines) + "\n\n" + text, fig_warnings + box_warnings


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("infile", nargs="?", default=None)
    ap.add_argument("-o", "--outfile", default=None)
    ap.add_argument("--config", default=None, help="master config JSON (see module docstring)")
    ap.add_argument("--catalog", default=None, help="figure catalog JSON (overrides config's catalog_file)")
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--preface", dest="preface", action="store_true", default=None)
    group.add_argument("--no-preface", dest="preface", action="store_false")
    args = ap.parse_args()

    config = {}
    if args.config:
        with open(args.config, "r", encoding="utf-8") as f:
            config = json.load(f)

    infile = args.infile or config.get("input_file")
    outfile = args.outfile or config.get("output_file")
    catalog_file = args.catalog or config.get("catalog_file")
    width_mapping = config.get("width_mapping") or DEFAULT_WIDTH_MAPPING

    if not infile:
        ap.error("no input file (pass it directly, or set 'input_file' in --config)")

    with open(infile, "r", encoding="utf-8") as f:
        src = f.read()

    preface = args.preface
    if preface is None and "preface" in config:
        preface = config["preface"]
    if preface is None:
        preface = bool(re.search(r"\\setcounter\{chapter\}\{-1\}", src))

    widths = load_catalog_section(catalog_file, "figures") if catalog_file else None
    box_widths = load_catalog_section(catalog_file, "boxes") if catalog_file else None

    # --- position sidecar -------------------------------------------------
    # If the output file already exists, it may carry hand-tuned [size][t/b]
    # positioning from a previous run -- snapshot it into a
    # "<outfile>_positions.json" sidecar BEFORE we overwrite it. The sidecar
    # (whether just (re)written, or already there from before) then wins
    # over the catalog/defaults for any label it covers; labels missing
    # from it (new figures/boxes, or no sidecar at all) just fall through
    # to the normal catalog/default resolution -- nothing errors.
    positions = {}
    if outfile:
        stem, _ext = os.path.splitext(outfile)
        sidecar_path = stem + "_positions.json"
        if os.path.exists(outfile):
            try:
                with open(outfile, "r", encoding="utf-8") as f:
                    existing = f.read()
                captured = extract_positions(existing)
                with open(sidecar_path, "w", encoding="utf-8") as f:
                    json.dump(captured, f, indent=2, sort_keys=True)
                print(
                    f"snapshotted {len(captured)} position(s) from existing "
                    f"{outfile} -> {sidecar_path}",
                    file=sys.stderr,
                )
            except Exception as e:
                print(
                    f"warning: could not snapshot positions from {outfile} ({e}); "
                    f"leaving {sidecar_path} as-is",
                    file=sys.stderr,
                )
        if os.path.exists(sidecar_path):
            with open(sidecar_path, "r", encoding="utf-8") as f:
                positions = json.load(f)

    out, size_warnings = transform(
        src, preface, fig_widths=widths, box_widths=box_widths,
        width_mapping=width_mapping, positions=positions,
    )

    for w in size_warnings:
        print(f"warning: {w}", file=sys.stderr)

    if outfile:
        with open(outfile, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"wrote {outfile} (preface={preface}, catalog={catalog_file or 'none'})", file=sys.stderr)
    else:
        sys.stdout.write(out)


if __name__ == "__main__":
    main()
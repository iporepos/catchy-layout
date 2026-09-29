#!/usr/bin/env python3
# =========================================================================
# export_overleaf_zip.py -- package main.tex into a self-contained zip
# -------------------------------------------------------------------------
# Builds a zip that reproduces main.tex and nothing else: the shared
# engine (config/parameters/cover/colophon), the book cover photo + logo,
# every chapter file main.tex \includes, and figures for those chapters --
# T1 only (no draft tier, no PDFs alongside the raster files).
#
# Chapters 00 and 01 carry real manuscript content, so every figure/box/
# bio image they reference is pulled in. Every other included chapter is
# still the blind-text mock chapter -- only its \chaptercover photo is
# pulled in, so it opens correctly; everything else in it renders as the
# layout's own placeholder box, which is expected and harmless.
#
# The zip mirrors main.tex's own relative paths exactly (chapters/mock/...,
# bench/..., figures/chapterNN/T1/...), so unzipping it at the root of a
# new Overleaf project and compiling main.tex with pdfLaTeX (3 passes)
# reproduces the book as-is. Nothing here needs a terminal on the
# receiving end -- this script is the only command-line step.
#
# Usage:
#   python export_overleaf_zip.py                     # -> book_export.zip
#   python export_overleaf_zip.py -o mybook.zip
#   python export_overleaf_zip.py --full-chapters 00,01,02
#   python export_overleaf_zip.py --dry-run            # list, don't zip
# =========================================================================

import argparse
import re
import sys
import zipfile
from pathlib import Path

IMG_EXTS = (".pdf", ".png", ".jpeg", ".jpg")
# Cover/logo lookups prefer raster explicitly (per spec), regardless of
# whether a .pdf version ever shows up alongside them later.
RASTER_EXTS = (".png", ".jpeg", ".jpg", ".pdf")

INCLUDE_RE = re.compile(r"\\include\{([^}]+)\}")
CHAPTERCOVER_RE = re.compile(r"\\chaptercover\{([^}]+)\}")
MAKEBOOKCOVER_RE = re.compile(r"\\makebookcover\s*\{([^}]+)\}")
LOGOPATH_RE = re.compile(r"\\newcommand\{\\bookcoverlogopath\}\{([^}]+)\}")
LABEL_RE = re.compile(r"C(\d{2})-(?:cov|mtx|box|bio)-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*")
CHAPTER_NUM_RE = re.compile(r"chapter(\d{2})", re.IGNORECASE)

CORE_FILES = ["config.tex", "parameters.tex", "cover.tex", "colophon.tex"]


def strip_comments(text):
    """Drop everything from an un-escaped '%' to end of line, per line."""
    out = []
    for line in text.splitlines(keepends=True):
        i = 0
        while True:
            idx = line.find("%", i)
            if idx == -1:
                out.append(line)
                break
            if idx > 0 and line[idx - 1] == "\\":
                i = idx + 1
                continue
            out.append(line[:idx].rstrip("\n") + "\n")
            break
    return "".join(out)


def find_asset(base_no_ext: Path, exts=IMG_EXTS):
    """Same pdf->png->jpeg->jpg fallback order the layout's own macros use,
    unless exts=RASTER_EXTS is passed (cover/logo: raster preferred)."""
    for ext in exts:
        candidate = base_no_ext.parent / (base_no_ext.name + ext)
        if candidate.is_file():
            return candidate
    return None


def build_manifest(root: Path, main_rel: str, full_chapters):
    manifest = []   # list of (src: Path, arcname: str)
    warnings = []
    seen_arc = set()

    def add_file(rel_path):
        src = root / rel_path
        if not src.is_file():
            warnings.append(f"missing file, skipped: {rel_path}")
            return
        arc = Path(rel_path).as_posix()
        if arc not in seen_arc:
            seen_arc.add(arc)
            manifest.append((src, arc))

    def add_asset(rel_base_no_ext, exts=IMG_EXTS):
        found = find_asset(root / rel_base_no_ext, exts=exts)
        if found is None:
            warnings.append(
                f"missing image, skipped: {rel_base_no_ext}.[pdf|png|jpeg|jpg]"
            )
            return
        arc = found.relative_to(root).as_posix()
        if arc not in seen_arc:
            seen_arc.add(arc)
            manifest.append((found, arc))

    main_path = root / main_rel
    if not main_path.is_file():
        raise SystemExit(f"entry file not found: {main_path}")
    main_text = strip_comments(main_path.read_text(encoding="utf-8"))

    for core in CORE_FILES:
        add_file(core)
    add_file(main_rel)

    m = MAKEBOOKCOVER_RE.search(main_text)
    if m:
        add_asset(m.group(1).strip(), exts=RASTER_EXTS)
    else:
        warnings.append(f"no \\makebookcover{{...}} found in {main_rel}")

    params_text = strip_comments((root / "parameters.tex").read_text(encoding="utf-8"))
    m = LOGOPATH_RE.search(params_text)
    if m:
        add_asset(m.group(1).strip(), exts=RASTER_EXTS)
    else:
        warnings.append("no \\bookcoverlogopath found in parameters.tex")

    for inc in INCLUDE_RE.finditer(main_text):
        chap_rel = inc.group(1).strip()
        chap_rel_tex = chap_rel + ".tex"
        add_file(chap_rel_tex)

        chap_path = root / chap_rel_tex
        if not chap_path.is_file():
            continue
        chap_text = strip_comments(chap_path.read_text(encoding="utf-8"))

        num_match = CHAPTER_NUM_RE.search(chap_rel)
        chap_num = num_match.group(1) if num_match else None

        if chap_num in full_chapters:
            labels = sorted({m.group(0) for m in LABEL_RE.finditer(chap_text)})
        else:
            cc = CHAPTERCOVER_RE.search(chap_text)
            labels = [cc.group(1).strip()] if cc else []
            if not cc:
                warnings.append(f"no \\chaptercover{{...}} found in {chap_rel_tex}")

        for label in labels:
            lm = re.match(r"C(\d{2})-", label)
            if not lm:
                warnings.append(
                    f"couldn't read a chapter number out of label '{label}' "
                    f"(from {chap_rel_tex})"
                )
                continue
            fig_num = lm.group(1)
            add_asset(f"figures/chapter{fig_num}/T1/{label}_T1")

    return manifest, warnings


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--main", default="main.tex",
                     help="entry .tex file to reproduce (default: main.tex)")
    ap.add_argument("-o", "--output", default="book_export.zip",
                     help="output zip path (default: book_export.zip)")
    ap.add_argument("--root", default=".",
                     help="repository root (default: current directory)")
    ap.add_argument("--full-chapters", default="00,01",
                     help="comma-separated two-digit chapter numbers to export "
                          "ALL referenced figures for, not just the cover "
                          "(default: 00,01)")
    ap.add_argument("--dry-run", action="store_true",
                     help="print the manifest, don't write a zip")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    full_chapters = {c.strip().zfill(2) for c in args.full_chapters.split(",") if c.strip()}

    manifest, warnings = build_manifest(root, args.main, full_chapters)

    tex_count = sum(1 for _, arc in manifest if arc.endswith(".tex"))
    img_count = len(manifest) - tex_count
    print(f"{len(manifest)} files to package ({tex_count} .tex, {img_count} images)")

    if args.dry_run:
        for _, arc in manifest:
            print(f"  {arc}")
    else:
        out_path = Path(args.output).resolve()
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for src, arc in manifest:
                zf.write(src, arc)
        print(f"wrote {out_path}")

    if warnings:
        print(f"\n{len(warnings)} warning(s):", file=sys.stderr)
        for w in warnings:
            print(f"  - {w}", file=sys.stderr)


if __name__ == "__main__":
    main()

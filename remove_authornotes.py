#!/usr/bin/env python3
# =========================================================================
# remove_authornotes.py -- delete every \authornote{...} from a chapter file
# -------------------------------------------------------------------------
# Usage:
#   python remove_authornotes.py chapter01.tex                  # -> stdout
#   python remove_authornotes.py chapter01.tex -o chapter01.tex # in place
#   python remove_authornotes.py chapter01.tex -o clean.tex     # new file
#
# \authornote{...} content can itself contain braces (nested commands), so
# this does a balanced-brace scan rather than a regex match -- a plain
# regex like \authornote\{[^}]*\} would stop at the first inner '}'.
# =========================================================================

import argparse
import re
import sys


def strip_authornotes(text):
    pattern = re.compile(r"\\authornote(?![A-Za-z])")
    out = []
    i = 0
    count = 0
    while True:
        m = pattern.search(text, i)
        if not m:
            out.append(text[i:])
            break
        out.append(text[i:m.start()])
        pos = m.end()
        while pos < len(text) and text[pos] in " \t":
            pos += 1
        if pos >= len(text) or text[pos] != "{":
            # Not actually followed by a brace group -- leave it untouched
            # rather than silently eating something unexpected.
            out.append(text[m.start():m.end()])
            i = m.end()
            continue
        depth = 1
        j = pos + 1
        while depth > 0:
            if j >= len(text):
                raise ValueError("unbalanced braces in \\authornote starting near %d" % m.start())
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
            j += 1
        count += 1
        i = j
        # Collapse a leftover double space where the note used to sit.
        if out and out[-1].endswith(" ") and i < len(text) and text[i] == " ":
            i += 1
    return "".join(out), count


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("infile")
    ap.add_argument("-o", "--outfile", default=None, help="write here instead of stdout (pass the same path as infile to edit in place)")
    args = ap.parse_args()

    with open(args.infile, "r", encoding="utf-8") as f:
        src = f.read()

    out, count = strip_authornotes(src)

    if args.outfile:
        with open(args.outfile, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"removed {count} \\authornote(s) -> {args.outfile}", file=sys.stderr)
    else:
        sys.stdout.write(out)
        print(f"removed {count} \\authornote(s)", file=sys.stderr)


if __name__ == "__main__":
    main()
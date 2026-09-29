# catchy-layout
Catchment Hydrology Book TeX Layout

A two-column, Wiley-style (216×276mm) book layout built on `config.tex` as
the single source of structure, with all tunable numbers split out into
`parameters.tex`. Manuscript chapters plug in with parameter changes only,
not structural ones.

## File map

| File                          | Role                                                                                                                                                                                                                                          |
|--------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `parameters.tex`               | **Every tunable value.** Page/margin sizes, colors, fonts, spacing, toggles. Edit here to retune the layout.                                                                                                                                |
| `config.tex`                   | **All logic.** Packages, macros, environments, page styles. Reads values from `parameters.tex` (loaded via `\input` near the top). Shouldn't need edits just to retune numbers.                                                            |
| `cover.tex`                    | Book cover page (`\makebookcover{path}{title}{subtitle}{authors}`): full-bleed photo with anchor-based cropping, editor logo, title/subtitle, authors.                                                                                      |
| `colophon.tex`                 | "About this document" page (`\makecolophon`). Currently takes **no arguments** — the source link and technical-team credit are hardcoded in the macro body, so `\makecolophon{}` in `main.tex`/`mock_main.tex` has a stray, harmless `{}`. |
| `main.tex`                     | Entry point for the **real** book. See ⚠️ note below — this currently `\include`s only 4 top-level chapter files (`chapter00`–`chapter03`) that don't yet exist in the repo.                                                                |
| `mock_main.tex`                | Entry point for the **layout test bench** — same `config.tex`/`cover.tex`/`colophon.tex`, blind-text chapters, used to iterate on parameters without touching real manuscript content. `\include`s all 16 files under `chapters/mock/`.     |
| `chapters/mock/mock_chapterNN.tex` | One mock chapter (`NN` = 00–15). Calls `\startchapter`/`\startchapterstar`, `\chaptercover`, `\chapterfirstpage`, body content, `boxmessages` — see **Chapter anatomy** below.                                                          |
| `transform_manuscript.py`      | Converts a manuscript chapter file into a book chapter file: renames `\chapter`→`\startchapter`, folds `\openingimage`+`\inthischapter`→`\chaptercover`, lifts `boxskills` into `\chapterfirstpage`, and tags every figure/box with a size (S/M/L) and placement (t/b). Sizes can come from a figure/box **catalog JSON**, and hand-tuned `[size][t/b]` edits made directly in Overleaf are preserved across re-runs via an auto-generated position sidecar. Preface (chapter 0) is auto-detected. See the module docstring for the full CLI/config-JSON reference.                                              |
| `remove_authornotes.py`        | Strips every `\authornote{...}` call from a chapter file (balanced-brace scan, so notes containing nested commands are handled correctly). Run before a "clean" export; skip it while notes are still useful.                              |
| `compile_mock.py`              | Compiles `mock_main.tex` locally via the `losalamos` Python package's `DocumentTeX` helper (not a bare `latexmk` call).                                                                                                                     |

## Editing workflow

- **Want to retune a size, color, or spacing value?** Edit `parameters.tex` only.
- **Want to change how something is built or add a new component?** Edit `config.tex` (or add a new file like `cover.tex`/`colophon.tex` for a one-off page type).
- **Want to change chapter content?** Edit the chapter file. Structural commands (`\chaptercover`, `\figplaceholder`, `\boxmain`, etc.) should already exist — only their arguments change.
- **Want to turn a manuscript chapter into a book chapter?** Run `transform_manuscript.py` on it rather than hand-editing — it keeps figure/box placement decisions in an editable JSON sidecar so a re-run after a manuscript update doesn't clobber your hand-tuning.

## Chapter anatomy

A standard chapter, in order:

```latex
\startchapter{Chapter Title}
\chaptershortname{Short Name}          % optional, else falls back to title
\chaptercover{cover-label}{caption}{spoiler text}
\chapterfirstpage{skills box content}  % {} to omit the box entirely
... regular content, figures, boxes, worked examples ...
\begin{boxmessages}
Take-home text.
\end{boxmessages}
```

**Chapter 0 (Preface)** uses `\startchapterstar` instead (no numbering, no
part-color logic tie-in beyond the default), skips `\chaptercover` entirely,
and calls `\chapterfirstpage{}` (empty) to get the title/number row without
the skills box. It also skips `boxmessages` at the end. Chapters below
`\bookfirstdecoratedchapter` (parameters.tex, default `1`) never render the
skills box regardless of what's passed in.

### Content command reference

The commands you'll actually type inside a chapter body:

| Command | Signature | Notes |
|---|---|---|
| `\figplaceholder` | `[size][placement]{label}{name}{caption}` | size = `S`/`M`/`L` (default `L`), placement = `t`/`b` (default `t`). `M` gets a fixed 126mm width with a side caption; `S`/`L` scale to a fixed placeholder height, real images scale by width only. |
| `\boxmain` | `[size][placement][tcolorbox keys]{label}{title}...text...` | Numbered, themed box (tips, examples). `size`/`placement` same convention as figures. |
| `\boxbio` | `[placement]{name}{dates}{...}` (env) | Always two-column width; `placement` defaults to `b` per spec. |
| `workedexample` (env) | `{title}` | Not floated — sits inline in the running text. Auto-numbered `chapter.N`. |
| `\subcase` | `{label}` | Sub-heading inside a `workedexample`. |
| `\chaptershortname` | `{text}` | Overrides the running-header short title (defaults to the full chapter title). |
| `\chapterhardbreak` | — | Forces a fresh page (use before the take-home box or a "Homework" section — `\newpage` alone won't break out of two-column mode). |

## Known gotchas

- **`includehead` is required** in `\geometry` — without it the header
  renders outside the intended top margin.
- **`stfloats` is required** for `[b]` placement on two-column
  (`figure*`/`table*`) floats — standard LaTeX only supports `[t]`/`[p]` for those.
- **tcolorboxes must be `breakable=false`** — every box lives inside a
  float, and floats can't split across pages. A box that overflows one
  page must be split editorially, not made breakable.
- **`[t]` minipages starting with a box need `\vspace{0pt}` on *both*
  minipages** (not just the caption side) — otherwise the first one takes
  the box's *center* as its baseline reference instead of its top, and
  the two columns misalign (see the M-size figure command).
- **Chapter-number extraction uses `\xdef`, not `\def`** — a plain
  `\def` inside a `\StrLeft`/`\StrRight` call reverts once that local
  group closes, silently making the chapter number undefined outside it.
  `\xdef` assigns globally and fully expanded.
- **`\startchapterstar` needs an explicit `\phantomsection`** before
  `\addcontentsline` — hyperref anchors ToC links to the nearest
  `\refstepcounter` call, which `\startchapterstar` deliberately skips
  (it's unnumbered). Without `\phantomsection` the ToC entry links to the
  wrong place.
- **One-off page macros (colophon, etc.) must wrap font/color switches in
  `\begingroup...\endgroup`** — `\sffamily`/`\color` outside a group
  leak into everything that follows in the document.
- **`\chapter`/`\chapter*` are unused by real chapters** — the only
  caller is `\tableofcontents`'s internal `\chapter*{Contents}`, so
  `\titleformat{\chapter}` only styles the ToC title, nothing else.
- **`\bookvunit` is a frozen snapshot, not a live value** — it's set once
  from `\baselineskip` at `\AtBeginDocument` (i.e. body-text size), and
  does not update when `\baselineskip` changes locally inside boxes,
  captions, or footnotes. This is intentional: heading-spacing values
  stay a fixed physical distance everywhere in the book.
- **Avoid `titlepage`/`\frontmatter`/`\mainmatter` in a twocolumn book**
  — each forces its own page break (and `\cleardoublepage` can ship
  *two* blank pages in twocolumn mode), which stack up fast. Use
  `openany` and explicit `\clearpage`/`\pagenumbering` calls instead.

## ⚠️ Open items

- **`main.tex` is stale.** Its header comment describes the mock/test-bench
  role (copy-pasted from `mock_main.tex`), and it `\include`s
  `chapter00`–`chapter03` at the repo root — none of which exist yet.
  Real book chapters presumably belong in their own folder (mirroring
  `chapters/mock/`) once `transform_manuscript.py` starts producing them;
  until then, treat `main.tex` as a placeholder and `mock_main.tex` as the
  only file that reliably compiles end-to-end.
- **`\bookfirstpagenumboxwidth`/`height`** are defined in `parameters.tex`
  but may no longer be read anywhere in `config.tex` after the refactor —
  worth a grep before the next cleanup pass.
- **`\boxmain`/`boxbio` are untested in the mock chapter set** — none of
  the 16 `chapters/mock/mock_chapterNN.tex` files currently exercise them,
  so edge cases in those two commands haven't been provoked yet the way
  figures and worked examples have.

## Compiling

The mock/test-bench book compiles via the `losalamos` Python package:

```bash
python compile_mock.py
```

This loads `mock_main.tex` and runs it to PDF (multiple passes under the
hood — ToC and `\Cref` need the extra runs). If compiling directly with
`pdflatex`/`latexmk` instead, run **3 passes**.
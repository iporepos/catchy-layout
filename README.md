# catchy-layout
Catchment Hydrology Book TeX Layout

A two-column, Wiley-style (216×276mm) book layout built on `config.tex` as
the single source of structure, with all tunable numbers split out into
`parameters.tex`. Manuscript chapters plug in with parameter changes only,
not structural ones.
 
## File map
 
| File                                   | Role                                                                                                                                                                                                                                                                       |
|----------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `parameters.tex`                       | **Every tunable value.** Page/margin sizes, colors, fonts, spacing, toggles. Edit here to retune the layout.                                                                                                                                                               |
| `config.tex`                           | **All logic.** Packages, macros, environments, page styles. Reads values from `parameters.tex` (loaded via `\input` near the top). Shouldn't need edits just to retune numbers.                                                                                            |
| `cover.tex`                            | Book cover page (`\makebookcover`): full-bleed photo with anchor-based cropping, title/subtitle, authors, editor logo.                                                                                                                                                     |
| `colophon.tex`                         | "About this document" page (`\makecolophon`): compile timestamp, purpose note, source link, technical team.                                                                                                                                                                |
| `main.tex` / `mock_main.tex`           | Orchestration. Loads `config`/`cover`/`colophon`, calls the cover/colophon/ToC, then `\include`s chapter files in order. `mockup.tex` is the layout test bench — same config, blind-text chapters, used to iterate on parameters without touching real manuscript content. |
| `chapterNN.tex` / `mock_chapterNN.tex` | One chapter. Calls `\startchapter`/`\startchapterstar`, `\chaptercover`, `\chapterfirstpage`, body content, `boxmessages`.                                                                                                                                                 |
| `transform_manuscript.py`    (TODO)    | Converts a manuscript chapter file into a book chapter file, adding book-only parameters (figure size/placement, box size/placement) via editable JSON sidecar files.                                                                                                      |
| `compile_mock.py`                      | Compiles the `main_mock.tex` file locally using `latexmk`                                                                                                                                                                                                                      |
 
## Editing workflow
 
- **Want to retune a size, color, or spacing value?** Edit `parameters.tex` only.
- **Want to change how something is built or add a new component?** Edit `config.tex` (or add a new file like `cover.tex`/`colophon.tex` for a one-off page type).
- **Want to change chapter content?** Edit the chapter file. Structural commands (`\chaptercover`, `\figplaceholder`, `\boxmain`, etc.) should already exist — only their arguments change.

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


## Compiling
 
Compile using:

```python
python /compile_mock.py
```
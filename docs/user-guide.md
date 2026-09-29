# User Guide: Setting Up Your Book Project

This guide walks you through turning this repository into a compiling book,
starting from a fresh copy with no chapter text and no images in it. It's
written for anyone working in a graphical LaTeX environment — an Overleaf
project, or a local editor like TeXstudio, TeXmaker, TeXShop, or the LaTeX
Workshop extension for VS Code — using their **Recompile** / **Build** /
**Typeset** button. No command line is required anywhere in this guide.

If you want the full technical reference (every macro, every parameter,
every known gotcha), see [`README.md`](../README.md) at the repository
root. This guide is the on-ramp; the README is the manual you keep open
while you work.

---

## 1. What you're looking at

This repository is a **layout engine**, not a finished book. It gives you:

- A complete, tuned two-column page design (216×276mm, Wiley-style) —
  margins, fonts, colors, spacing, chapter openers, boxes, figures.
- A working **demo book** (`mock_main.tex`) with 16 example chapters full
  of placeholder text, so you can see every layout feature in action and
  compile something immediately, before writing a single word yourself.
- A clean split between **values** (`parameters.tex` — sizes, colors,
  spacing, all the numbers you'd tune) and **logic** (`config.tex` — how
  the page is actually built). You will spend almost all of your tuning
  time in `parameters.tex` and almost none in `config.tex`.

What it does **not** give you — on purpose:

- Any of your book's actual chapter text.
- Any of your book's actual images (cover photo, chapter photos, figures,
  author portraits, logos).

This repository is public, and a book's manuscript and artwork usually
aren't. So the entire `figures/` folder, and every real chapter file, are
left out of the repository and simply don't exist yet in a fresh copy.
Building them is what this guide is about.

---

## 2. Before you start

You need a LaTeX environment that can run **pdfLaTeX** and — importantly —
**recompile three times in a row** for a single document. This layout uses
a table of contents and cross-references, both of which need extra passes
to resolve correctly. A few notes depending on where you work:

- **Overleaf**: set the compiler to `pdfLaTeX` in the project's Menu panel.
  Overleaf normally re-runs the compiler automatically enough times to
  settle references, but if you ever see a stale table of contents or a
  "??" where a reference should be, click **Recompile** two or three more
  times.
- **A local GUI app** (TeXstudio, TeXmaker, TeXShop, Texifier, VS Code +
  LaTeX Workshop, etc.): make sure the project's build tool chain is set
  to pdfLaTeX, and either enable "compile until references are stable" if
  your app offers it, or just press **Build/Recompile** three times after
  any change that affects the table of contents or a cross-reference.

You do not need to install any LaTeX packages by hand — everything this
layout uses (`tikz`, `tcolorbox`, `xstring`, `eso-pic`, etc.) is loaded
automatically by `config.tex` and is included in any standard TeX
distribution (TeX Live, MiKTeX) or on Overleaf by default.

---

## 3. Getting the project into your editor

- **Overleaf**: create a new project and upload this repository's files
  and folders (drag-and-drop the whole folder, or use Overleaf's
  "Upload Project" option with a zip of the repository). Keep the folder
  structure exactly as it is — the files reference each other with
  relative paths.
- **Local GUI app**: open the repository's folder as the project's root
  directory (the folder containing `main.tex` and `mock_main.tex`).

Either way, don't change any file or folder names yet — do a first test
compile before touching anything.

---

## 4. First compile: the demo book

Before adding a single word of your own, compile the demo book to confirm
your environment is set up correctly:

1. Set **`mock_main.tex`** as the file to compile (in Overleaf, click the
   file, then use the dropdown near the Recompile button, or set it as
   the main document in Project Settings; in a local app, open
   `mock_main.tex` and set it as the root/main document).
2. Recompile. Do it **three times** the first time, so the table of
   contents and cross-references settle.
3. You should get a full mock book: a cover page, an "About this
   document" page, a table of contents, and 16 chapters of placeholder
   ("Lorem ipsum") text demonstrating every layout feature — chapter
   covers, figures, boxes, worked examples, take-home messages.

If this compiles cleanly, your environment is ready and any problem you
hit later is almost certainly about content or file placement, not setup.
Keep `mock_main.tex` around even after you start your own book — it's
your safe place to test a parameter change before applying it to the real
thing.

---

## 5. The folder tree you need to build

Here is the complete tree this layout expects, once a real book is fully
populated. Everything marked **(ships)** already exists in your copy of
the repository. Everything marked **(you add this)** does not exist yet
and you'll create it as you go — that's the point of this guide.

```
your-book-project/
├── main.tex                    (ships, but see step 8 — currently a stale placeholder)
├── mock_main.tex                (ships) — working demo, keep it for testing
├── config.tex                   (ships) — layout logic, rarely edited
├── parameters.tex               (ships) — every tunable value
├── cover.tex                    (ships) — book cover macros
├── colophon.tex                  (ships) — "About this document" page macros
│
├── chapters/
│   ├── mock/                    (ships) — 16 demo chapters, leave these alone
│   │   ├── mock_chapter00.tex
│   │   ├── mock_chapter01.tex
│   │   └── ... mock_chapter15.tex
│   ├── chapter00.tex             (you add this) — your Preface
│   ├── chapter01.tex             (you add this) — your Chapter 1
│   └── chapterNN.tex             (you add this) — one file per chapter
│
└── figures/                      (you create this entire folder)
    ├── cover/
    │   ├── main-cover.jpg          (you add this) — full-bleed book cover photo
    │   └── logo.png                 (you add this) — publisher/editor logo
    │
    ├── chapter00/
    │   ├── T0/                       (you add images here — draft quality)
    │   └── T1/                       (you add images here — final quality)
    ├── chapter01/
    │   ├── T0/
    │   └── T1/
    └── chapterNN/
        ├── T0/
        └── T1/
```

A few things worth noticing about this tree:

- The `figures/` folder doesn't exist at all in a fresh copy of the
  repository. You are creating it from scratch, chapter by chapter, as
  you gather your book's artwork.
- Every chapter gets **two** image folders, `T0` and `T1` — this is a
  two-tier system explained in the next section, not a duplication
  mistake.
- Chapter numbers are always **two digits**: `chapter00`, `chapter01`, ...
  `chapter15`, not `chapter0`/`chapter1`. Chapter `00` is the Preface.

---

## 6. How images are named and found

Every image in this layout is looked up automatically by a naming
convention — you never write a full file path or a file extension inside
a chapter. You just save your image with the right name in the right
folder, and the layout finds it.

### The two-tier system: T0 and T1

Each chapter's image folder has a `T0` and a `T1` subfolder:

- **`T1`** = the final, production-quality version of an image.
- **`T0`** = a draft, sketch, or placeholder version.

The layout always looks for the `T1` version **first**, and only falls
back to `T0` if no `T1` file exists yet. This means you can start writing
a chapter with rough placeholder art in `T0`, see it flow correctly on
the page, and later drop the finished artwork into `T1` with the exact
same base filename — the page updates automatically, nothing in the
chapter text needs to change.

You also don't need to worry about file format: the layout tries, in
order, `.pdf`, `.png`, `.jpeg`, then `.jpg` for every image. Save your
file in whichever of those four formats you have; there's no need to
convert anything.

### The filename pattern

Every image filename follows this shape:

```
C{NN}-{kind}-{label}_T{0 or 1}.{pdf|png|jpeg|jpg}
```

- **`{NN}`** — the two-digit chapter number this image belongs to (must
  match the folder it sits in: an image inside `figures/chapter06/` must
  start with `C06-`).
- **`{kind}`** — what role the image plays. One of:

  | kind  | used for                                                | placed in a chapter with |
  |-------|----------------------------------------------------------|---------------------------|
  | `cov` | the full-bleed photo at the top of a chapter's opening page | `\chaptercover{...}` |
  | `mtx` | an ordinary in-text figure                                | `\figplaceholder{...}` |
  | `box` | an image living inside a tip/example/take-home box        | inside a `\boxmain{...}` |
  | `bio` | an author or researcher's biography portrait               | inside a `boxbio` environment |

- **`{label}`** — any short, descriptive, lowercase word or two of your
  choosing (`livelihoods`, `budyko`, `perth`...). This is what ties the
  image file to the place in your chapter text that displays it, so pick
  something you'll recognize later.
- **`_T{0 or 1}`** — the tier, as above.

Two worked examples:

- The opening photo for Chapter 6 goes in `figures/chapter06/T1/` (or
  `T0/` while you're still sourcing final art), named
  `C06-cov-livelihoods_T1.jpeg`.
- A biography portrait for Chapter 1 goes in `figures/chapter01/T1/`,
  named `C01-bio-budyko_T1.jpeg`.

### The one exception: the book cover and logo

The outer book cover photo and the publisher/editor logo don't belong to
any chapter and don't use the tier system. They live directly in
`figures/cover/` with a plain name and no chapter prefix:

- `figures/cover/main-cover.jpg` (or `.pdf`/`.png`/`.jpeg`) — the
  full-bleed photo on the book's front cover.
- `figures/cover/logo.png` (or `.pdf`/`.jpeg`/`.jpg`) — the small
  publisher/editor logo shown on the cover.

---

## 7. Setting up your book cover

Open `mock_main.tex` (or your own main file, once you have one — see
step 8) and find the `\makebookcover` call near the top:

```latex
\makebookcover
  {./figures/cover/main-cover}
  {Hydrology}
  {Unified principles and practices across scales}
  {M. Sivapalan \\ Peter A. Troch \\ Günter Blöschl}
```

The four arguments are, in order: the cover photo's path **without a file
extension** (the layout adds the extension automatically), the title, the
subtitle, and the author list (`\\` between names to stack them on their
own lines). Once you've placed `main-cover.jpg` and `logo.png` in
`figures/cover/` as described above, replace these four values with your
own book's details.

If you don't have final cover art yet, leave the folder empty — the
layout draws a clearly-labeled gray placeholder box instead of failing,
so you can keep working on everything else first.

---

## 8. Writing your first real chapter

The shipped `main.tex` currently still points mostly at the mock/demo
chapters rather than real content — it hasn't been adapted into your
book's actual entry point yet. The reliable way to start is to copy the
pattern that already works in `mock_main.tex`.

**Step by step:**

1. Duplicate `mock_main.tex` and rename the copy (for example `main.tex`,
   replacing the placeholder version — or `book_main.tex`, if you'd
   rather keep the original `main.tex` untouched for now).
2. Inside your new copy, replace the `\makebookcover{...}` details with
   your own (step 7 above).
3. Replace the block of `\include{chapters/mock/mock_chapterNN}` lines
   with `\include{chapters/chapterNN}` lines pointing at chapters you're
   about to write — start with just one, e.g. `\include{chapters/chapter00}`.
4. Create `chapters/chapter00.tex` (your Preface). The easiest way is to
   duplicate `chapters/mock/mock_chapter00.tex` into the `chapters/`
   folder (not inside `mock/`) under its new name, then replace the
   placeholder text with your own. Every structural command already
   there (`\startchapterstar`, `\chapterfirstpage`, etc.) can stay as-is
   — only the words change.
5. Recompile your new main file three times.

Once Chapter 0 compiles the way you want, repeat for Chapter 1 onward,
using `chapters/mock/mock_chapter01.tex` (a fully decorated chapter, with
a cover page, skills box, figures, boxes, and a take-home box) as your
template instead.

### Anatomy of a standard chapter

Every real chapter (Chapter 1 onward) follows this shape:

```latex
\startchapter{Your Chapter Title}
\chaptershortname{Short Running-Header Name}   % optional
\chaptercover{C01-cov-yourlabel}{Caption text under the photo}{Spoiler paragraph}
\chapterfirstpage{
  \begin{itemize}
  \item A skills/learning-objective bullet.
  \item Another one.
  \end{itemize}
}

... your chapter's actual text, figures, and boxes ...

\begin{boxmessages}
Your take-home summary text.
\end{boxmessages}
```

The Preface (Chapter 0) is simpler — it uses `\startchapterstar` instead,
skips `\chaptercover` and `boxmessages` entirely, and calls
`\chapterfirstpage{}` with nothing inside the braces (just a title row,
no skills box).

For the full list of content commands you'll use inside a chapter body
(`\figplaceholder`, `\boxmain`, `\boxbio`, `workedexample`, and so on),
see the **Content command reference** table in `README.md` — every one of
them is already demonstrated in the matching `chapters/mock/mock_chapterNN.tex`
file, so the fastest way to learn a command is to find it being used
there first.

---

## 9. Tuning the design: two files, two purposes

Once your content is in place, you'll likely want to nudge the design.
There are exactly two places to look, and they have different jobs:

- **`parameters.tex`** — every number, color, font size, and spacing
  value in the whole book. Want the chapter cover photo taller? The
  author line in a different position? A box's padding adjusted? It's a
  single named value in this file. This is the file you'll edit most.
- **`config.tex`** — how those values get turned into an actual page.
  You should rarely need to open this file unless you're changing how a
  component is *built*, not just how big or where it sits.

Every value in `parameters.tex` has a comment explaining what it controls
and, often, what to check if changing it looks wrong. When in doubt,
search `parameters.tex` for a word related to what you're trying to
change (e.g. "author", "cover", "spacing") before touching `config.tex`.

---

## 10. Troubleshooting

- **The table of contents or a cross-reference looks wrong or shows "??"**
  — recompile two or three more times. This layout's ToC and `\Cref`
  references need multiple passes to settle; it's expected on the first
  compile after a structural change.
- **An image doesn't show up and you see a gray placeholder box instead**
  — check three things: the file sits in the right chapter's `T0` or
  `T1` folder, the filename's chapter number prefix (`C06-...`) matches
  the folder it's in, and the `{label}` in the filename matches exactly
  what's written in the chapter's `\figplaceholder`/`\chaptercover`/etc.
  call (it's case-sensitive).
- **A box or figure looks cut off at the bottom of a page** — boxes in
  this layout can't split across pages by design; shorten the content or
  move it, rather than trying to force it to break.
- **The header text renders in the wrong place, outside the top margin**
  — this usually means `includehead` was removed from the page geometry
  in `config.tex`; it shouldn't be touched, but if you're investigating
  a layout issue near the header, that's the setting to check first.
- **A chapter's title/number row doesn't line up with the header rule
  below it** — see `\bookfirstpagetitlenudge` in `parameters.tex`
  (Section 7) — it's a small deliberate correction, not a bug, but it
  may need retuning if you change fonts or sizes nearby.

For anything not covered here, the **Known gotchas** section of
`README.md` documents every layout quirk found so far, with the reasoning
behind each one.

---

## 11. Where to go next

- **`README.md`** — the full technical reference: every file's role, the
  complete content command table, and every known gotcha.
- **`chapters/mock/`** — sixteen worked examples of every layout feature.
  When you're not sure how to use a command, find it in use here first.
- **`parameters.tex`** — read through it once, top to bottom. It's
  organized by section and commented throughout; twenty minutes with
  this file will teach you most of what this layout can do.

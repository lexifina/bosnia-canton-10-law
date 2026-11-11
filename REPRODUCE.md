# How this repository was made (Canton 10)

This file is written by the build on 2026-11-11, the day the source data was retrieved.

## Sources

| Source | Address | Retrieved | Licence |
| --- | --- | --- | --- |
| Vlada Hercegbosanske županije: Narodne novine Hercegbosanske županije (each issue as a PDF, 1996-2025) | <https://www.vladahbz.com/narodne-novine/> | 2026-11-11 | Official text, not protected: Zakon o autorskom i srodnim pravima BiH (Sl. glasnik BiH 63/10), čl. 8(1)(b) |
| Narodne novine Hercegbosanske županije (each issue as a PDF) | <https://www.vladahbz.com/narodne-novine/> | 2026-11-11 | Official text, not protected: Zakon o autorskom i srodnim pravima BiH (Sl. glasnik BiH 63/10), čl. 8(1)(b) |

Every word of law in this repository comes from these sources. Lexifina reads them and records each act's dated versions, and the laws that made each change, in one corpus file. This repository is built from that file.

## What is in it

| Act | Title | Versions | Span |
| --- | --- | ---: | --- |
| 48 acts | every act, with its kind, number, status and span, is listed in [ACTS.md](ACTS.md) | 48 | |

The build made 48 commits:

| Commits | Kind |
| ---: | --- |
| 48 | first version of an act |
| 0 | one law on its in-force day |
| 0 | changes no amendment note explains, credited to the publisher |

Other counts:
- 0 commits on the branch `buducnost`: laws not yet in force on 2026-11-11.
- 0 commits dated 1 January 1970: in force before 1970, with the real day in their `In-force` trailer.
- 48 laws in the record.
- 96 tags.

## Dates

Each commit is dated at noon (Europe/Sarajevo) on the day the change took effect. The other dates, enacted and published, are trailers.

When a law gives no date of its own, the default rule applies: A law takes effect on the day its own final article names, counted from its publication in the Narodne novine Hercegbosanske županije. https://www.vladahbz.com/narodne-novine/

## How the history is built

`tools/build/build.py` (and, for later publishes, `tools/build/append.py`) turns the corpus into this history in one pass: one commit per law, on the day it took effect. The same corpus always gives the same commit hashes. `tools/build/check_repo.py` reads every version back from git and compares it with the corpus. `tools/on.py` shows the law as it stood on any date. The corpus format is described in `tools/build/SCHEMA.md`.

- Corpus: sha256 `da6a9d8a962ac1053f0a3ebf797daa249a1716b7981c78260106444955f22929` (1704611 bytes).
- Builder blob hashes (`git hash-object`): `build.py` `7ff2a6900797ff7ab8c9d8fd28125e5e52250112`, `check.py` `f7f9c39fff1b1f9a3aded2ad3364a27fb0908033`, `on.py` `0be88de7820b2dafe9f94fa40472a48776aa4cf5`.
- Python 3.12.10; git version 2.46.0.windows.1.

## Checks

Not yet run for this build.

No second build of this corpus has been compared yet.

## Decisions made by hand

- Every act's decisions made by hand (3 in all) are listed in that act's own README.md, under "Decisions made by hand".

## What AI did and did not do

The scripts that read the sources and build this repository were written by Claude Code running Claude Opus 5.5 (`claude-opus-5-5`) under Lexifina's direction.

No model wrote, translated or corrected legal text. No model runs at build time. Every word of law in this repository comes from the official sources above.

The commit messages are written by `build.py` from the source data.

Model use at data-build time:
- none: the text is read from the gazette PDFs' text layer by a deterministic parser; no model output is legal text.

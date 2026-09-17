# Bespoke Reader

*Your book, cut to your measure.*

**English** | [简体中文](README.zh-CN.md)

Bespoke Reader tailors a whole book to one reader. It measures the gap between you and the book, keeps the original text you need, cuts what you already know, annotates the places you cannot yet cross alone, and hands you a personal EPUB.

An Agent Skill for Claude (apps and Claude Code), Codex, and other agents that support `SKILL.md`.

## Why it exists

A book and its reader are almost never aligned. Some chapters cover what you already know. Some passages sit above your current understanding. Others assume background you lack, and you often do not know you lack it. All three misalignments consume reading time, while the part you actually absorb stays small.

The usual alternatives are summaries, explainers, and guided readings. They save time, but someone else decides what is worth knowing, and the author's argument, the texture of the language, and the way the author thinks disappear along the way. What remains is a set of conclusions, not a book.

Bespoke Reader sits between the two. It does not read the book for you and does not rewrite it. It measures the gap between this reader and this book, then decides which parts of the original stay. Everything you read is still the author's own words.

## How it works

**1. Read the whole book and identify its type**
Fifteen types (argument, popular science, method, academic monograph, history, philosophy, fiction, poetry and drama, and more) each have their own unit of value and their own way of being trimmed. Philosophy, literary fiction, poetry, and detective fiction are never cut, only annotated.

**2. Calibrate with questions drawn from the book**
It never asks about your level. It turns the book's own claims and reasoning chains into multiple-choice questions, at most 20, adapting each batch to your previous answers.

- Topic layer: how familiar you are with the book's tradition and core concepts
- Claim probes: the book's specific claims; did you know it, hear of it without thinking it through, find it new, or disagree
- Self-assessment checks: spot-checks on what you marked as "knew it", to catch overestimation
- Thinking probes: reasoning depth, framework transfer, missing links; where your reasoning stops and how many steps further the author goes

**3. Show the gap map, and wait for your confirmation**

| Gap | Meaning | Treatment |
|---|---|---|
| Covered | You know it, and passed a check | Compressed to one line or cut |
| Knowledge gap | You lack a concept or background | Original kept, background card added |
| View gap | You hold a different view | Kept in full, with the author's premises and counterarguments |
| Thinking gap | You do not yet have the author's way of reasoning | Highest priority, marked as key |

Your reading goal and time budget then set the retained length and estimated reading time. When the budget cannot hold the essential passages, you decide; nothing essential is cut on your behalf.

**4. Trim, annotate, and build the EPUB**
Annotations point to mechanisms and what transfers beyond the book; they do not restate content. The EPUB opens directly in Apple Books, WeChat Read, and other reader apps.

## Example: *Antifragile*

Nassim Nicholas Taleb, *Antifragile: Things That Gain from Disorder* (2012).

<!-- Replace the numbers below with the results of the demo run. -->

| | |
|---|---|
| Reading goal | _TBD_ |
| Time budget | _TBD_ |
| Original length | _TBD_ words |
| Retained | _TBD_ words (_TBD_%) |
| Estimated reading time | _TBD_ |

**Calibration questions**

![Calibration questions](examples/antifragile/en-01-calibration.png)

**Gap map**

![Gap map](examples/antifragile/en-02-gap-map.png)

**A page of the tailored book**

![Tailored page with markers](examples/antifragile/en-03-page.png)

**A "Don't skip" passage**

![Don't skip passage](examples/antifragile/en-04-dont-skip.png)

The full EPUB is not included in this repository because it contains the book's text.

## What you get

- **Front matter**: gap map, background cards, a one-page skeleton of the book, and type-specific cards (concept maps, timelines, method cards, character maps)
- **Body**: the original text in its original order, with markers
  - `[Skim]` summarized passage
  - `[Cut N ¶: reason]` where and why something was cut
  - `[Note]` annotation on mechanism
  - `[Predict]` a question to think about before reading on
  - `[Don't skip]` a passage that challenges your position and is most worth reading
- **Back matter**: where the author's ideas come from, present-day mapping, limits and counterarguments, and a full cut log

Chinese readers get the same structure with Chinese markers (`〔略读〕` `〔批注〕` `〔别跳〕` …). Questions, annotations, and markers always follow your language; the book's text stays in its own language.

## Design principles

- Measures only the gap between you and this book; never grades your overall level.
- Nothing is cut before you confirm the gap map.
- An unverified "knew it" is summarized, never cut.
- Every book keeps one to three passages that oppose your position, so the tool never simply confirms what you already believe.
- AI extrapolation is always kept separate from the author's views.
- No spoilers in pre-reading mode.

## Installation

The `bespoke-reader/` folder is the skill itself (`SKILL.md` plus `scripts/`). The host must be able to run Python to parse and package EPUB files.

```bash
git clone https://github.com/<username>/bespoke-reader.git
```

**Claude apps (web or desktop)**
Zip the `bespoke-reader/` folder and upload it on the Skills page in Settings. Code execution must be enabled.

**Claude Code**
```bash
cp -r bespoke-reader/bespoke-reader ~/.claude/skills/
```

**Codex**
```bash
cp -r bespoke-reader/bespoke-reader ~/.agents/skills/
```

## Usage

Give the agent a book file (EPUB preferred; PDF and TXT also work) and say any of:

- "Tailor this book to me"
- "Bespoke reading"
- "Cut this book to my level"

Then answer the questions about your goal, time budget, and calibration.

## Copyright

The output contains the book's text. It is for the personal use of a reader who owns the book. Do not share it publicly.

## License

MIT

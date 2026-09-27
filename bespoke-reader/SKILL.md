---
name: bespoke-reader
description: "Bespoke Reader 量体裁书: tailors a whole book (EPUB, PDF, TXT) to one reader. Measures the gap between reader and book with multiple-choice questions drawn from the book itself, trims the original text by reading goal and time budget, annotates what the reader cannot yet cross alone, adds chapter guides, character tables and plot hints for hard fiction, and outputs a personal EPUB that keeps the original cover and styling. Triggers: \"tailor this book\", \"bespoke reading\", \"gap reading\", \"cut this book to my level\"; 「量体裁书」「差距阅读」「帮我拆这本书」「按我的水平处理这本书」."
---

# Bespoke Reader v2.0

Aim: the smoothest, most comfortable reading of this book this reader can have. Time goes to the book itself, not to re-reading passages that are already familiar, looking up background halfway through a page, or losing track of who is who and when.

Core principle: do not locate the reader's absolute level. Measure only **the gap between this reader and this book**. The gap decides what is cut, kept, and annotated; the **reading goal** decides emphasis; the **time budget** caps the total.

## Host and language conventions

This skill runs on any agent that can read files, run Python, and write files (Claude apps, Claude Code, Codex, and similar).

- **Questions**: every calibration and confirmation step is multiple choice. If the host offers a structured question tool, use it, at most 4 questions per batch. Otherwise, post the batch in chat as numbered questions with lettered options and wait for the answers before continuing.
- **Working files**: keep intermediate files in `bespoke-work/<book-slug>/` under the current working directory (or the host's scratch directory). Scripts live in `<skill-dir>/scripts/`.
- **State file**: keep `bespoke-work/<book-slug>/state.md` up to date: every decision the reader made (goal, budget, speed, mode, hint depth, extras, reader app), the gap map, the per-chapter budget, and which chapters have specs. Hosts lose sessions and hit usage limits; with the state file, the specs and the original book, any new session resumes where the last one stopped.
- **Backups**: after each part of the book, send the reader a zip of `state.md`, `spec/` and `front/`. These contain no book text, so they are safe to keep anywhere, and they are enough to rebuild or revise the EPUB later.
- **Output**: write the final file to the host's designated output directory if one exists, otherwise to `./output/`, then deliver it through whatever mechanism the host provides for sending files to the user.
- **Language**: talk to the reader, write questions, annotations, cards, and markers in **the reader's language** (the language of their messages, unless they ask otherwise). Original text always stays in the book's own language and is never translated in place.

**Markers** (use the column matching the reader's language; for other languages, translate the English column):

| Purpose | English | 中文 |
|---|---|---|
| Summarized passage | `[Skim]` | `〔略读〕` |
| Cut passage | `[Cut N ¶: reason]` | `〔删去 N 段：原因〕` |
| Annotation | `[Note]` | `〔批注〕` |
| Prediction prompt | `[Predict]` | `〔先想〕` |
| Must-read passage | `[Don't skip]` | `〔别跳〕` |
| Self-test | `[Self-test]` | `〔自测〕` |
| Chapter guide | `[Guide]` | `〔导读〕` |
| Plot or reading hint | `[Hint]` | `〔提示〕` |

**Locators**: show a paragraph locator only where something was done: a paragraph with a note, hint, prediction or Don't skip flag, and every Skim or Cut line (with the range it replaces). Paragraphs kept untouched carry no locator; a number before every paragraph spoils the reading.

## Kinds of gap

| Kind | Meaning | Treatment |
|---|---|---|
| Covered (verified) | Reader knows it and passed a check question | Compress to one line or cut |
| Covered (assumed) | Reader claims to know it, not verified | Summarize as a skim, never cut |
| Knowledge gap | Reader lacks a concept or background the book uses | Keep, add background |
| View gap | Reader holds a different view or disagrees | Keep in full, add the author's premises and counterarguments |
| Thinking gap | Reader lacks the author's way of reasoning | Highest priority, mark as key |

Thinking gaps are the most valuable and the hardest to measure; calibration must include questions designed for them.

## Workflow

### Step 0: Extract the whole book

```bash
python3 <skill-dir>/scripts/extract_epub.py book.epub bespoke-work/<book-slug>
```

It unpacks the EPUB into `orig/` (the cover, stylesheets and images are reused at build time), writes one `text/chNNN.txt` per spine item with every paragraph prefixed `[N.i]`, lists footnotes separately at the end of each file, and writes `paras.json`, `meta.json` and `index.tsv`. Chapter numbers follow the spine and never skip, so text files, spec files and the build always agree. Front matter such as copyright pages and tables of contents shows up as small files; ignore them. When citing a location to the reader, give the chapter title and the opening words, not only the number. For PDF or TXT, produce the same files with available tools.

Chapter files are often too large to read at once. Read them in chunks of about 27 KB, cut at line boundaries, and read the **entire** book, not only the beginning. Read the author's notes, afterword and appendices too: they are raw material for annotations.

### Step 1: First pass, structure and type

Write `notes/overview.md`: type and value unit, estimated padding ratio, total length, core argument chain, high-value paragraph locators (thinking-gap candidates), author-level clues (background, writing situation, self-image, contradictions, moments of self-doubt), suspicious anecdotes and quotations, publication year (for science, practical, and academic books, to judge what is outdated).

**Type table**

| Family | Type | Value unit | Mode | Base retention |
|---|---|---|---|---|
| Nonfiction | Argument (social commentary, politics, cultural criticism) | Claims | Cut | 15–20% |
| Nonfiction | Popular science, subject introductions | Concepts, models, key evidence | Cut | 20–30% |
| Nonfiction | Practical, method, business, self-help | Methods and their conditions | Heavy cut, convert to method cards | 5–10% |
| Nonfiction | Academic monograph, classic textbook | Argument, method, place in the literature | Cut surveys, keep method and argument | 25–40% |
| Nonfiction | History | Turning points, explanatory frameworks | Cut chronicle, keep explanation | 15–25% |
| Nonfiction | Biography, memoir | Key decisions, construction of self-narrative | Cut | 15–25% |
| Nonfiction | Essays, collections | Observation and language | Select whole pieces, never cut within a piece | 30–50% |
| Nonfiction | Interviews, speeches | Distinctive answers | Cut repetition and pleasantries | 10–20% |
| Philosophy | Systematic treatise | Argument steps | Annotate, almost no cuts | 80%+ |
| Philosophy | Aphorisms, fragments, dialogues | Core propositions and thematic links | Annotate, build a thematic index | 80%+ |
| Fiction | Detective fiction | Puzzle and structure | Post-reading breakdown, never reorder | No cuts |
| Fiction | Science fiction, fantasy (setting-driven, idea-driven) | Setting and its consequences, key scenes, the ideas the plot carries | Pre-reading (full or trimmed) or post-reading | Full: no cuts; trimmed: 35–50%, set by budget |
| Fiction | Literary fiction, including dense classics (Dostoevsky, Latin American novels, multi-generation sagas) | Form, point of view, image systems, who is who | Reader aids plus post-reading close annotation | No cuts by default |
| Fiction | Genre fiction, long web serials | Main plot, character change | Skip markers | Keep 20–40% along the main line |
| Poetry, drama | Poetry collections, plays | Images, allusions, conflict structure | Annotate, no cuts | No cuts |

**Mixed books**: chapters may belong to different types (narrative and argument alternating, method inside memoir). Decide the main type, tag each chapter with its own type, and apply per-chapter rules in Step 4.

For fiction, first ask whether the reader has already read it (this selects pre- or post-reading mode), and what makes the book hard for them: names and relationships, jumping timelines, background knowledge, the ideas, or plain length. The answer decides which reader aids to build (Step 4, fiction).

**Extras**: list what the edition carries besides the main text (author's notes and references, translator's notes, afterword, appendices, bonus stories) and ask in batch 0 how to treat each: fold into annotations, keep as optional back matter outside the budget, or leave out.

### Step 2: Calibration (the critical step)

Never ask "what is your level". Build every question from the book. **The entire calibration is multiple choice; no open-ended questions are inserted**, so the flow stays uninterrupted. At most 4 questions per batch.

**Batch order and limits**

| Batch | Content |
|---|---|
| 0 | Reading goal, time budget, reading language and speed; for fiction, whether already read; target reader app may be asked here or in the last batch |
| 1 | A: topic layer |
| 2–3 | B: claim probes (adjusted by the adaptive rules) |
| 4 | B′: self-assessment checks, and C: thinking probes |
| 5 | Remaining C questions if needed |

Whole calibration, batch 0 included: at most 20 questions in 6 batches. Questions removed by adaptive rules are not replaced.

**Batch 0: goal and budget**

1. Reading goal (single choice): master it systematically (course, thesis, work) / grasp the core ideas / learn how the author thinks / read critically, to review or rebut / get the gist, enough to discuss it
2. Time budget: under 2 hours / 2–5 hours / 5–10 hours / unlimited
3. Reading language and speed: native, fast / native, normal / non-native, fluent / non-native, needs a dictionary
4. For fiction: how much the hints may reveal (only what has happened so far, recommended / may foreshadow / full post-reading analysis) and in what form (chapter guides plus hints in the text, recommended / chapter guides only / in-text hints only)

Default effective speeds for original text, including time spent on annotations:

| | Native fast | Native normal | Non-native fluent | With dictionary |
|---|---|---|---|---|
| CJK text (characters/min) | 450 | 300 | 150 | 80 |
| Alphabetic text (words/min) | 250 | 180 | 100 | 50 |

The reader can correct these in the feedback loop.

**A. Topic layer (3–4 questions, before claim probes)**
Claim probes assume the reader has a foundation in the book's subject, so test that first: the intellectual tradition the book belongs to, its core conceptual framework, its era and context. Options: can explain and evaluate it / know the gist / have only heard the term / unfamiliar. Every "unfamiliar" item requires a background card at the front of the output; "only heard the term" items should get one too.

**B. Claim probes (8 by default, adaptive range 5–10)**, one sentence each, fixed options:
- Knew it already
- Heard of it, never thought it through
- New to me
- Disagree

Rules:
- Write **this book's specific version** of a claim, not a truism everyone accepts.
- At least one counterintuitive claim, and at least one of the book's most central claims.
- Cover the beginning, middle, and end of the book.
- **Compression must not change the strength or scope of the author's position.** If the author "admits X has an objective function but refuses to praise it", do not compress to "the author denies X's function". Otherwise "Disagree" measures distortion in the probe, not a real view gap.
- In pre-reading mode, probes touch only premises and themes, never plot.

**B′. Self-assessment checks (1–3 questions)**
"Knew it already" is often an overestimate. Spot-check those items:
- Number: 1 check if "knew it" is under half of the B answers; 2–3 if half or more. Prefer the most central claims.
- Format: a missing-link or framework-transfer question (C types 2 and 3) with 4 options plus "Not sure". The correct option must depend on this book's specific version; someone who only knows the common version should choose wrong.
- Scoring: correct means Covered (verified); wrong or "Not sure" downgrades to "heard of it, never thought it through" and it is handled as a knowledge or thinking gap.
- If any check is downgraded, all unchecked "knew it" items become Covered (assumed): summarized, not cut. If all checks pass, unchecked items count as Covered (verified).
- Do not reveal answers during calibration; answers and scoring appear in the Step 3 gap map.
- A check that tests an author-specific reasoning step may also count toward the C quota.

**C. Thinking probes (2–4 questions, all multiple choice)**
Goal: find where the reader's reasoning stops and how many further steps the author takes. Choose two or three of these formats:

1. **Reasoning depth ladder**: take a core question of the book and give 3–4 answers of different depth (surface attribution, the author's surface explanation, the author's deeper mechanism, a reflection beyond the author such as the author's own blind spot). Ask which is closest to the reader's judgment. Word options by content, never label depth, shuffle order, never hint which is the author's.
2. **Framework transfer**: give a concrete situation outside the book (another event of the same period, or a real present-day phenomenon) and ask what the key error or mechanism is by the author's logic. The correct option is the author's transferable reasoning; distractors are common but shallow explanations; add "The author's logic does not apply here" as an exit for readers able to rebut.
3. **Missing link**: write out one of the author's reasoning chains, remove its most crucial step, offer 4 candidates. The missing step must be distinctive to the author, not a common-sense connection.
4. **Position strength** (replaces asking why the reader disagrees): for the one or two broadest or most contested claims, offer graded attitudes: holds / partly holds but hard to test (e.g., national-character explanations) / does not hold, a better explanation exists (write that explanation) / never thought about it. This separates "disagree" from "overstated", which B probes cannot.

Scoring: a surface option on the depth ladder, or a wrong framework-transfer answer, records a thinking gap. Choosing the "beyond the author" option means the reader is ahead of the author on that question: switch related passages to critical reading and aim annotations at the author's blind spots. "Partly holds" or "does not hold" on position strength records a view gap to be developed in annotations; "holds" on a contested claim makes that passage a Don't skip.

**D. Prediction prompt (1, optional, multiple choice)**: give the starting point of an argument or plot and 3–4 possible directions, one of which is the book's. Not asked during calibration; placed before the relevant chapter under the Predict marker, with the answer in the annotation after the passage.

**Adaptive rules**

Adjust each batch based on the previous one:
- **Topic layer all "unfamiliar" or "only heard the term"**: B down to 5–6, core claims and entry-level themes only; C uses missing-link and position-strength questions, not the depth ladder (low discrimination on a thin foundation); add all background cards.
- **Topic layer all "can explain and evaluate"**: B down to 5–6, counterintuitive and author-specific versions only; C up to 4, must include depth ladder and framework transfer.
- **First 4 B probes all "knew it"**: the next batch uses deeper claims closer to the author's specific wording; B′ checks at least 2.
- **First 4 B probes all "new"**: no more B questions; the gap is mainly knowledge, so shift to background cards and knowledge-gap processing; keep 2 C questions.
- **A section (beginning, middle, end) already has 2 "knew it" answers and one passed a check**: no more B questions for that section; its remaining claims count as Covered (assumed).
- **Goal is "get the gist"**: C down to 2, B′ checks only 1.
- **Goal is "learn how the author thinks" or "read critically"**: C at least 3, including a position-strength question.

**Calibration by type**

| Type | Adjustment |
|---|---|
| Popular science, introductions | B adds 1–2 model questions (given a phenomenon, which model explains it); topic layer tests prerequisites such as the math or statistics required |
| Practical, method | B options become: already use it / know it but don't use it / new / think it doesn't work; C becomes applicability questions: given a situation, does the method apply and why |
| Academic monograph | Topic layer tests the field's main schools and methods; C adds "which side of the scholarly debate does this book take" |
| History | C adds framework recognition: three or four explanations of one event; which is the author's, which does the reader accept |
| Biography, memoir | Position strength targets the subject's or author's self-narrative: credible / partly flattering / heavily constructed / never thought about it |
| Essays | B becomes per-piece interest and familiarity; no thinking probes, test preferences for form and language instead |
| Interviews, speeches | B tests the speaker's signature views; C uses position strength only |
| Philosophy | Topic layer must test key terms; C mainly missing-link questions |
| Literary fiction | No claim probes; post-reading mode tests recognition of narrative technique (given a passage, what is the effect of its point of view or handling of time); pre-reading mode tests only background and tolerance for difficulty |
| Idea-driven science fiction | Topic layer is the main instrument: one question per field the plot leans on (for *Blindsight*: philosophy of mind, neuroscience). "Only heard the term" or "unfamiliar" gets a background card and denser annotations at first use; no claim probes that would reveal plot |
| Genre fiction, web serials | Only ask whether read and which line the reader cares about (plot, romance, setting); no thinking probes |
| Poetry, drama | Topic layer tests allusion and prosody background; for translations, ask whether the original should be shown alongside |

### Step 3: Show the gap map and budget fit, allow corrections

In chat, give a compact table: probe, reader's answer, check result (verified, assumed, downgraded), gap kind, treatment; plus one or two sentences on the thinking gaps based on the C answers. If a probe's wording caused a misreading, say so and correct it. Reveal the B′ answers and briefly explain any downgrade.

Also give the budget fit:
- Total length, padding ratio
- Target retained length and retention rate from type, goal, and budget (Step 4 algorithm)
- Estimated reading time counted on the **whole reading load**: kept original text, summaries, guides, annotations, and front and back matter. In practice the added text is 25–35% of the total, so the old rule of thumb that annotations take 30% of the time is optimistic for heavily annotated books
- If the budget cannot hold every thinking gap and Don't skip passage, say so and offer: extend the budget / summarize all knowledge-gap passages / read only certain parts closely and the rest as skeleton

The gap map is the most important intermediate product. Ask the reader to confirm or correct it, again as multiple choice (confirm / correct some items / adjust budget), before processing.

### Step 4: Processing

**Budget allocation**

1. Take the type's base retention (Step 1 table); for mixed books, per chapter.
2. Adjust by goal:

| Goal | Retention factor | Emphasis |
|---|---|---|
| Master systematically | ×1.5–2 | Keep more knowledge-gap passages; add a glossary; 2–3 self-test questions at the end of each part |
| Grasp core ideas | ×0.7 | Skeleton and thinking gaps; almost all examples cut |
| Learn how the author thinks | ×1 | Keep reasoning chains as complete original text, never fragmented; one prediction prompt per part |
| Read critically | ×1.3 | Keep the author's evidence whole, never summarize on the author's behalf; heavier Limits and Counterarguments; 3 Don't skip passages |
| Get the gist | ×0.5 | Mostly skims; keep only the one or two most central thinking-gap passages in original |

3. Cap by time budget: available original length ≈ budget minutes × effective speed × 0.7 (the other 30% is for front matter, annotations, and skims). No cap for "unlimited".
4. Target retained length is the smaller of steps 2 and 3. If over budget, cut in this order, finishing each class before touching the next:
   1. Covered (verified)
   2. Repeated examples of the same point, build-up
   3. Covered (assumed) reduced to one line
   4. Knowledge-gap passages reduced to summary plus background card
   5. View-gap passages reduced to their core
   6. Thinking gaps and Don't skip passages are never cut; if still over budget, return to Step 3 and let the reader choose
5. No-cut types (literary fiction, poetry, drama, detective fiction, philosophy) are exempt from cutting; if the budget is short, recommend a selection of pieces or chapters with reasons, and never alter the selected parts.
6. **Allocate before writing specs.** Give every chapter a target in characters (or words) from its role: chapters that carry the book's central ideas or turning points get more, transitional action, travel and repeated set pieces get less. Record the table in `state.md`. Allocating after the fact does not work: the first draft of a spec always keeps too much, and trimming a finished book costs a second pass over every chapter.
7. **Check while writing.** After each chapter's spec, run the checker with the target; it prints the cumulative retention and flags overshoot:

```bash
python3 <skill-dir>/scripts/check_spec.py bespoke-work/<book-slug> --speed 300 --budget 360 --target 0.4
```

If the reader later relaxes the budget ("keep it if cutting would lose something important"), stop trimming the core passages and say what the final time is.

**Route spec file**

One file per chapter, `spec/chNNN.txt`, numbered like `text/chNNN.txt`. Paragraph numbers are the `i` in `[N.i]`:

```
T 罗夏 · 4                      chapter title for the table of contents
G 本章……                        chapter guide (fiction: previously, who is where, what to watch for)
R 1-2                           keep original paragraphs 1..2
S 3-14 船员们五次下到罗夏……       skim: summary replacing 3..14
K 15-18 second example of the same point   cut, with the reason
N 16 这就是盲视背后的神经学……      annotation after paragraph 16
H 22 说话的是萨沙……               plot or reading hint after paragraph 22
P 30 他会怎么做？                 prediction question before paragraph 30
F 16                            Don't skip flag before paragraph 16
```

Every paragraph with text is covered by exactly one R, S or K range. N and H may point inside an S or K range; they then appear after that summary, so write them to make sense next to the summary. `check_spec.py` reports gaps, overlaps, misplaced flags and the budget. A filled example is in the repository under `examples/blindsight/`.

**Cutting standards (general)**
- In narrative books, prefer Skim over Cut: a skim that says what happened keeps the plot continuous, a cut line leaves a hole. Use Cut for material with no plot content (description, repeated set pieces, filler).
- Keep: passages matching knowledge, view, and thinking gaps; the author's distinctive reasoning steps; transferable patterns of thought.
- Cut: second and third examples of the same point; retellings of films or news; repeated arguments and slogans; verified-covered background; build-up.
- Mandatory Don't skip: keep one to three passages that oppose the reader's position or give the author's strongest counterevidence to it, so the tool never merely confirms existing beliefs. If the reader chose no "Disagree", select from position-strength answers and the author's self-contradictions.

**Annotation standards (general)**
- Point out mechanisms and what transfers; do not restate content.
- Check anecdotes, quotations, and dates the author cites. Flag doubtful ones with wording such as "commonly attributed" or "hard to verify"; never invent sources.
- Where the author explains only half a mechanism, complete it with the corresponding scholarship.
- At view gaps, name the substance of the disagreement (e.g., consequentialism versus teleology) and find the author's own inconsistency on the same question.
- Fold the author's own notes into annotations at the passages they explain, and say that the point comes from the author. In pre-reading mode use only what the text has revealed so far: authors' notes often discuss the ending.
- No leading annotations. A note that says "remember this judgment" about a claim the book will later overturn is a spoiler by hint. Explain what the reader needs now and stop.
- Keep annotations short. Most should be one to three sentences; the added text counts against the reading budget.

**Additional processing by type**

- **Popular science, introductions**
  - Concept dependency map of core concepts and prerequisites, in front matter.
  - Cut scientist anecdotes and dramatized discovery stories; keep the design logic of key experiments.
  - Outdated check: conclusions overturned, revised, or failed to replicate since publication are flagged with the current mainstream view (verify by search if available; never assert from memory).
- **Practical, method, business, self-help**
  - A method card per method: steps, conditions, evidence strength (research / case / author experience only), failure scenarios.
  - Flag survivorship bias and unsupported assertions.
  - Keep only the one case story that best shows the conditions.
- **Academic monographs, textbooks**
  - Scholarly position card: the debate the book answers, opposing schools, later influence.
  - Cut literature-review chapters according to the topic layer; never cut method chapters.
  - Keep representative exercises and worked examples, tagged with their core concept.
- **History**
  - Separate fact from interpretation; annotations say explicitly which sentence is the author's interpretation.
  - Timeline card in front matter; chronicle detail can be cut from the body.
  - Name the author's historiographical approach and other major explanations of the same events.
- **Biography, memoir**
  - Key decision table: time, decision, reason given, possible other reasons.
  - Flag self-flattery, post hoc rationalization, and narrative gaps (periods conspicuously skipped).
  - Author-level chapter weighted more heavily.
- **Essays, collections**
  - Select by piece: keep or cut whole pieces, never sentences, to protect language.
  - Each kept piece gets one line on why it is worth reading; each cut piece's theme goes in the cut log.
- **Interviews, speeches**: cut pleasantries, repeated questions, and repeated answers; where one view recurs across pieces, keep the fullest statement and cross-reference the rest.
- **Philosophy**
  - Systematic: glossary (with the translation's rendering and the original term), argument step map, one-sentence version of each difficult point.
  - Aphorisms, fragments, dialogues: no step map; a thematic index (entries grouped by theme) marking tensions and contradictions between entries.
- **Detective fiction**: structure and puzzle breakdown only in post-reading mode.
- **Science fiction, fantasy**
  - Pre-reading, full: no cuts; chapter guides, hints and annotations only, no spoilers.
  - Pre-reading, trimmed (when the reader sets a budget): the book is cut, but every removed stretch of plot becomes a Skim that says what happened, so the story never breaks. Idea passages, turning points and form-carrying passages are kept whole. Front matter: how-to-use page with the marker table and the estimated time, one background card per unfamiliar field, a character and term table limited to what the opening chapters reveal. Back matter: an "after reading" page with the ending discussion, marked at the top as containing the ending.
  - Post-reading:
    - Setting consequence table: core setting; first- and second-order consequences the author draws; directions the author left unexplored (clearly marked as AI extrapolation).
    - Reskin test: replace the setting with a realistic background; if the story barely changes, point out the setting is only a skin.
  - Form protection in every mode: passages where form carries meaning (e.g., style changing with a character's state) are uncuttable.
- **Literary fiction, dense classics**
  - Reader aids, all spoiler-free in pre-reading mode:
    - Character table with every name form the book uses. Russian novels call one person by full name, name and patronymic, surname and several diminutives; Latin American family sagas reuse the same names across generations. List each person once with all forms, their role and relations, as far as the reader has read.
    - Relationship map and family tree, kept to what has been revealed.
    - Chapter guide: previously, who is where, what to watch for.
    - In-text hints where the narration jumps in time, switches narrator or refers to someone by a new name.
  - Pre-reading background card and difficulty hints (how time jumps work, a caution about narrator reliability, without conclusions).
  - Post-reading: point of view and time structure analysis, image system table (image, locations, shifts in meaning), relation of form to theme.
  - No cuts by default; if the budget is short, recommend a selection as in budget rule 5. If the reader explicitly asks for a trimmed version, use the trimmed mode above and tell them what kind of passage is lost.
- **Genre fiction, web serials**
  - Main-line map: main and side plots, with each chapter's line.
  - Skip markers: filler chapters, repetitive fights or daily life, side plots unrelated to the main line.
  - Keep complete scenes of character change and main-line turns.
- **Poetry, drama**
  - Poetry: allusion and image notes; original alongside translations if requested; notes on prosody or form.
  - Drama: character relationship map, conflict structure (conflict progression per act), notes on key lines.

### Step 5: Output

**Ask for the target reader app in batch 0 or the last batch. Default output is a trimmed EPUB**: everyday reading happens in a reader app, and switching between an HTML page and the book adds friction. Output HTML only if the reader explicitly wants close study on a computer (annotations collapsed in `<details>`, light and dark themes, readable at phone width, no browser storage).

**Preview**: after the first part of the book (or about a fifth of it), build and send a preview EPUB. Readers find format problems (locators, marker style, guide length) faster in their own reader app than in a description, and fixing them early saves rework.

**EPUB structure** (nonfiction; for fiction use the front and back matter listed under Step 4, fiction)
- Front matter:
  - How to use (marker legend, suggested reading order, estimated time)
  - Overview and gap map (title, type, goal, budget, padding ratio, retention, gap table, check results, thinking-gap judgment)
  - Background cards (one per "unfamiliar" topic item)
  - Type cards (concept map, timeline, scholarly position, method card index, main-line map, character map, as the type requires)
  - One-page skeleton
  - "You will want to skip these, but shouldn't" list
- Body: in the book's original order, one chapter per piece.
  - Locators only where something was done (see Locators)
  - Skim, Cut, Note, Predict, and Don't skip markers as in the marker table
  - For "master systematically", Self-test questions at the end of each part, answers at the start of the next
  - A piece cut entirely still gets a chapter containing only its cut line
- Back matter: author level, present-day mapping, limits and counterarguments, idea thread tags, cut log (generated from the spec). Method books also get all method cards.

**Reader app compatibility**
- Apps with limited popup-footnote and CSS support (e.g., WeChat Read, some Kindle conversions): annotations become indented small text after the paragraph, distinguished by the text marker so they remain recognizable if CSS fails.
- Apps supporting EPUB3 popup footnotes (e.g., Apple Books): annotations may use `epub:type="noteref"` footnotes.

**Build**: write front and back matter pages as plain files in `front/` (`# ` title, `## ` heading, `|`-separated table rows, one paragraph per line; names sorted, files starting with `zz` go after the last chapter), then:

```bash
python3 <skill-dir>/scripts/build_epub.py bespoke-work/<book-slug> output/<file>.epub --title "<book title>" --lang zh
```

The script carries over the original cover, stylesheets, images and the footnotes of kept paragraphs, places each chapter guide after the heading and epigraph, writes `nav.xhtml` and `toc.ncx`, and checks that every document is well formed. Afterwards render one or two chapters (a headless browser is enough) and look at them.

**Title and cover**: the book keeps its own title and cover. Do not add "bespoke", "量体裁书版" or similar to the title inside the book; strip marketing text some editions put in the title field. The file name may carry a marker if the reader wants one; by default use the plain title.

**Delivery**: save as `<book title>.epub` in the output location described in Host conventions and send it to the reader. **Never publish it online** (no public links, hosted pages, or repositories): the output contains the book's text and is a personal file only.

## How to write the back-matter chapters

- **Author level**: not what the book says, but where these ideas come from. Analyze how background and experience were promoted into principles, how the writing situation shaped the tone, the book's real axis of values, its self-image and contradictions, its rare self-doubt. Each point ends with a "generalizable trait" that applies to other authors.
- **Present-day mapping**: test the book's mechanisms against real, verifiable present-day phenomena; never invent cases.
- **Limits and counterarguments**: one per core claim, covering conceptual confusion, half-explained mechanisms, survivorship bias, evidence quality, and testable period judgments.
- **Idea thread tags**: a table of tag, location in the book, directions it connects to.

## Annotation style

Analytical, restrained, complete sentences. Stand above the content and analyze why the author thinks this way rather than restating content point by point. No dashes, no conversational filler, no jokes. Each annotation states its core judgment without walking through every supporting detail.

## Revision mode

When a reader brings back an earlier version with complaints ("still too long", "not enough help", "the cover is gone"), do not rerun the full calibration. Ask one batch about the changes only (new retention, hint depth, extras, whether to redo read chapters), keep what the reader did not question, and rebuild. If the earlier specs are gone, extract the book again and start from the state file or the reader's summary of past decisions.

## Feedback loop

After the reader finishes, if willing, collect with one multiple-choice batch: which kinds of annotation helped, where they stopped, whether predictions were right, which probe was inaccurate, actual time versus estimate (faster / as expected / slower), whether cuts were too heavy or too light. Use this to correct the gap judgment and default speed, and to improve probe design, type rules, and this skill for the next book.

## Never

- Grade the reader or evaluate their overall intellectual level.
- Start cutting before calibration and a confirmed gap map.
- Insert open-ended questions into calibration.
- Cut an unverified "knew it"; only summarize it.
- Cut thinking gaps or Don't skip passages to fit the budget; budget conflicts go to the reader.
- Cut or alter literary fiction, poetry, drama, detective fiction, or philosophy; only recommend selections when the budget is short.
- Mix AI extrapolation into the author's views.
- Spoil anything in pre-reading mode.
- Publish an output containing the book's text online.
- Put a locator before every kept paragraph, or rename the book inside the EPUB.
- Let a hint or annotation reveal what the reader has not reached, in pre-reading mode.

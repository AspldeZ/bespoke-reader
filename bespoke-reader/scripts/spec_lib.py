"""Shared helpers for check_spec.py and build_epub.py.

Route spec format, one file per chapter: WORKDIR/spec/chNNN.txt (NNN matches text/chNNN.txt).
Paragraph numbers are the i in [N.i]. One instruction per line:

  T title               chapter title used in the table of contents
  G text                chapter guide, shown after the heading and epigraph
  R a-b                 keep original paragraphs a..b
  S a-b summary         skim: replace paragraphs a..b with a summary
  K a-b reason          cut paragraphs a..b, shown as a one-line cut marker
  N i text              annotation after paragraph i
  H i text              plot or reading hint after paragraph i
  P i text              prediction question before paragraph i
  F i                   "don't skip" flag before paragraph i
  # anything            comment

Every paragraph with text must be covered by exactly one R, S or K range.
N and H may point into an S or K range; they are then shown after that summary.
"""
import re, os, json, glob

LINE = re.compile(r'^([TGRSKNHPF#])(?:\s+(.*))?$')


def load(work):
    paras = json.load(open(os.path.join(work, 'paras.json'), encoding='utf-8'))
    meta = json.load(open(os.path.join(work, 'meta.json'), encoding='utf-8'))
    return paras, meta


def spec_files(work):
    out = []
    for f in sorted(glob.glob(os.path.join(work, 'spec', 'ch*.txt'))):
        m = re.search(r'ch(\d+)\.txt$', f)
        if m:
            out.append((int(m.group(1)), f))
    return out


def parse(path):
    spec = {'title': '', 'guide': '', 'ranges': [], 'after': {}, 'before': {}, 'flags': set(), 'errors': []}
    for no, line in enumerate(open(path, encoding='utf-8'), 1):
        line = line.rstrip('\n')
        if not line.strip():
            continue
        m = LINE.match(line)
        if not m:
            spec['errors'].append(f'line {no}: cannot parse: {line[:40]}')
            continue
        op, rest = m.group(1), (m.group(2) or '').strip()
        if op == '#':
            continue
        if op == 'T':
            spec['title'] = rest
        elif op == 'G':
            spec['guide'] = rest
        elif op in 'RSK':
            r = re.match(r'(\d+)-(\d+)\s*(.*)', rest)
            if not r:
                spec['errors'].append(f'line {no}: expected "{op} a-b": {line[:40]}')
                continue
            spec['ranges'].append((op, int(r.group(1)), int(r.group(2)), r.group(3)))
        elif op in 'NH':
            r = re.match(r'(\d+)\s+(.*)', rest)
            if not r:
                spec['errors'].append(f'line {no}: expected "{op} i text"')
                continue
            spec['after'].setdefault(int(r.group(1)), []).append((op, r.group(2)))
        elif op == 'P':
            r = re.match(r'(\d+)\s+(.*)', rest)
            if r:
                spec['before'].setdefault(int(r.group(1)), []).append(r.group(2))
        elif op == 'F':
            if rest.isdigit():
                spec['flags'].add(int(rest))
            else:
                spec['errors'].append(f'line {no}: expected "F i"')
    spec['ranges'].sort(key=lambda x: x[1])
    return spec


def check(spec, paras):
    """Return (coverage map, list of problems)."""
    n = len(paras)
    cov, problems = {}, list(spec['errors'])
    for op, a, b, t in spec['ranges']:
        if a < 1 or b > n or a > b:
            problems.append(f'range {op} {a}-{b} outside 1-{n}')
            continue
        if op != 'R' and not t:
            problems.append(f'{op} {a}-{b} has no summary or reason')
        for i in range(a, b + 1):
            if i in cov:
                problems.append(f'paragraph {i} covered twice')
            cov[i] = op
    missing = [i for i in range(1, n + 1) if i not in cov and (paras[i - 1]['text'] or paras[i - 1].get('imgs'))]
    if missing:
        problems.append('not covered: ' + compact(missing))
    for i in list(spec['after']) + list(spec['before']) + list(spec['flags']):
        if i < 1 or i > n:
            problems.append(f'note or flag on paragraph {i}, outside 1-{n}')
    for i in list(spec['before']) + list(spec['flags']):
        if cov.get(i) != 'R':
            problems.append(f'P/F on paragraph {i}, which is not kept (R); it will not show')
    return cov, problems


def compact(nums):
    out, start, prev = [], None, None
    for x in nums:
        if start is None:
            start = prev = x
        elif x == prev + 1:
            prev = x
        else:
            out.append(f'{start}-{prev}' if start != prev else str(start))
            start = prev = x
    if start is not None:
        out.append(f'{start}-{prev}' if start != prev else str(start))
    return ','.join(out)


def stats(spec, paras):
    orig = sum(len(p['text']) for p in paras)
    keep = 0
    added = len(spec['guide']) + len(spec['title'])
    for op, a, b, t in spec['ranges']:
        if op == 'R':
            keep += sum(len(paras[i - 1]['text']) for i in range(a, b + 1) if 0 < i <= len(paras))
        else:
            added += len(t)
    added += sum(len(t) for v in spec['after'].values() for _, t in v)
    added += sum(len(t) for v in spec['before'].values() for t in v)
    return orig, keep, added


def page_text_len(path):
    """Length of a front or back matter page written in the simple page markup."""
    return sum(len(l.lstrip('#| ').replace('|', '')) for l in open(path, encoding='utf-8') if l.strip())

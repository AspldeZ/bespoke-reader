#!/usr/bin/env python3
"""Check route specs and report the reading budget.

Usage: python3 check_spec.py WORKDIR [--speed 300] [--budget MINUTES] [--target 0.4]

--speed    effective reading speed in characters (CJK) or words per minute
--budget   time budget in minutes; the report says whether the book fits
--target   target retention of original text (0.4 = 40%), compared per chapter
           and cumulatively, so overshoot is caught while specs are being written

Every spec is checked for coverage, overlaps and misplaced notes. Reading time
counts everything the reader will read: kept original text, summaries, guides,
annotations and the front and back matter pages in WORKDIR/front/.
"""
import sys, os, glob, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_lib as S


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('work')
    ap.add_argument('--speed', type=float, default=300)
    ap.add_argument('--budget', type=float)
    ap.add_argument('--target', type=float)
    a = ap.parse_args()
    paras, meta = S.load(a.work)
    T = K = A = 0
    bad = False
    for n, path in S.spec_files(a.work):
        ch = paras.get(str(n))
        if not ch:
            print(f'ch{n:03d}: no such chapter in paras.json')
            bad = True
            continue
        spec = S.parse(path)
        _, problems = S.check(spec, ch['paras'])
        orig, keep, added = S.stats(spec, ch['paras'])
        T, K, A = T + orig, K + keep, A + added
        line = f'ch{n:03d} {spec["title"][:16]:<16} orig {orig:>7} keep {keep:>7} ({keep / max(orig, 1):4.0%}) added {added:>6}'
        if a.target:
            line += f'  cumulative {K / max(T, 1):4.0%}' + ('  OVER' if K / max(T, 1) > a.target * 1.15 else '')
        print(line)
        for p in problems:
            print('   !', p)
            bad = True
    front = sum(S.page_text_len(f) for f in glob.glob(os.path.join(a.work, 'front', '*.txt')))
    total = K + A + front
    minutes = total / a.speed
    print(f'\nALL orig {T} keep {K} ({K / max(T, 1):.0%}) summaries+notes {A} front/back pages {front}')
    print(f'reading load {total} at {a.speed:g}/min = {minutes / 60:.1f} h')
    if a.budget:
        diff = minutes - a.budget
        print(f'budget {a.budget / 60:.1f} h: ' + ('fits' if diff <= 0 else f'over by {diff:.0f} min, cut about {diff * a.speed:.0f} characters'))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()

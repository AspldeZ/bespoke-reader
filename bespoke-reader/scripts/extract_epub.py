#!/usr/bin/env python3
"""Extract an EPUB into numbered paragraphs for Bespoke Reader.

Usage: python3 extract_epub.py book.epub WORKDIR

Writes into WORKDIR:
  orig/            the unpacked EPUB (cover, styles, images are reused by build_epub.py)
  text/chNNN.txt   one file per spine item, every paragraph prefixed with [N.i],
                   footnotes listed separately at the end
  paras.json       paragraph HTML, plain text and footnotes, used by build_epub.py
  meta.json        title, author, language, cover, stylesheets
  index.tsv        chapter number, paragraph count, character count, opening words

Chapter numbers follow the spine order and never skip, so chNNN.txt,
spec/chNNN.txt and paras.json always agree. Footnotes are detected from
in-file links (a link whose target comes after it) and from epub:type
footnote/endnote, and are kept out of the paragraph list.
"""
import sys, os, re, json, html, zipfile, posixpath
from xml.etree import ElementTree as ET

XHTML = 'http://www.w3.org/1999/xhtml'
EPUB = 'http://www.idpf.org/2007/ops'
ET.register_namespace('', XHTML)
ET.register_namespace('epub', EPUB)
LEAF = {'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'table', 'blockquote', 'pre', 'ul', 'ol', 'dl', 'figure', 'hr'}
CONTAINER = {'div', 'section', 'article', 'aside', 'main', 'header', 'footer', 'nav', 'body'}
NOTE_TYPES = {'footnote', 'endnote', 'rearnote', 'note'}


def local(tag):
    return tag.rsplit('}', 1)[-1] if isinstance(tag, str) else ''


def plain(el):
    parts = []
    def walk(e):
        if local(e.tag) == 'br':
            parts.append('\n')
        if e.text:
            parts.append(e.text)
        for c in e:
            walk(c)
            if c.tail:
                parts.append(c.tail)
    walk(el)
    t = ''.join(parts)
    t = re.sub(r'[ \t\r\f\v　\xa0]+', ' ', t)
    return re.sub(r' *\n *', '\n', t).strip()


def has_block(el):
    return any(local(d.tag) in LEAF | CONTAINER for d in el.iter() if d is not el)


def blocks_of(body):
    out = []
    def walk(e):
        for c in e:
            t = local(c.tag)
            if t in LEAF:
                out.append(c)
            elif t in CONTAINER:
                if has_block(c):
                    walk(c)
                else:
                    out.append(c)
            elif t in ('img', 'svg', 'image'):
                out.append(c)
    walk(body)
    return out


def main(src, work):
    os.makedirs(work, exist_ok=True)
    z = zipfile.ZipFile(src)
    z.extractall(os.path.join(work, 'orig'))
    opf_path = ET.fromstring(z.read('META-INF/container.xml')).find('.//{*}rootfile').get('full-path')
    opf = ET.fromstring(z.read(opf_path))
    base = posixpath.dirname(opf_path)
    manifest = {}
    for it in opf.find('{*}manifest'):
        manifest[it.get('id')] = {
            'href': posixpath.normpath(posixpath.join(base, it.get('href').split('#')[0])),
            'type': it.get('media-type', ''), 'props': it.get('properties', '')}
    md = opf.find('{*}metadata')
    dc = lambda n: (md.findtext('{http://purl.org/dc/elements/1.1/}' + n) or '').strip()
    cover = None
    for m in md.iter():
        if local(m.tag) == 'meta' and m.get('name') == 'cover' and m.get('content') in manifest:
            cover = manifest[m.get('content')]['href']
    for it in manifest.values():
        if 'cover-image' in it['props']:
            cover = it['href']
    if cover and not cover.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
        cover = None
    meta = {'title': dc('title'), 'author': dc('creator'), 'language': dc('language') or 'und',
            'cover': cover, 'css': [v['href'] for v in manifest.values() if v['type'] == 'text/css']}
    spine = [r.get('idref') for r in opf.find('{*}spine')]

    data = {}
    index = []
    os.makedirs(os.path.join(work, 'text'), exist_ok=True)
    for n, idref in enumerate(spine, 1):
        item = manifest.get(idref)
        if not item or 'html' not in item['type']:
            continue
        path = item['href']
        raw = z.read(path).decode('utf-8', 'ignore')
        try:
            root = ET.fromstring(re.sub(r'<!DOCTYPE[^>]*>', '', raw))
        except ET.ParseError:
            print('warning: not well-formed XHTML, skipped:', path)
            continue
        body = root.find('{%s}body' % XHTML)
        if body is None:
            body = root.find('.//{*}body')
        if body is None:
            continue
        order = {id(e): i for i, e in enumerate(body.iter())}
        ids = {e.get('id'): e for e in body.iter() if e.get('id')}
        note_targets = set()
        for a in body.iter():
            href = a.get('href') or ''
            if local(a.tag) == 'a' and '#' in href:
                f, frag = href.split('#', 1)
                if (not f or posixpath.basename(f) == posixpath.basename(path)) and frag in ids:
                    if order[id(ids[frag])] > order[id(a)]:
                        note_targets.add(frag)
        for e in body.iter():
            if (e.get('{%s}type' % EPUB) or '') in NOTE_TYPES and e.get('id'):
                note_targets.add(e.get('id'))
        paras, notes = [], {}
        for b in blocks_of(body):
            inner_ids = {e.get('id') for e in b.iter() if e.get('id')}
            hit = inner_ids & note_targets
            etype = b.get('{%s}type' % EPUB) or ''
            if hit or etype in NOTE_TYPES:
                notes[sorted(hit)[0] if hit else b.get('id')] = ET.tostring(b, encoding='unicode')
                continue
            imgs = [e.get('src') or e.get('{http://www.w3.org/1999/xlink}href') for e in b.iter()
                    if local(e.tag) in ('img', 'image')]
            imgs = [posixpath.normpath(posixpath.join(posixpath.dirname(path), s)) for s in imgs if s]
            paras.append({'html': ET.tostring(b, encoding='unicode'), 'text': plain(b),
                          'tag': local(b.tag), 'cls': b.get('class', ''), 'imgs': imgs})
        while paras and not paras[-1]['text'] and not paras[-1]['imgs']:
            paras.pop()
        if not paras:
            continue
        for i, p in enumerate(paras, 1):
            p['id'] = f'{n}.{i}'
        data[n] = {'file': path, 'paras': paras, 'notes': notes}
        with open(os.path.join(work, 'text', f'ch{n:03d}.txt'), 'w', encoding='utf-8') as f:
            for p in paras:
                f.write(f"[{p['id']}] {p['text'] or ('(image)' if p['imgs'] else '')}\n")
            if notes:
                f.write('--- footnotes ---\n')
                for k, v in notes.items():
                    f.write(f'{k}: {plain(ET.fromstring(v))}\n')
        chars = sum(len(p['text']) for p in paras)
        index.append((f'ch{n:03d}', len(paras), chars, paras[0]['text'][:30].replace('\n', ' ')))
    json.dump(data, open(os.path.join(work, 'paras.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    json.dump(meta, open(os.path.join(work, 'meta.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    with open(os.path.join(work, 'index.tsv'), 'w', encoding='utf-8') as f:
        f.write(f"# {meta['title']}\n")
        for r in index:
            f.write('\t'.join(map(str, r)) + '\n')
    total = sum(r[2] for r in index)
    print(f"{meta['title']}: {len(index)} files, {total} characters")
    for r in index:
        print(*r, sep='\t')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])

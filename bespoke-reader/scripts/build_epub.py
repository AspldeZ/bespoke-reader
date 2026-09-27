#!/usr/bin/env python3
"""Build the tailored EPUB from route specs.

Usage: python3 build_epub.py WORKDIR OUT.epub [--title T] [--author A] [--lang zh|en]
                             [--locators marked|all|none]

Reads WORKDIR/paras.json, meta.json, orig/ (from extract_epub.py), spec/chNNN.txt
(see spec_lib.py) and front/*.txt. Front pages are sorted by file name; files whose
name starts with "zz" go after the last chapter as back matter.

Front page markup: "# " title, "## " heading, lines starting with "|" form a table
(first row is the header), every other non-empty line is a paragraph.

The original cover, stylesheets, images and footnotes are carried over. The book
title defaults to the original title with bracketed marketing text removed; pass
--title to set it. Kept paragraphs carry no locator unless they have a note, a hint,
a prediction or a flag (--locators marked, the default).
"""
import sys, os, re, html, json, zipfile, uuid, datetime, argparse, posixpath, glob
from xml.etree import ElementTree as ET
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_lib as S

esc = html.escape
MARK = {
    'zh': {'guide': '〔导读〕', 'skim': '〔略读〕', 'cut': '〔删去 {n} 段：{r}〕', 'note': '〔批注〕',
           'hint': '〔提示〕', 'predict': '〔先想〕', 'flag': '〔别跳〕下面这段是本章的关键，请放慢读。',
           'toc': '目录', 'cover': '封面', 'break': '＊　＊　＊'},
    'en': {'guide': '[Guide]', 'skim': '[Skim] ', 'cut': '[Cut {n} ¶: {r}]', 'note': '[Note] ',
           'hint': '[Hint] ', 'predict': '[Predict] ', 'flag': "[Don't skip] The next passage is the key to this chapter; read it slowly.",
           'toc': 'Contents', 'cover': 'Cover', 'break': '*   *   *'},
}
EXTRA_CSS = '''
p.bn, p.bh, p.bp { font-size: 0.86em; line-height: 1.6em; margin: 0.3em 0 0.8em 1.2em; padding: 0.2em 0 0.2em 0.6em; border-left: 3px solid #b08a4a; color: #555; text-indent: 0; }
p.bh { border-left-color: #4a7ab0; }
p.bp { border-left-color: #5a9a5a; margin: 0.8em 0 0.3em 1.2em; }
p.skim { font-size: 0.9em; line-height: 1.6em; margin: 0.6em 0 0.8em 0; padding: 0.3em 0.6em; background: #f3efe6; color: #444; text-indent: 0; }
span.mk { font-weight: bold; color: #8a6420; }
p.bh span.mk { color: #2f5f93; }
p.bp span.mk { color: #3a7a3a; }
span.loc { font-size: 0.7em; color: #999; margin-right: 0.3em; font-family: sans-serif; }
div.guide { margin: 1em 0 1.4em 0; padding: 0.5em 0.8em; border: 1px solid #d9cfb8; background: #faf7f0; }
p.gt { font-weight: bold; color: #8a6420; margin: 0; text-indent: 0; }
p.gp { font-size: 0.92em; line-height: 1.65em; margin: 0.2em 0 0 0; text-indent: 0; color: #333; }
p.flag { font-size: 0.85em; color: #a33; font-weight: bold; margin: 0.8em 0 0.2em 0; text-indent: 0; }
p.brk { text-align: center; color: #999; margin: 0.8em 0; text-indent: 0; }
p.chh { font-size: 0.85em; color: #999; text-indent: 0; margin: 0.5em 0 1.5em 0; font-family: sans-serif; }
div.tn { margin-top: 2em; font-size: 0.85em; color: #555; }
h1.fm { font-size: 1.5em; margin: 1em 0 1em 0; }
h2.fm { font-size: 1.15em; margin: 1.2em 0 0.5em 0; color: #8a6420; }
p.fm { text-indent: 2em; margin: 0 0 0.5em 0; line-height: 1.7em; }
table.fm { border-collapse: collapse; width: 100%; font-size: 0.9em; margin: 0.5em 0 1em 0; }
table.fm td, table.fm th { border: 1px solid #ccc; padding: 0.3em 0.4em; vertical-align: top; text-align: left; }
@media (prefers-color-scheme: dark) {
 p.bn, p.bh, p.bp { color: #bbb; } p.skim { background: #2a2722; color: #ccc; }
 div.guide { background: #24211c; border-color: #4a4336; } p.gp { color: #ddd; }
}
'''


def page(title, inner, css, lang):
    links = ''.join(f'<link rel="stylesheet" type="text/css" href="../{c}"/>' for c in css)
    return (f'<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n'
            f'<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="{lang}" lang="{lang}">\n'
            f'<head><meta charset="utf-8"/><title>{esc(title)}</title>{links}</head>\n<body class="calibre">\n{inner}\n</body></html>')


def front_page(path):
    out, title, tbl = [], '', []
    def flush():
        nonlocal tbl
        if tbl:
            rows = [[c.strip() for c in r.strip().strip('|').split('|')] for r in tbl]
            s = '<table class="fm"><tr>' + ''.join(f'<th>{esc(c)}</th>' for c in rows[0]) + '</tr>'
            for r in rows[1:]:
                s += '<tr>' + ''.join(f'<td>{esc(c)}</td>' for c in r) + '</tr>'
            out.append(s + '</table>')
            tbl = []
    for l in open(path, encoding='utf-8').read().split('\n'):
        if l.startswith('|'):
            tbl.append(l)
            continue
        flush()
        if not l.strip():
            continue
        if l.startswith('# '):
            title = l[2:]
            out.append(f'<h1 class="fm">{esc(title)}</h1>')
        elif l.startswith('## '):
            out.append(f'<h2 class="fm">{esc(l[3:])}</h2>')
        else:
            out.append(f'<p class="fm">{esc(l)}</p>')
    flush()
    return title or os.path.basename(path), '\n'.join(out)


def render_chapter(n, spec, ch, M, locators, img_map):
    paras, fnotes = ch['paras'], ch['notes']
    cov, _ = S.check(spec, paras)
    rng = {}
    for op, a, b, t in spec['ranges']:
        for i in range(a, b + 1):
            rng[i] = (op, a, b, t)
    classes = [p['cls'] for p in paras if p['tag'] == 'p' and len(p['text']) > 40]
    body_cls = max(set(classes), key=classes.count) if classes else None
    out, used_notes = [], []
    state = {'guide': not spec['guide'], 'brk': True}

    def guide():
        if not state['guide']:
            out.append(f'<div class="guide"><p class="gt">{M["guide"]}</p><p class="gp">{esc(spec["guide"])}</p></div>')
            state['guide'] = True

    def notes_after(i):
        for op, t in spec['after'].get(i, []):
            c, mk = ('bn', M['note']) if op == 'N' else ('bh', M['hint'])
            out.append(f'<p class="{c}"><span class="mk">{mk}</span>{esc(t)}</p>')

    def loc(label):
        return f'<span class="loc">[{label}]</span>' if locators != 'none' else ''

    if paras and paras[0]['tag'] not in ('h1', 'h2', 'h3') and spec['title']:
        out.append(f'<p class="chh">{esc(spec["title"])}</p>')
    done = set()
    for i, p in enumerate(paras, 1):
        if i not in rng:
            if not p['text'] and not p['imgs'] and not state['brk']:
                out.append(f'<p class="brk">{M["break"]}</p>')
                state['brk'] = True
            continue
        op, a, b, t = rng[i]
        if op == 'R':
            is_body = (p['tag'] == 'p' and (body_cls is None or p['cls'] == body_cls) and len(p['text']) > 0)
            if not state['guide'] and (is_body or p['imgs']):
                guide()
            if not p['text'] and not p['imgs']:
                if not state['brk']:
                    out.append(f'<p class="brk">{M["break"]}</p>')
                    state['brk'] = True
                continue
            for q in spec['before'].get(i, []):
                out.append(f'<p class="bp"><span class="mk">{M["predict"]}</span>{esc(q)}</p>')
            if i in spec['flags']:
                out.append(f'<p class="flag">{M["flag"]}</p>')
            h = p['html']
            for nid in re.findall(r'href="[^"#]*#([^"]+)"', h):
                if nid in fnotes:
                    used_notes.append(nid)
            h = re.sub(r'href="[^"#]*#([^"]+)"', lambda m: f'href="#{m.group(1)}"' if m.group(1) in fnotes else '', h)
            for src, new in img_map.items():
                h = re.sub(r'(src|href)="[^"]*' + re.escape(posixpath.basename(src)) + '"', rf'\1="../{new}"', h)
            marked = i in spec['after'] or i in spec['flags'] or i in spec['before']
            if (locators == 'all' or (locators == 'marked' and marked)):
                h = re.sub(r'^(<[a-z0-9]+\b[^>]*>)', lambda m: m.group(1) + loc(i), h, count=1)
            out.append(h)
            notes_after(i)
            state['brk'] = False
        else:
            if (a, b) in done:
                continue
            done.add((a, b))
            guide()
            label = f'{a}' if a == b else f'{a}–{b}'
            if op == 'S':
                out.append(f'<p class="skim">{loc(label)}<span class="mk">{M["skim"]}</span>{esc(t)}</p>')
            else:
                cnt = sum(1 for j in range(a, b + 1) if paras[j - 1]['text'])
                out.append(f'<p class="skim">{loc(label)}<span class="mk">{esc(M["cut"].format(n=cnt, r=t))}</span></p>')
            for j in range(a, b + 1):
                notes_after(j)
            state['brk'] = False
    guide()
    if used_notes:
        out.append('<div class="tn"><hr/>')
        for nid in dict.fromkeys(used_notes):
            out.append(re.sub(r'href="[^"#]*#', 'href="#', fnotes[nid]))
        out.append('</div>')
    return '\n'.join(out)


def clean_title(t):
    return re.sub(r'\s*[（(【\[].*?[）)】\]]\s*', '', t).strip() or t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('work')
    ap.add_argument('out')
    ap.add_argument('--title')
    ap.add_argument('--author')
    ap.add_argument('--lang', choices=['zh', 'en'], default='zh')
    ap.add_argument('--locators', choices=['marked', 'all', 'none'], default='marked')
    a = ap.parse_args()
    W = a.work
    paras, meta = S.load(W)
    M = MARK[a.lang]
    title = a.title or clean_title(meta['title'])
    author = a.author or meta['author']
    lang = meta['language'] or ('zh-CN' if a.lang == 'zh' else 'en')
    orig = os.path.join(W, 'orig')
    css = [f'css/{i}_{posixpath.basename(c)}' for i, c in enumerate(meta['css'])] + ['css/extra.css']

    specs = S.spec_files(W)
    imgs = set()
    for n, path in specs:
        spec = S.parse(path)
        cov, _ = S.check(spec, paras[str(n)]['paras'])
        for i, p in enumerate(paras[str(n)]['paras'], 1):
            if cov.get(i) == 'R':
                imgs.update(p['imgs'])
    img_map = {src: f'images/{k}_{posixpath.basename(src)}' for k, src in enumerate(sorted(imgs))}

    items = []
    fronts = sorted(glob.glob(os.path.join(W, 'front', '*.txt')))
    for fp in [f for f in fronts if not os.path.basename(f).startswith('zz')]:
        t, inner = front_page(fp)
        items.append(('f_' + os.path.basename(fp)[:-4], t, page(t, inner, css, lang)))
    for n, path in specs:
        spec = S.parse(path)
        t = spec['title'] or f'ch{n:03d}'
        items.append((f'c{n:03d}', t, page(t, render_chapter(n, spec, paras[str(n)], M, a.locators, img_map), css, lang)))
    for fp in [f for f in fronts if os.path.basename(f).startswith('zz')]:
        t, inner = front_page(fp)
        items.append(('f_' + os.path.basename(fp)[:-4], t, page(t, inner, css, lang)))

    uid = 'urn:uuid:' + str(uuid.uuid5(uuid.NAMESPACE_URL, 'bespoke-reader:' + title))
    now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    man = [f'<item id="{i}" href="text/{i}.xhtml" media-type="application/xhtml+xml"/>' for i, _, _ in items]
    man += ['<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
            '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>']
    man += [f'<item id="css{k}" href="{c}" media-type="text/css"/>' for k, c in enumerate(css)]
    types = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.gif': 'image/gif', '.webp': 'image/webp', '.svg': 'image/svg+xml'}
    spine = ''
    cover_href = None
    if meta.get('cover') and os.path.exists(os.path.join(orig, meta['cover'])):
        ext = os.path.splitext(meta['cover'])[1].lower()
        cover_href = 'cover' + ext
        man.append(f'<item id="cover-image" href="{cover_href}" media-type="{types.get(ext, "image/jpeg")}" properties="cover-image"/>')
        man.append('<item id="coverpage" href="text/cover.xhtml" media-type="application/xhtml+xml"/>')
        spine += '<itemref idref="coverpage"/>'
    for k, (src, new) in enumerate(img_map.items()):
        man.append(f'<item id="img{k}" href="{new}" media-type="{types.get(os.path.splitext(new)[1].lower(), "image/jpeg")}"/>')
    spine += ''.join(f'<itemref idref="{i}"/>' for i, _, _ in items)
    opf = (f'<?xml version="1.0" encoding="utf-8"?>\n<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid" xml:lang="{lang}">\n'
           f'<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="bookid">{uid}</dc:identifier>'
           f'<dc:title>{esc(title)}</dc:title><dc:creator>{esc(author)}</dc:creator><dc:language>{lang}</dc:language>'
           f'<meta property="dcterms:modified">{now}</meta>' + ('<meta name="cover" content="cover-image"/>' if cover_href else '') +
           f'</metadata>\n<manifest>\n' + '\n'.join(man) + f'\n</manifest>\n<spine toc="ncx">{spine}</spine>\n</package>')
    nav = (f'<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="{lang}">'
           f'<head><meta charset="utf-8"/><title>{M["toc"]}</title></head><body><nav epub:type="toc" id="toc"><h1>{M["toc"]}</h1><ol>'
           + ''.join(f'<li><a href="text/{i}.xhtml">{esc(t)}</a></li>' for i, t, _ in items) + '</ol></nav></body></html>')
    ncx = (f'<?xml version="1.0" encoding="utf-8"?>\n<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1"><head><meta name="dtb:uid" content="{uid}"/></head>'
           f'<docTitle><text>{esc(title)}</text></docTitle><navMap>'
           + ''.join(f'<navPoint id="np{k}" playOrder="{k + 1}"><navLabel><text>{esc(t)}</text></navLabel><content src="text/{i}.xhtml"/></navPoint>'
                     for k, (i, t, _) in enumerate(items)) + '</navMap></ncx>')
    container = ('<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
                 '<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
    with zipfile.ZipFile(a.out, 'w') as z:
        z.writestr(zipfile.ZipInfo('mimetype'), 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
        w = lambda name, s: z.writestr(name, s, compress_type=zipfile.ZIP_DEFLATED)
        w('META-INF/container.xml', container)
        w('OEBPS/content.opf', opf)
        w('OEBPS/nav.xhtml', nav)
        w('OEBPS/toc.ncx', ncx)
        for c_src, c_dst in zip(meta['css'], css):
            p = os.path.join(orig, c_src)
            if os.path.exists(p):
                w('OEBPS/' + c_dst, open(p, encoding='utf-8', errors='ignore').read())
        w('OEBPS/css/extra.css', EXTRA_CSS)
        if cover_href:
            z.write(os.path.join(orig, meta['cover']), 'OEBPS/' + cover_href)
            w('OEBPS/text/cover.xhtml', '<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n<html xmlns="http://www.w3.org/1999/xhtml">'
              f'<head><meta charset="utf-8"/><title>{M["cover"]}</title><style>body{{margin:0;padding:0;text-align:center;}} img{{max-width:100%;max-height:100%;}}</style></head>'
              f'<body><div><img src="../{cover_href}" alt="{M["cover"]}"/></div></body></html>')
        for src, new in img_map.items():
            if os.path.exists(os.path.join(orig, src)):
                z.write(os.path.join(orig, src), 'OEBPS/' + new)
        for i, t, content in items:
            w(f'OEBPS/text/{i}.xhtml', content)
    z = zipfile.ZipFile(a.out)
    errors = 0
    for name in z.namelist():
        if name.endswith(('.xhtml', '.opf', '.ncx', '.xml')):
            try:
                ET.fromstring(z.read(name))
            except ET.ParseError as e:
                errors += 1
                print('XML error', name, e)
    print(f'{a.out}: {len(items)} documents, {len(img_map)} images, cover {"yes" if cover_href else "no"}, '
          f'{"all documents well-formed" if not errors else str(errors) + " malformed"}')
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()

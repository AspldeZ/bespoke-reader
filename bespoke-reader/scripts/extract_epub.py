#!/usr/bin/env python3
# Usage: python3 extract_epub.py book.epub outdir
import zipfile, sys, os, re, posixpath
from xml.etree import ElementTree as ET
from html.parser import HTMLParser
BLOCK={'p','div','h1','h2','h3','h4','h5','h6','li','blockquote','br','tr'}
class Ext(HTMLParser):
    def __init__(s): super().__init__(); s.buf=[]; s.out=[]; s.skip=0
    def handle_starttag(s,t,a):
        if t in ('script','style'): s.skip+=1
        if t in BLOCK: s.flush()
    def handle_endtag(s,t):
        if t in ('script','style'): s.skip-=1
        if t in BLOCK: s.flush()
    def handle_data(s,d):
        if not s.skip: s.buf.append(d)
    def flush(s):
        x=re.sub(r'\s+',' ',''.join(s.buf)).strip(); s.buf=[]
        if x: s.out.append(x)
src,out=sys.argv[1],sys.argv[2]; os.makedirs(out,exist_ok=True)
z=zipfile.ZipFile(src)
opf=ET.fromstring(z.read('META-INF/container.xml')).find('.//{*}rootfile').get('full-path')
o=ET.fromstring(z.read(opf)); base=posixpath.dirname(opf)
man={i.get('id'):i.get('href') for i in o.find('{*}manifest')}
spine=[r.get('idref') for r in o.find('{*}spine')]
title=o.findtext('.//{http://purl.org/dc/elements/1.1/}title') or ''
rows=[]; n=0
for idref in spine:
    href=man.get(idref)
    if not href: continue
    path=posixpath.normpath(posixpath.join(base,href.split('#')[0]))
    try: raw=z.read(path).decode('utf-8','ignore')
    except KeyError: continue
    e=Ext(); e.feed(raw); e.flush()
    chars=sum(len(p) for p in e.out)
    if chars<200: continue
    n+=1; fn=f'ch{n:03d}.txt'
    with open(os.path.join(out,fn),'w') as f:
        for i,p in enumerate(e.out,1): f.write(f'[{n}.{i}] {p}\n')
    rows.append((fn,len(e.out),chars,e.out[0][:40]))
with open(os.path.join(out,'index.tsv'),'w') as f:
    f.write(f'# {title}\n')
    for r in rows: f.write('\t'.join(map(str,r))+'\n')
print(title,len(rows),'chapters',sum(r[2] for r in rows),'chars')

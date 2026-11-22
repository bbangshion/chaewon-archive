#!/usr/bin/env python3
"""Prepare permitted public Objekt card art for a same-origin, exportable 4-card canvas.
Does not rewrite any existing Objekt catalog record. Logs missing card sources explicitly.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import ipaddress
import json
import os
from pathlib import Path
import socket
import sys
from urllib.parse import urlsplit

import requests
from PIL import Image, ImageOps

CATALOG=Path('public/data/objekt.json')
MAP=Path('public/data/objekt-poster-map.json')
OUTPUT=Path('public/objekt-poster')
MAX_IMAGE_BYTES=9*1024*1024
Image.MAX_IMAGE_PIXELS=32_000_000


def allowed(url):
    if not isinstance(url,str):
        return False
    try:
        p=urlsplit(url)
        if p.scheme != 'https' or not p.hostname or p.username or p.password or p.port not in (None,443):
            return False
        if p.hostname.lower() in {'localhost','metadata.google.internal'} or p.hostname.lower().endswith(('.local','.internal')):
            return False
        try:
            addr=ipaddress.ip_address(p.hostname)
            if not addr.is_global: return False
        except ValueError:
            pass
        return True
    except ValueError:
        return False


def public_dns(hostname):
    # Avoid connecting to private/cloud metadata hosts even through custom DNS.
    try:
        addresses=socket.getaddrinfo(hostname,443,type=socket.SOCK_STREAM)
        return bool(addresses) and all(ipaddress.ip_address(row[4][0]).is_global for row in addresses)
    except (socket.gaierror,ValueError):
        return False


def download(url):
    if not allowed(url) or not public_dns(urlsplit(url).hostname):
        raise ValueError('Unsupported card image URL')
    with requests.Session() as sess:
        sess.headers.update({'User-Agent':'CHAEWON-ARCHIVE/1.0 Poster Cache','Accept':'image/avif,image/webp,image/png,image/jpeg,image/*;q=0.8'})
        # Restrict each hop, including redirect targets.
        for _ in range(4):
            with sess.get(url,timeout=(5,12),stream=True,allow_redirects=False) as response:
                if response.is_redirect:
                    from urllib.parse import urljoin
                    dest=urljoin(url,response.headers.get('location',''))
                    if not allowed(dest): raise ValueError('Unsafe redirected URL')
                    url=dest
                    if not public_dns(urlsplit(url).hostname): raise ValueError('Unsafe redirected host')
                    continue
                response.raise_for_status()
                kind=response.headers.get('Content-Type','')
                if kind and not kind.lower().startswith('image/') and 'octet-stream' not in kind.lower():
                    raise ValueError('Not an image response')
                total=0
                chunks=[]
                for chunk in response.iter_content(65536):
                    total+=len(chunk)
                    if total>MAX_IMAGE_BYTES: raise ValueError('Card image too large')
                    chunks.append(chunk)
                return b''.join(chunks)
    raise ValueError('Too many image redirects')


def convert(raw):
    with Image.open(BytesIO(raw)) as src:
        src=ImageOps.exif_transpose(src)
        if src.width<50 or src.height<50: raise ValueError('Card image too small')
        src.thumbnail((660,990),Image.Resampling.LANCZOS)
        if src.mode != 'RGB':
            if 'A' in src.getbands():
                background=Image.new('RGBA',src.size,'#211d27')
                background.alpha_composite(src.convert('RGBA'))
                src=background.convert('RGB')
            else: src=src.convert('RGB')
        output=BytesIO()
        src.save(output,'WEBP',quality=80,method=4)
        return output.getvalue()


def main():
    if not CATALOG.is_file(): raise RuntimeError('Missing public/data/objekt.json')
    source=json.loads(CATALOG.read_text('utf-8'))
    cards=source if isinstance(source,list) else source.get('objekts',source.get('items',[]))
    if not isinstance(cards,list): raise RuntimeError('Unsupported Objekt data structure')
    urls=sorted(set(row['imageUrl'].strip() for row in cards if isinstance(row,dict) and isinstance(row.get('imageUrl'),str) and allowed(row['imageUrl'].strip())))
    if not urls: raise RuntimeError('No HTTPS Objekt images in catalog. No poster cache can be generated.')
    OUTPUT.mkdir(parents=True,exist_ok=True)
    MAP.parent.mkdir(parents=True,exist_ok=True)
    existing = {}
    if MAP.is_file():
        try: existing=json.loads(MAP.read_text('utf-8')).get('sources',{})
        except (ValueError,TypeError,AttributeError): pass
    prepared={}
    failures=[]
    def worker(url):
        digest=sha256(url.encode('utf-8')).hexdigest()[:24]
        relative=f'objekt-poster/{digest}.webp'
        target=OUTPUT/(digest+'.webp')
        if target.exists() and 64 <= target.stat().st_size <= MAX_IMAGE_BYTES:
            return url,relative,None
        try:
            raw=download(url)
            result=convert(raw)
            temp=target.with_suffix('.webp.tmp')
            temp.write_bytes(result)
            temp.replace(target)
            return url,relative,None
        except Exception as exc:
            return url,None,type(exc).__name__
    with ThreadPoolExecutor(max_workers=12) as executor:
        tasks=[executor.submit(worker,url) for url in urls]
        for i,future in enumerate(as_completed(tasks),1):
            url,relative,error=future.result()
            if relative: prepared[url]=relative
            else: failures.append(error)
            if i%50 == 0 or i==len(urls):
                print(f'Poster cache {i}/{len(urls)}: {len(prepared)} ready, {len(failures)} unavailable',flush=True)
    manifest={'version':1,'preparedAt':datetime.now(timezone.utc).isoformat(),
        'totalSourceImages':len(urls),'prepared':len(prepared),'sources':prepared}
    MAP.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if prepared:
        print(f'OK: {len(prepared)}/{len(urls)} card thumbnails cached. The tournament poster can use these images.',flush=True)
    if failures:
        print(f'WARNING: {len(failures)} card thumbnails could not be prepared. Unavailable cards use marked placeholders in saved PNG.',flush=True)
    if not prepared:
        raise RuntimeError('Could not prepare any card thumbnails. Check the original image URLs and access conditions.')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f:
            f.write(f'## World Cup image cache\n\n- Cards with remote images: {len(urls)}\n- Cached: {len(prepared)}\n- Unavailable: {len(failures)}\n')


if __name__=='__main__': main()

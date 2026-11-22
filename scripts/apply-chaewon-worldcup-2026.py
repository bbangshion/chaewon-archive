#!/usr/bin/env python3
"""Minimal targeted, repeatable patch for S21 world cup PNG & 2026 HOME photos."""
from pathlib import Path
import json, re, os, sys

def change(path, replace_list):
    file=Path(path)
    if not file.is_file():
        raise RuntimeError(f'Expected file missing: {file}')
    src=file.read_text(encoding='utf-8')
    out=src
    for before,after in replace_list:
        if before not in out:
            if after in out: continue
            raise RuntimeError(f'Cannot find expected source fragment in {file}: {before[:105]}')
        out=out.replace(before,after,1)
    if src != out:
        file.write_text(out,encoding='utf-8')
        print(f'PATCHED: {path}',flush=True)
    else:
        print(f'ALREADY PATCHED: {path}',flush=True)

change('src/lib/searchIndex.ts', [
    ('year: date?.slice(0, 4) || null,',
     "year: (typeof row.year === 'string' && /^20\\d{2}$/.test(row.year) ? row.year : date?.slice(0, 4) || null),")
])

change('src/components/HomeUpdates.tsx', [
    ('const photos = data?.photos.slice(0, 6) ?? [];',
     "// Prefer source-labelled 2026 photography; do not invent shoot dates.\n"
     "  const photos = data?.photos.filter((photo) => photo.year === '2026')"
     ".sort((a, b) => (b.date || '').localeCompare(a.date || '') || a.key.localeCompare(b.key))"
     ".slice(0, 6) ?? [];"),
    ("{photo.date || t('날짜 미등록')}",
     "{photo.date || (photo.year === '2026' ? '2026 · 촬영일 미확인' : t('날짜 미등록'))}"),
])

featured='src/components/ChaewonFeaturedPhotos.tsx'
if Path(featured).is_file():
    change(featured,[
        ('const featured = items.slice(0, 6);',
         "const featured = items.filter((photo) => photo.year === '2026' || photo.date?.startsWith('2026-')).slice(0, 6);")
    ])

wc='src/components/TournamentArena.tsx'
changes=[
    ("if (!output.blob || output.missingImages !== 0) {\n          setPosterError(copy.imageBlocked);\n          return;\n        }",
     "if (!output.blob) {\n          setPosterError(copy.imageBlocked);\n          return;\n        }\n"
     "        // Never disable PNG saving merely because a remote card host blocks CORS.\n"
     "        if (output.missingImages > 0) setPosterError(copy.imageBlocked);"),
    ('박시온 오브젝트 월드컵','김채원 오브젝트 월드컵'),
    ('ShiOn Objekt World Cup','ChaeWon Objekt World Cup'),
    ('シオンObjektワールドカップ','チェウォンObjektワールドカップ'),
    ('SHION ARCHIVE · @bbangshion','CHAEWON ARCHIVE · @bbangshion'),
    ('SHION ARCHIVE <span>·</span> @bbangshion','CHAEWON ARCHIVE <span>·</span> @bbangshion'),
    ('SHION-Objekt-Top4-','CHAEWON-Objekt-Top4-'),
    ('<h3>ShiOn</h3>','<h3>ChaeWon</h3>'),
    ("imageBlocked: '카드 원본 이미지가 일부 준비되지 않아 사진 4장이 포함된 PNG를 만들 수 없어요. GitHub Actions의 World Cup photo cache 로그를 확인해 주세요.'",
     "imageBlocked: '일부 카드 원본을 불러올 수 없어 해당 사진은 안내 영역으로 표시됩니다. PNG 저장과 공유는 가능합니다.'"),
    ("imageBlocked: 'Some card images could not be prepared for PNG export. Please check the World Cup photo cache step in GitHub Actions.'",
     "imageBlocked: 'Some original card images could not load. Their spaces are marked, but you can still save and share the PNG.'"),
    ("imageBlocked: '一部のカード画像をPNG用に準備できませんでした。GitHub ActionsのWorld Cup photo cacheを確認してください。'",
     "imageBlocked: '一部のカード写真を読み込めませんでした。代替表示になりますが、PNGの保存と共有はできます。'"),
]
# Source versions can already have individualized branding; missing branding replacement should be harmless.
if not Path(wc).is_file(): raise RuntimeError('Missing TournamentArena.tsx')
raw=Path(wc).read_text('utf-8')
if 'output.missingImages !== 0' not in raw and 'output.missingImages > 0' not in raw:
    raise RuntimeError('Cannot locate the tournament PNG export guard: refusing unsafe edit')
patches=[]
for before,after in changes:
    if before in raw or after in raw: patches.append((before,after))
change(wc,patches)

p='src/lib/worldCupPoster.ts'
if Path(p).is_file():
    raw=Path(p).read_text('utf-8')
    tweaks=[]
    for a,b in [('SHION ARCHIVE  ·  @bbangshion','CHAEWON ARCHIVE  ·  @bbangshion'),
                ("ctx.fillText('ShiOn', 540, 156)","ctx.fillText('ChaeWon', 540, 156)"),
                ("ctx.fillText('SHION', box.x + box.w / 2, box.y + box.h / 2)","ctx.fillText('CHAEWON', box.x + box.w / 2, box.y + box.h / 2)")]:
        if a in raw or b in raw: tweaks.append((a,b))
    change(p,tweaks)

# Validate the number of 2026 source-marked photos; no invented dates, filler or duplicate entries.
photos_file=Path('public/data/photos.json')
if photos_file.is_file():
    payload=json.loads(photos_file.read_text('utf-8'))
    photos=payload if isinstance(payload,list) else payload.get('photos',[])
    matches=[r for r in photos if isinstance(r,dict) and (str(r.get('year') or '')=='2026' or str(r.get('date') or '').startswith('2026-'))]
    print(f'2026 source-labelled PHOTO records: {len(matches)}',flush=True)
    if len(matches)<6:
        raise RuntimeError('Not enough metadata-verified 2026 photos for six HOME tiles. Add six real 2026 records or verify year metadata first.')


#!/usr/bin/env python3
"""Non-destructive S21 design unification atop current CHAEWON source.

Borrow only YEONJI's editorial layout language, not its content, metadata or images.
Run inside the checked-out chaewon-archive repository from the workflow.
"""
from pathlib import Path
import json
import re

ROOT=Path.cwd()
APP=ROOT/'src/App.tsx'
MAIN=ROOT/'src/main.tsx'
PHOTO=ROOT/'src/components/PhotoArchive.tsx'
STYLES=ROOT/'src/chaewon-unified.css'
FEATURE=ROOT/'src/components/ChaewonFeaturedPhotos.tsx'
GALLERY=ROOT/'public/gallery/index.html'

if not APP.is_file():
    raise SystemExit('STOP: src/App.tsx not found. Site has changed; no edits made.')
if not PHOTO.is_file():
    raise SystemExit('STOP: src/components/PhotoArchive.tsx not found. Site has changed; no edits made.')
if not MAIN.is_file():
    raise SystemExit('STOP: src/main.tsx not found. Site has changed; no edits made.')
for asset in (STYLES, FEATURE, GALLERY):
    if not asset.is_file() or not asset.stat().st_size:
        raise SystemExit('STOP: Missing patch asset: '+str(asset))

app = APP.read_text(encoding='utf-8')
main = MAIN.read_text(encoding='utf-8')
photo = PHOTO.read_text(encoding='utf-8')
# Validate every insertion target BEFORE writing files.
if 'ChaewonFeaturedPhotos' not in app and '<HomeUpdates />' not in app:
    raise SystemExit('STOP: HomeUpdates anchor changed. No files overwritten.')
if 'ChaewonFeaturedPhotos' in app and '<ChaewonFeaturedPhotos' not in app:
    raise SystemExit('STOP: Partial previous insertion detected. No files overwritten.')
if 'cw-gallery-inline' not in photo and '<RecentPhotoSources />' not in photo:
    raise SystemExit('STOP: PhotoArchive anchor changed. No files overwritten.')
if "import './chaewon-unified.css';" not in main and "import './index.css';" not in main:
    raise SystemExit('STOP: main.tsx stylesheet anchor changed. No files overwritten.')

# Import after the base index.css to ensure the S21 override wins the CSS cascade.
# Remove legacy previous-version import only when main.tsx has the replacement.
if "import './chaewon-unified.css';" not in main:
    main=main.replace("import './index.css';", "import './index.css';\nimport './chaewon-unified.css';", 1)
app=app.replace("import './chaewon-unified.css';\n", '', 1)
if "const ChaewonFeaturedPhotos = lazy" not in app:
    anchor=re.search(r'(?m)^const HomeUpdates\s*=\s*lazy\(',app)
    if not anchor:
        raise SystemExit('STOP: lazy HomeUpdates import is missing. No files overwritten.')
    start=anchor.start()
    app=app[:start]+"const ChaewonFeaturedPhotos = lazy(() => import('./components/ChaewonFeaturedPhotos'));\n"+app[start:]
if '<ChaewonFeaturedPhotos' not in app:
    idx=app.find('<HomeUpdates />')
    stop=app.find('</Suspense>',idx)
    if idx<0 or stop<0 or stop-idx>600:
        raise SystemExit('STOP: Home insertion target ambiguous. No files overwritten.')
    stop+=len('</Suspense>')
    app=app[:stop]+"\n      <Suspense fallback={null}><ChaewonFeaturedPhotos /></Suspense>"+app[stop:]
if 'cw-gallery-inline' not in photo:
    photo=photo.replace('<RecentPhotoSources />', '''<RecentPhotoSources />
    <a className="cw-gallery-inline" href={`${import.meta.env.BASE_URL}gallery/`}>
      <span><b>THE PHOTO COLLECTION</b><small>CHAEWON · S21</small></span>
      <span>ALL PHOTOS <span aria-hidden="true">↗</span></span>
    </a>''',1)
# Only change the two source files if all pattern checks pass.
APP.write_text(app,encoding='utf-8')
MAIN.write_text(main,encoding='utf-8')
PHOTO.write_text(photo,encoding='utf-8')
# Never edit existing photos / assets / Objekt metadata.
checks={
  'PROFILE': ROOT/'src/components/ProfilePage.tsx',
  'PHOTO': PHOTO,
  'FILM': ROOT/'src/components/ShionFilm.tsx',
  'TIMELINE': ROOT/'src/components/TimelinePage.tsx',
  'OBJEKT': ROOT/'src/components/Collection.tsx',
  'WORLD CUP': ROOT/'src/components/TournamentArena.tsx',
  'WORLD CUP TOP 4':ROOT/'src/lib/topFour.ts',
  'SEARCH':ROOT/'src/components/SearchPage.tsx',
  'KO/EN/JA':ROOT/'src/i18n/I18nContext.tsx',
  'SCROLL REVEAL':ROOT/'src/components/ScrollReveal.tsx',
  'GALLERY V2':GALLERY,
  'HOME PHOTO GRID':FEATURE,
}
print('CHAEWON DESIGN UNIFICATION — file checks:')
for name,file in checks.items(): print(('PASS' if file.is_file() else 'CHECK')+'  '+name)
photo_path=ROOT/'public/data/photos.json'
if photo_path.is_file():
    try:
        data=json.loads(photo_path.read_text(encoding='utf-8'))
        rows=data if isinstance(data,list) else data.get('photos',[])
        print('PHOTO DATA PRESERVED:',len(rows))
    except Exception as e:
        raise SystemExit('STOP: Existing photos.json invalid; no photo data altered.') from e
print('Applied ADDITIVE design and gallery enhancement. Existing contents preserved.')

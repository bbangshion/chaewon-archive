#!/usr/bin/env python3
"""CHAEWON ARCHIVE / official Instagram candidate discovery & reviewed photo import.
No automated login/scraping; Business Discovery via authorized Meta Graph API.
"""
import datetime as dt
import hashlib
import io
import json
import os
from pathlib import Path
import re
import time
from urllib import error, parse, request

from PIL import Image, ImageOps, UnidentifiedImageError

OFFICIAL = 'triplescosmos'
MEMBER = 'S21'
NAME = re.compile(r'(?<![\w])(?:김\s*채원|채원|kim\s*chae\s*won|chae\s*won|チェウォン|S21)(?![\w])', re.I)
DATE_START = '2024-04-01'
REVIEW = Path('reports/chaewon-official-instagram-review.json')
PHOTOS = Path('public/data/photos.json')
ASSETS = Path('public/images/chaewon-official')
SUPPORTED_HOSTS = ('cdninstagram.com', 'fbcdn.net')


def save_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)


def load_json(path, default):
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding='utf-8'))


def require_https(url):
    try:
        p = parse.urlsplit(url)
        return p.scheme == 'https' and bool(p.hostname) and not p.username and not p.password
    except (TypeError, ValueError):
        return False


def allow_cdn(url):
    if not require_https(url):
        return False
    host = parse.urlsplit(url).hostname.lower()
    return any(host == ending or host.endswith('.' + ending) for ending in SUPPORTED_HOSTS)


class Redirects(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not allow_cdn(newurl):
            raise ValueError('Remote media redirect domain not allowed')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def api(url, token):
    req = request.Request(url, headers={
        'Authorization': 'Bearer ' + token,
        'Accept': 'application/json',
        'User-Agent': 'CHAEWON-ARCHIVE/1.0',
    })
    try:
        with request.urlopen(req, timeout=30) as res:
            return json.loads(res.read(12_000_000))
    except error.HTTPError as exc:
        info = {}
        try:
            info = json.loads(exc.read(16384)).get('error', {})
        except Exception:
            pass
        # Never expose token, raw URL or sensitive response body in CI logs.
        raise RuntimeError(f'Meta Graph API HTTP {exc.code}; code={info.get("code", "?")}; subcode={info.get("error_subcode", "?")}') from None


def valid_date(value):
    if not value:
        return None
    try:
        return dt.date.fromisoformat(str(value)[:10]).isoformat()
    except ValueError:
        return None


def flatten_post(post):
    caption = post.get('caption') or ''
    if not NAME.search(caption):
        return []  # no auto-claim of appearance for unlabeled posts
    day = valid_date(post.get('timestamp'))
    permalink = post.get('permalink') or ''
    if not day or day < DATE_START or not require_https(permalink):
        return []
    if parse.urlsplit(permalink).hostname not in ('instagram.com', 'www.instagram.com'):
        return []
    typ = post.get('media_type')
    if typ == 'IMAGE':
        child_items = [post]
    elif typ == 'CAROUSEL_ALBUM':
        child_items = post.get('children', {}).get('data', [])
    else:
        return []
    found = []
    for idx, child in enumerate(child_items, 1):
        if child.get('media_type') != 'IMAGE' or not child.get('id'):
            continue
        media_url = child.get('media_url') or ''
        media_id = str(child['id'])
        found.append({
            'mediaId': media_id,
            'postId': str(post.get('id') or ''),
            'date': day,
            'position': idx,
            'author': '@' + OFFICIAL,
            'sourceUrl': permalink,
            'caption': caption[:500],
            'imageUrl': media_url if allow_cdn(media_url) else '',
            'status': 'pending',
        })
    return found


def scan(token, user_id, version, max_pages):
    if not re.fullmatch(r'v\d+\.\d+', version):
        raise ValueError('Invalid Graph API version')
    if not user_id.isdigit():
        raise ValueError('Invalid IG_USER_ID')
    found = {}
    cursor = None
    scanned = pages = 0
    seen_cursors = set()
    more = False
    incomplete = 0
    for _ in range(max_pages):
        paging = '.after(' + cursor + ')' if cursor else ''
        fields = (f'business_discovery.username({OFFICIAL})'
                  '{username,media.limit(50)' + paging +
                  '{id,caption,media_type,permalink,timestamp,media_url,'
                  'children{id,media_type,media_url}}}')
        url = f'https://graph.facebook.com/{version}/{user_id}?' + parse.urlencode({'fields': fields})
        response = api(url, token)
        obj = response.get('business_discovery') or {}
        if (obj.get('username') or '').casefold() != OFFICIAL:
            raise RuntimeError('Requested official account was not confirmed')
        media = obj.get('media') or {}
        data = media.get('data')
        if not isinstance(data, list):
            raise RuntimeError('Official media not returned by API')
        pages += 1
        for post in data:
            scanned += 1
            for row in flatten_post(post):
                found[row['mediaId']] = row
            if post.get('media_type') == 'CAROUSEL_ALBUM' and NAME.search(post.get('caption') or ''):
                children = post.get('children') or {}
                if (children.get('paging') or {}).get('next'):
                    incomplete += 1
        more = bool((media.get('paging') or {}).get('next'))
        if not more:
            break
        cursor = ((media.get('paging') or {}).get('cursors') or {}).get('after')
        if not cursor or cursor in seen_cursors or not re.fullmatch(r'[A-Za-z0-9_+\-/=]+', cursor):
            raise RuntimeError('Instagram pagination cursor unavailable')
        seen_cursors.add(cursor)
        time.sleep(1)
    return found, {'scannedPosts': scanned, 'pages': pages, 'morePagesAvailable': more,
                   'incompleteCarousels': incomplete}


def fetch_image(url):
    if not allow_cdn(url):
        raise ValueError('Image URL is unavailable or not an official API CDN URL')
    req = request.Request(url, headers={'User-Agent': 'CHAEWON-ARCHIVE/1.0', 'Accept': 'image/*'})
    with request.build_opener(Redirects()).open(req, timeout=30) as response:
        if not (response.headers.get_content_type() or '').startswith('image/'):
            raise ValueError('Unexpected content type')
        data = response.read(15_000_001)
        if len(data) > 15_000_000 or not data:
            raise ValueError('Image too large or empty')
    with Image.open(io.BytesIO(data)) as check:
        check.verify()
    return data


def rows(value):
    if isinstance(value, list):
        return value
    if isinstance(value, dict) and isinstance(value.get('photos'), list):
        return value['photos']
    raise ValueError('Existing photos.json has an unsupported shape; refusing to overwrite')


def publish(selected, discovered, base_data):
    items = rows(base_data)
    existing_ids = {str(x.get('mediaId') or '') for x in items if isinstance(x, dict)}
    existing_hashes = {x.get('sha256') for x in items if isinstance(x, dict) and x.get('sha256')}
    published = []
    errors = []
    duplicates = 0
    ASSETS.mkdir(parents=True, exist_ok=True)
    for mid in selected:
        if mid in existing_ids:
            duplicates += 1
            continue
        item = discovered.get(mid)
        if not item or not item.get('imageUrl'):
            errors.append(f'{mid}: not found or media URL unavailable in current scan')
            continue
        try:
            raw = fetch_image(item['imageUrl'])
            digest = hashlib.sha256(raw).hexdigest()
            if digest in existing_hashes:
                duplicates += 1
                continue
            with Image.open(io.BytesIO(raw)) as image:
                image = ImageOps.exif_transpose(image)
                if min(image.size) < 64:
                    raise ValueError('Image resolution too small')
                image.thumbnail((1800, 2400))
                if image.mode not in ('RGB', 'L'):
                    image = image.convert('RGB')
                output = ASSETS / f'{digest[:32]}.webp'
                image.save(output, format='WEBP', quality=88, method=5)
            record = {
                'id': f'cw-official-{digest[:32]}', 'category': 'photo', 'memberId': MEMBER,
                'image': f'images/chaewon-official/{output.name}',
                'title': {'ko': '김채원 · 공식 SNS', 'en': 'ChaeWon · Official SNS', 'ja': 'チェウォン・公式SNS'},
                'album': {'ko': '공식 SNS', 'en': 'Official SNS', 'ja': '公式SNS'},
                'date': item['date'],
                'credit': {'ko': '원본: tripleS 공식 Instagram · 제작: 빵시온',
                           'en': 'Original: tripleS official Instagram · Site: bbangshion',
                           'ja': '原典: tripleS公式Instagram・制作: bbangshion'},
                'sourceUrl': item['sourceUrl'],
                'sourceType': 'official-instagram', 'originalCreator': '@' + OFFICIAL,
                'tags': ['S21', '김채원', 'ChaeWon'],
                'sha256': digest, 'mediaId': mid,
                'rightsStatus': 'reviewed-by-curator',
            }
            items.append(record)
            published.append(mid)
            existing_ids.add(mid)
            existing_hashes.add(digest)
        except (ValueError, error.URLError, TimeoutError, UnidentifiedImageError, OSError) as exc:
            errors.append(f'{mid}: {type(exc).__name__}')
    if published:
        if isinstance(base_data, list):
            result = items
        else:
            result = dict(base_data, photos=items)
        save_json(PHOTOS, result)
    return published, duplicates, errors


def main():
    mode = os.getenv('MODE', 'discover')
    if mode not in ('discover', 'publish'):
        raise SystemExit('Mode must be discover or publish')
    token = os.getenv('IG_ACCESS_TOKEN', '')
    user_id = os.getenv('IG_USER_ID', '')
    if not token or not user_id:
        raise SystemExit('Add IG_ACCESS_TOKEN and IG_USER_ID to this repository Actions Secrets')
    max_pages = int(os.getenv('MAX_PAGES', '2'))
    if not 1 <= max_pages <= 20:
        raise SystemExit('MAX_PAGES must be 1-20')
    requested = sorted({x.strip() for x in os.getenv('MEDIA_IDS', '').split(',') if x.strip()})
    if mode == 'publish':
        if not requested:
            raise SystemExit('Enter verified media IDs from review report')
        if os.getenv('CONFIRM') != 'VERIFIED_AND_CLEARED':
            raise SystemExit('Set CONFIRM only after verifying ChaeWon is depicted and reuse rights are cleared')
    found, stats = scan(token, user_id, os.getenv('IG_GRAPH_API_VERSION') or 'v24.0', max_pages)
    past = load_json(REVIEW, {})
    prev = {str(x.get('mediaId')): x for x in past.get('candidates', [])
            if isinstance(x, dict) and x.get('author') == '@' + OFFICIAL and x.get('mediaId')}
    for mid, row in found.items():
        # Never carry expired CDN URLs into a saved approval record.
        item = {k: v for k, v in row.items() if k != 'imageUrl'}
        item['imageAvailableInLastScan'] = bool(row.get('imageUrl'))
        item['status'] = prev.get(mid, {}).get('status', 'pending')
        prev[mid] = item
    added = []
    dup = 0
    failures = []
    if mode == 'publish':
        # Only publish IDs already selected from a prior review report.
        unknown = set(requested) - set(prev)
        if unknown:
            raise SystemExit(f'{len(unknown)} selected IDs were not in review report; run discover first')
        base = load_json(PHOTOS, [])
        added, dup, failures = publish(requested, found, base)
        for mid in added:
            prev[mid]['status'] = 'published'
    report = {'account': '@' + OFFICIAL,
              'note': 'Caption matches are candidates, not proof of the person in every picture. Review & rights clearance required.',
              'mode': mode, 'lastScan': stats,
              'candidateCount': len(prev),
              'newPublishedCount': len(added), 'duplicatesSkipped': dup, 'publishErrors': failures,
              'candidates': sorted(prev.values(), key=lambda r: (r.get('date') or '', r.get('mediaId') or ''), reverse=True)}
    save_json(REVIEW, report)
    summary = (f'Official posts scanned: {stats["scannedPosts"]} ({stats["pages"]} pages)\n\n'
               f'Chaewon-labelled image candidates: {len(prev)}\n\n'
               f'New images published: {len(added)}; duplicates skipped: {dup}; failed: {len(failures)}\n\n'
               f'Existing PHOTO count: {len(rows(load_json(PHOTOS, [])))}\n\n'
               f'More pages available: {stats["morePagesAvailable"]}\n\n'
               'Review: reports/chaewon-official-instagram-review.json')
    print(summary)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as file:
            file.write('## CHAEWON OFFICIAL PHOTO\n\n' + summary.replace('\n', '  \n') + '\n')


if __name__ == '__main__':
    main()

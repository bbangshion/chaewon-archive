import { useEffect, useMemo, useState } from 'react';
import { useI18n } from '../i18n/I18nContext';

type Row = Record<string, unknown>;
type GalleryPhoto = {
  id: string;
  url: string;
  title: string;
  album: string;
  date: string | null;
  year: string | null;
};
const BASE = import.meta.env.BASE_URL;
const PATH = `${BASE}gallery/`;
const localized = (v: unknown, language: string, fallback: string) => {
  if (typeof v === 'string') return v || fallback;
  if (v && typeof v === 'object' && !Array.isArray(v)) {
    const o = v as Record<string, unknown>;
    return String(o[language] || o.ko || o.en || fallback);
  }
  return fallback;
};
const safeImage = (value: unknown) => {
  if (typeof value !== 'string') return null;
  if (/^https:\/\//i.test(value)) return value;
  if (/^(?!\/)(?!\.)(?!.*\/\.{1,2}\/)[a-z0-9_./%\-]+\.(?:webp|avif|png|jpe?g)$/i.test(value)) return `${BASE}${value}`;
  return null;
};
const validDay = (v: unknown) => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(v) ? v : null;

export default function ChaewonFeaturedPhotos() {
  const { language } = useI18n();
  const [all, setAll] = useState<Row[]>([]);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    fetch(`${BASE}data/photos.json`, { signal: controller.signal, cache: 'no-cache' })
      .then(r => { if (!r.ok) throw new Error('PHOTO'); return r.json(); })
      .then((data: unknown) => {
        const rows = Array.isArray(data) ? data : data && typeof data === 'object' && Array.isArray((data as {photos?:unknown}).photos) ? (data as {photos:Row[]}).photos : [];
        if (!controller.signal.aborted) setAll(rows.filter((r): r is Row => r !== null && typeof r === 'object' && !Array.isArray(r)));
      })
      .catch(() => { if (!controller.signal.aborted) setFailed(true); });
    return () => controller.abort();
  }, []);
  const items = useMemo(() => all.map((row): GalleryPhoto | null => {
    const id = typeof row.id === 'string' ? row.id : '';
    const url = safeImage(row.image);
    if (!id || !url || row.category && row.category !== 'photo') return null;
    return {
      id, url, title: localized(row.title, language, '김채원'),
      album: localized(row.album, language, 'PHOTO'), date: validDay(row.date),
      year: typeof row.year === 'string' && /^20\d{2}$/.test(row.year) ? row.year : null,
    };
  }).filter((photo): photo is GalleryPhoto => photo !== null)
    .sort((a,b) => Number(Boolean(b.date)) - Number(Boolean(a.date)) || (b.date || '').localeCompare(a.date || '')),
  [all, language]);
  const featured = items.slice(0, 6);
  if (failed || !items.length) return null;
  const L = language === 'en' ? {
    eyebrow: 'THE COLLECTION / S21', title: 'Photo collection', tagline: 'A visual archive of Kim ChaeWon.', view: 'Explore all photographs', count: 'PHOTOGRAPHS', unknown: 'Date unverified',
  } : language === 'ja' ? {
    eyebrow: 'THE COLLECTION / S21', title: 'フォトコレクション', tagline: 'キム・チェウォンの写真アーカイブ', view: 'すべての写真を見る', count: '枚の写真', unknown: '撮影日未確認',
  } : {
    eyebrow: 'THE COLLECTION / S21', title: '사진 컬렉션', tagline: '김채원의 순간들을 한곳에 모았습니다.', view: '전체 사진 보기', count: 'PHOTOGRAPHS', unknown: '촬영일 미확인',
  };
  return <section className="cw-featured" aria-labelledby="cw-featured-heading">
    <div className="shion-content-width cw-featured-inner">
      <div className="cw-featured-intro">
        <div><p className="cw-featured-eyebrow">{L.eyebrow}</p><h2 id="cw-featured-heading">{L.title}</h2><p className="cw-featured-sub">{L.tagline}</p></div>
        <div className="cw-featured-aside"><span className="cw-featured-num">{items.length.toLocaleString()}</span><span>{L.count}</span></div>
      </div>
      <div className="cw-featured-grid">
        {featured.map((photo,i) => <a key={photo.id} href={`${PATH}?photo=${encodeURIComponent(photo.id)}`} className="cw-featured-tile" aria-label={`${photo.title}, ${photo.album}`}>
          <div className="cw-featured-visual"><img src={photo.url} alt={photo.title} loading="lazy" decoding="async"/><span className="cw-featured-index">{String(i+1).padStart(2,'0')}</span></div>
          <div className="cw-featured-meta"><strong>{photo.album}</strong><span>{photo.date || (photo.year ? `${photo.year} · ${L.unknown}` : L.unknown)}</span></div>
        </a>)}
      </div>
      <a href={PATH} className="cw-featured-more">{L.view}<span aria-hidden="true">↗</span></a>
    </div>
  </section>;
}

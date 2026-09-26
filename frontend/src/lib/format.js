const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

/**
 * Genius отдаёт дату по-разному: полную ("2000-01-31"), только месяц
 * ("2000-01") или только год ("2000") — Genius сам не всегда знает точный день.
 * Форматируем настолько подробно, насколько позволяют данные.
 */
export function formatReleaseDate(dateStr) {
  if (!dateStr) return "";

  const match = dateStr.match(/^(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?$/);
  if (!match) return dateStr; // неожиданный формат — показываем как есть, не гадаем

  const [, year, month, day] = match;
  if (day) return `${MONTHS[Number(month) - 1]} ${Number(day)}, ${year}`;
  if (month) return `${MONTHS[Number(month) - 1]} ${year}`;
  return year;
}

let measureCtx = null;
function getMeasureContext(font) {
  if (!measureCtx) measureCtx = document.createElement("canvas").getContext("2d");
  measureCtx.font = font;
  return measureCtx;
}

/**
 * Обрезает список имён (продюсеры и т.п.) с конца — целыми именами, не по буквам —
 * пока строка не влезет в maxWidthPx. В отличие от CSS text-overflow:ellipsis,
 * никогда не показывает половину имени: либо оно целиком, либо его нет вообще.
 * Требует реальный canvas.measureText(), поэтому чистым CSS не решается.
 */
/** Компактный формат числа подписчиков: 1234567 -> "1.2M", 3400 -> "3.4K". */
export function formatFollowers(n) {
  if (!n) return null;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

export function truncateNameList(names, maxWidthPx, font = "12px Roboto, system-ui, sans-serif") {
  if (!names || names.length === 0) return "";
  const ctx = getMeasureContext(font);
  const render = (count) => names.slice(0, count).join(", ") + (count < names.length ? "…" : "");

  let count = names.length;
  while (count > 0 && ctx.measureText(render(count)).width > maxWidthPx) {
    count -= 1;
  }
  return count > 0 ? render(count) : "…";
}

// Genius отдаёт album_type строчными ("album", "ep", "single", "mixtape",
// "compilation"...). Порядок задаёт последовательность секций на странице
// артиста; всё, чего нет в списке (в т.ч. отсутствующий album_type),
// уходит в "Other" и показывается последним.
const ALBUM_TYPE_ORDER = ["album", "ep", "single", "mixtape", "compilation", "video"];

const ALBUM_TYPE_LABELS = {
  album: "Albums",
  ep: "EPs",
  single: "Singles",
  mixtape: "Mixtapes",
  compilation: "Compilations",
  video: "Videos",
};

/** Название секции дискографии артиста для данного album_type. */
export function albumTypeSectionTitle(albumType) {
  if (!albumType) return "Other";
  const key = albumType.toLowerCase();
  if (ALBUM_TYPE_LABELS[key]) return ALBUM_TYPE_LABELS[key];
  return `${key.charAt(0).toUpperCase()}${key.slice(1)}s`;
}

/** Группирует альбомы артиста по типу, сохраняя порядок ALBUM_TYPE_ORDER,
 * с неизвестными типами в конце (в порядке появления). */
export function groupAlbumsByType(albums) {
  const groups = new Map();
  for (const album of albums) {
    const key = (album.album_type || "").toLowerCase() || "other";
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(album);
  }

  const orderedKeys = [
    ...ALBUM_TYPE_ORDER.filter((key) => groups.has(key)),
    ...[...groups.keys()].filter((key) => !ALBUM_TYPE_ORDER.includes(key)),
  ];

  return orderedKeys.map((key) => ({
    key,
    title: albumTypeSectionTitle(key === "other" ? null : key),
    albums: groups.get(key),
  }));
}

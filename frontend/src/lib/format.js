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

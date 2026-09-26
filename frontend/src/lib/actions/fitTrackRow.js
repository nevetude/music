/**
 * Svelte action для строки трека в треклисте альбома.
 *
 * Приоритеты при нехватке ширины:
 * 1. Первый продюсер показывается всегда целиком.
 * 2. Если полное название трека помещается — сохраняем его целиком.
 * 3. Всё оставшееся место отдаём дополнительным продюсерам.
 * 4. Если название само слишком длинное — оно сокращается CSS-эллипсисом
 *    (см. .track-title в app.css), но первый продюсер всё равно остаётся целиком.
 *
 * Требует реальный canvas.measureText(), поэтому чистым CSS не решается —
 * ужимать список продюсеров по словам (а не по буквам) без замера текста нельзя.
 *
 * Использование: <div class="track-content" use:fitTrackRow={track.producers}>
 * с дочерними .track-title и .track-producer внутри node.
 */
export function fitTrackRow(node, producers) {
  const title = node.querySelector(".track-title");
  const producer = node.querySelector(".track-producer");

  if (!title || !producer || !producers?.length) return;

  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");
  const gap = 12;

  function measure(element, text) {
    ctx.font = getComputedStyle(element).font;
    return ctx.measureText(text).width;
  }

  function update() {
    const rowWidth = node.clientWidth;

    const titleText = title.textContent.trim();
    const titleWidth = measure(title, titleText);

    const firstProducer = producers[0];
    const firstProducerWidth = measure(producer, firstProducer);

    const titleCanFit = titleWidth + gap + firstProducerWidth <= rowWidth;

    const reservedTitleWidth = titleCanFit
      ? titleWidth
      : Math.max(0, rowWidth - gap - firstProducerWidth);

    const availableForProducers = Math.max(
      firstProducerWidth,
      rowWidth - reservedTitleWidth - gap,
    );

    let visible = firstProducer;
    let truncated = false;

    for (let i = 1; i < producers.length; i++) {
      const candidate = `${visible}, ${producers[i]}`;
      const hasMore = i < producers.length - 1;

      // Если после этого продюсера ещё кто-то останется,
      // сразу резервируем место под многоточие.
      const rendered = hasMore ? `${candidate}…` : candidate;
      const candidateWidth = measure(producer, rendered);

      if (candidateWidth <= availableForProducers) {
        visible = candidate;
      } else {
        truncated = true;
        break;
      }
    }

    if (truncated) {
      // Многоточие должно помещаться вместе с последним
      // полностью отображаемым именем.
      while (
        visible !== firstProducer &&
        measure(producer, `${visible}…`) > availableForProducers
      ) {
        const parts = visible.split(", ");
        parts.pop();
        visible = parts.join(", ");
      }
      visible += "…";
    }

    const finalWidth = measure(producer, visible);

    producer.textContent = visible;
    producer.style.width = `${Math.ceil(finalWidth)}px`;
    producer.style.flexBasis = `${Math.ceil(finalWidth)}px`;
  }

  const observer = new ResizeObserver(update);
  observer.observe(node);

  document.fonts?.ready.then(update);
  update();

  return {
    update(nextProducers) {
      producers = nextProducers;
      update();
    },

    destroy() {
      observer.disconnect();
    },
  };
}

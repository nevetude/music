<script>
  import { link } from "svelte-spa-router";
  import { api } from "../lib/api.js";
  import { formatReleaseDate } from "../lib/format.js";

  let { params } = $props();

  let album = $state(null);
  let loading = $state(true);
  let error = $state(null);

  const DESCRIPTION_COLLAPSED_HEIGHT = 70;

  let descRef = $state(null);
  let descFullHeight = $state(0);
  let descExpanded = $state(false);
  let descNeedsToggle = $derived(descFullHeight > DESCRIPTION_COLLAPSED_HEIGHT + 4);

  $effect(() => {
    void album?.description_preview;
    void descRef;

    descExpanded = false;

    queueMicrotask(() => {
      if (descRef) descFullHeight = descRef.scrollHeight;
    });
  });

  let stretchBlock = $derived(
    album && Object.keys(album.credits).length > 0
      ? "credits"
      : album?.description_preview
        ? "description"
        : null,
  );

  $effect(() => {
    loading = true;
    error = null;

    api
      .getAlbum(params.id)
      .then((data) => (album = data))
      .catch((e) => (error = e.message))
      .finally(() => (loading = false));
  });

  const roleOrder = [
    "Producer",
    "Producers",
    "Featuring",
    "Writer",
    "Writers",
    "Distributor",
  ];

  function sortedRoles(credits) {
    const keys = Object.keys(credits);

    return keys.sort((a, b) => {
      const ia = roleOrder.indexOf(a);
      const ib = roleOrder.indexOf(b);

      return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib);
    });
  }

function fitTrackRow(node, producers) {
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

    /*
     * Приоритеты:
     *
     * 1. Первый продюсер показывается всегда целиком.
     * 2. Если полное название трека помещается — сохраняем его целиком.
     * 3. Всё оставшееся место отдаём дополнительным продюсерам.
     * 4. Если название само слишком длинное — оно сокращается,
     *    но первый продюсер всё равно остаётся целиком.
     */

    const titleCanFit =
      titleWidth + gap + firstProducerWidth <= rowWidth;

    const reservedTitleWidth = titleCanFit
      ? titleWidth
      : Math.max(0, rowWidth - gap - firstProducerWidth);

    const availableForProducers = Math.max(
      firstProducerWidth,
      rowWidth - reservedTitleWidth - gap,
    );

    let visible = firstProducer;
    let visibleWidth = firstProducerWidth;
    let truncated = false;

    for (let i = 1; i < producers.length; i++) {
      const candidate = `${visible}, ${producers[i]}`;
      const hasMore = i < producers.length - 1;

      /*
       * Если после этого продюсера ещё кто-то останется,
       * сразу резервируем место под многоточие.
       */
      const rendered = hasMore ? `${candidate}…` : candidate;
      const candidateWidth = measure(producer, rendered);

      if (candidateWidth <= availableForProducers) {
        visible = candidate;
        visibleWidth = measure(producer, visible);
      } else {
        truncated = true;
        break;
      }
    }

    if (truncated) {
      /*
       * Многоточие должно помещаться вместе с последним
       * полностью отображаемым именем.
       */
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
</script>

{#if loading}
  <p class="text-soft">Loading…</p>
{:else if error}
  <p class="text-soft">Failed to load album: {error}</p>
{:else if album}
  <div class="release-layout">
    <aside class="release-aside">
      <section
        class="release-summary"
        class:tinted={album.album_art_secondary_color}
        style:--cover={album.album_art_secondary_color}
      >
        <figure class="cover">
          {#if album.cover_art_url}
            <img
              src={album.cover_art_url}
              width="240"
              height="240"
              alt="{album.name} cover"
            />
          {/if}
        </figure>

        <div class="controls" aria-hidden="true"></div>
      </section>

      <section class="release-tracklist">
        <ol role="list" class="tracklist">
          {#each album.tracks as track (track.song_id)}
            <li class="track">
              <a href="/songs/{track.song_id}" use:link class="track-link">
                <span class="track-num">{track.number ?? ""}</span>

                {#if track.cover_thumbnail_url}
                  <img
                    src={track.cover_thumbnail_url}
                    class="tracklist-cover"
                    alt="{track.title} cover"
                  />
                {:else}
                  <span class="tracklist-cover"></span>
                {/if}

                <div
                  class="track-content"
                  use:fitTrackRow={track.producers}
                >
                  <span class="track-title">
                    {track.title}{#if track.featuring.length > 0}<span class="track-feat"
                      >&nbsp;(feat. {track.featuring.join(", ")})</span
                    >{/if}
                  </span>

                  {#if track.producers.length > 0}
                    <span
                      class="track-producer"
                      title={track.producers.join(", ")}
                    ></span>
                  {/if}
                </div>
              </a>
            </li>
          {/each}
        </ol>
      </section>
    </aside>

    <section class="release-details">
      <article class="main-info">
        <div class="release-header">
          <h2 class="release-title">
            {#if album.url}
              <a href={album.url} target="_blank" rel="noreferrer">
                {album.name}
              </a>
            {:else}
              {album.name}
            {/if}
          </h2>

          <div class="album-ratings">
            <span class="rating-badge">10</span>
          </div>
        </div>

        {#if album.artists.length > 0}
          <p class="release-artist-line">
            {#each album.artists as artist, i (artist.id)}
              <a
                href="/artists/{artist.id}"
                use:link
                class="release-artist"
              >
                {artist.name}
              </a>

              {#if i < album.artists.length - 1}
                <span>,&nbsp;</span>
              {/if}
            {/each}
          </p>
        {/if}

        <dl class="release-meta">
          {#if album.album_type}
            <dt>Format</dt>
            <dd>{album.album_type}</dd>
          {/if}

          {#if album.release_date}
            <dt>Released</dt>
            <dd>{formatReleaseDate(album.release_date)}</dd>
          {/if}

          {#if album.country}
            <dt>Country</dt>
            <dd>{album.country}</dd>
          {/if}

          {#if album.language_name}
            <dt>Language</dt>
            <dd>{album.language_name}</dd>
          {/if}

          {#if album.label.length > 0}
            <dt>Label</dt>
            <dd>{album.label.join(", ")}</dd>
          {/if}

          {#if album.genres.length > 0}
            <dt>Genre</dt>
            <dd class="genres">{album.genres.join(", ")}</dd>
          {/if}
        </dl>

        {#if album.album_art_primary_color || album.album_art_secondary_color}
          <div class="release-footer">
            {#if album.album_art_primary_color}
              <div class="color-swatch">
                <span
                  class="swatch-box"
                  style="background: {album.album_art_primary_color}"
                ></span>
                <span class="swatch-hex">
                  {album.album_art_primary_color}
                </span>
              </div>
            {/if}

            {#if album.album_art_secondary_color}
              <div class="color-swatch">
                <span
                  class="swatch-box"
                  style="background: {album.album_art_secondary_color}"
                ></span>
                <span class="swatch-hex">
                  {album.album_art_secondary_color}
                </span>
              </div>
            {/if}

            <span class="release-id">#{album.id}</span>
          </div>
        {/if}
      </article>

      {#if album.description_preview}
        <article
          class="album-info"
          class:stretch={stretchBlock === "description"}
        >
          <h5>Description</h5>

          <div
            class="description"
            bind:this={descRef}
            style="max-height: {descExpanded
              ? descFullHeight + 'px'
              : DESCRIPTION_COLLAPSED_HEIGHT + 'px'}"
          >
            <p>{album.description_preview}</p>
          </div>

          {#if descNeedsToggle}
            <button
              class="show-more-btn"
              onclick={() => (descExpanded = !descExpanded)}
            >
              {descExpanded ? "Show less" : "Show more"}
            </button>
          {/if}
        </article>
      {/if}

      {#if Object.keys(album.credits).length > 0}
        <article
          class="album-info"
          class:stretch={stretchBlock === "credits"}
        >
          <h5>Credits</h5>

          <dl class="release-meta">
            {#each sortedRoles(album.credits) as role (role)}
              <dt>{role}</dt>
              <dd>{album.credits[role].join(", ")}</dd>
            {/each}
          </dl>
        </article>
      {/if}

      {#if album.cover_arts.length > 1}
        <article class="album-info">
          <h5>Cover arts</h5>

          <div class="physical-gallery">
            {#each album.cover_arts as cover (cover.image_url)}
              <div class="physical-item">
                <img
                  src={cover.thumbnail_image_url ?? cover.image_url}
                  alt="{album.name} cover"
                />
                <span class="format-label">
                  {cover.label ?? "Cover"}
                </span>
              </div>
            {/each}
          </div>
        </article>
      {/if}
    </section>
  </div>
{/if}
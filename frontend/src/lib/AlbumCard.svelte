<script>
  import { link } from "svelte-spa-router";

  let { album } = $props();

  function year(dateStr) {
    // release_date из Genius не всегда ISO ("March 3, 2023" и т.п.),
    // поэтому просто ищем первые 4 цифры подряд, а не режем по позиции.
    const match = dateStr && dateStr.match(/\d{4}/);
    return match ? match[0] : "";
  }
</script>

<a href="/albums/{album.id}" use:link class="album-card">
  <div class="album-card-cover">
    {#if album.cover_art_url}
      <img src={album.cover_art_url} alt={album.name} loading="lazy" />
    {/if}
  </div>
  <span class="album-card-name">{album.name}</span>
  <div class="album-card-meta">
    <span class="album-card-artists">{album.artists.map((a) => a.name).join(", ")}</span>
    <span class="album-card-year">{year(album.release_date)}</span>
  </div>
</a>

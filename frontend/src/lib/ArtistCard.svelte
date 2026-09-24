<script>
  import { link } from "svelte-spa-router";

  let { artist } = $props();

  function formatFollowers(n) {
    if (!n) return null;
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
    return String(n);
  }
</script>

<a href="/artists/{artist.id}" use:link class="artist-card">
  <div class="artist-card-avatar">
    {#if artist.image_url}
      <img src={artist.image_url} alt={artist.name} loading="lazy" />
    {/if}
  </div>
  <span class="artist-card-name">{artist.name}</span>
  {#if formatFollowers(artist.followers_count)}
    <span class="artist-card-followers">{formatFollowers(artist.followers_count)} followers</span>
  {/if}
</a>

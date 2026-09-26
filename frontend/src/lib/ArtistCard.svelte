<script>
  import { link } from "./router.js";
  import { formatFollowers } from "./format.js";

  let { artist } = $props();
</script>

<a href="/artists/{artist.id}" use:link target="_blank" rel="noopener" class="artist-card">
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

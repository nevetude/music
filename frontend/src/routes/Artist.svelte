<script>
  import { api } from "../lib/api.js";
  import AlbumCard from "../lib/AlbumCard.svelte";

  let { params } = $props();

  let artist = $state(null);
  let loading = $state(true);
  let error = $state(null);

  $effect(() => {
    loading = true;
    error = null;
    api
      .getArtist(params.id)
      .then((data) => (artist = data))
      .catch((e) => (error = e.message))
      .finally(() => (loading = false));
  });
</script>

{#if loading}
  <p class="text-soft">Loading…</p>
{:else if error}
  <p class="text-soft">Failed to load artist: {error}</p>
{:else if artist}
  <section class="page-block">
    <div class="artist-header">
      {#if artist.image_url}
        <img class="artist-header-avatar" src={artist.image_url} alt={artist.name} />
      {/if}
      <div>
        <h2 class="release-title">{artist.name}</h2>
        {#if artist.followers_count}
          <p class="text-soft">{artist.followers_count.toLocaleString("en-US")} followers</p>
        {/if}
      </div>
    </div>

    {#if artist.description_preview}
      <p class="description">{artist.description_preview}</p>
    {/if}
  </section>

  <section class="page-block">
    <h3 class="page-title">Albums</h3>
    {#if artist.albums.length === 0}
      <p class="text-soft">No albums yet.</p>
    {:else}
      <div class="album-grid">
        {#each artist.albums as album (album.id)}
          <AlbumCard {album} />
        {/each}
      </div>
    {/if}
  </section>
{/if}

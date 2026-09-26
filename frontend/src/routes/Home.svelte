<script>
  import { api } from "../lib/api.js";
  import { useApiResource } from "../lib/useApiResource.svelte.js";
  import ArtistCard from "../lib/ArtistCard.svelte";

  const artistsResource = useApiResource(api.listArtists);
  artistsResource.load();

  let loading = $derived(artistsResource.loading);
  let error = $derived(artistsResource.error);

  // Три группы, в порядке приоритета: полностью распарсенные -> у кого хотя бы
  // есть альбомы -> все остальные (попали в базу только как соавторы/фиты).
  let artists = $derived(artistsResource.data ?? []);
  let fullArtists = $derived(artists.filter((a) => a.full));
  let withAlbumsArtists = $derived(artists.filter((a) => !a.full && a.has_albums));
  let otherArtists = $derived(artists.filter((a) => !a.full && !a.has_albums));
</script>

{#if loading}
  <section class="page-block">
    <p class="text-soft">Loading…</p>
  </section>
{:else if error}
  <section class="page-block">
    <p class="text-soft">Failed to load artists: {error}</p>
  </section>
{:else if artists.length === 0}
  <section class="page-block">
    <p class="text-soft">No artists in the database yet.</p>
  </section>
{:else}
  {#if fullArtists.length > 0}
    <section class="page-block">
      <h2 class="page-title">Fully parsed</h2>
      <div class="artist-grid">
        {#each fullArtists as artist (artist.id)}
          <ArtistCard {artist} />
        {/each}
      </div>
    </section>
  {/if}

  {#if withAlbumsArtists.length > 0}
    <section class="page-block">
      <h2 class="page-title">With albums</h2>
      <div class="artist-grid">
        {#each withAlbumsArtists as artist (artist.id)}
          <ArtistCard {artist} />
        {/each}
      </div>
    </section>
  {/if}

  {#if otherArtists.length > 0}
    <section class="page-block">
      <h2 class="page-title">Other artists</h2>
      <div class="artist-grid">
        {#each otherArtists as artist (artist.id)}
          <ArtistCard {artist} />
        {/each}
      </div>
    </section>
  {/if}
{/if}

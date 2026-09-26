<script>
  import { link } from "../lib/router.js";
  import { api } from "../lib/api.js";
  import { useApiResource } from "../lib/useApiResource.svelte.js";
  import { groupAlbumsByType, formatFollowers } from "../lib/format.js";
  import { fitTrackRow } from "../lib/actions/fitTrackRow.js";
  import AlbumCard from "../lib/AlbumCard.svelte";

  let { params } = $props();

  const artistResource = useApiResource(api.getArtist);

  $effect(() => {
    artistResource.load(params.id);
  });

  let artist = $derived(artistResource.data);
  let loading = $derived(artistResource.loading);
  let error = $derived(artistResource.error);

  const DESCRIPTION_COLLAPSED_HEIGHT = 70;

  let descRef = $state(null);
  let descFullHeight = $state(0);
  let descExpanded = $state(false);
  let descNeedsToggle = $derived(descFullHeight > DESCRIPTION_COLLAPSED_HEIGHT + 4);

  $effect(() => {
    void artist?.description_preview;
    void descRef;

    descExpanded = false;

    queueMicrotask(() => {
      if (descRef) descFullHeight = descRef.scrollHeight;
    });
  });

  let stretchBlock = $derived(artist?.description_preview ? "description" : null);

  // Секции дискографии по типу альбома (Albums / EPs / Singles / ...). "Collab" —
  // фильтр внутри конкретной секции: показывает только альбомы, где у артиста
  // есть соавторы (artists.length > 1). Ключ секции -> boolean.
  let albumGroups = $derived(artist ? groupAlbumsByType(artist.albums) : []);
  let collabFilters = $state({});

  function toggleCollab(key) {
    collabFilters[key] = !collabFilters[key];
  }

  function visibleAlbums(group) {
    return collabFilters[group.key] ? group.albums.filter((a) => a.artists.length > 1) : group.albums;
  }

  function hasCollab(group) {
    return group.albums.some((a) => a.artists.length > 1);
  }
</script>

{#if loading}
  <p class="text-soft">Loading…</p>
{:else if error}
  <p class="text-soft">Failed to load artist: {error}</p>
{:else if artist}
  <div class="release-layout">
    <aside class="release-aside">
      <section class="release-summary">
        <figure class="cover cover-sm">
          {#if artist.image_url}
            <img src={artist.image_url} width="160" height="160" alt={artist.name} />
          {/if}
        </figure>

        <div class="controls controls-sm" aria-hidden="true"></div>
      </section>

      <section class="release-tracklist">
        <ol role="list" class="tracklist">
          {#each artist.top_tracks as track (track.song_id)}
            <li class="track">
              <a href="/songs/{track.song_id}" use:link target="_blank" rel="noopener" class="track-link">
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

                <div class="track-content" use:fitTrackRow={track.producers}>
                  <span class="track-title">
                    {track.title}{#if track.featuring.length > 0}<span class="track-feat"
                      >&nbsp;(feat. {track.featuring.join(", ")})</span
                    >{/if}
                  </span>

                  {#if track.producers.length > 0}
                    <span class="track-producer" title={track.producers.join(", ")}></span>
                  {/if}
                </div>
              </a>
            </li>
          {:else}
            <li class="text-soft" style="padding: 10px 8px;">No tracks yet.</li>
          {/each}
        </ol>
      </section>
    </aside>

    <section class="release-details">
      <article class="main-info">
        <div class="release-header">
          <h2 class="release-title">
            {#if artist.url}
              <a href={artist.url} target="_blank" rel="noreferrer">
                {artist.name}
              </a>
            {:else}
              {artist.name}
            {/if}
          </h2>

          {#if artist.is_verified}
            <div class="album-ratings">
              <span class="rating-badge">✓ Verified</span>
            </div>
          {/if}
        </div>

        <dl class="release-meta">
          {#if formatFollowers(artist.followers_count)}
            <dt>Followers</dt>
            <dd>{formatFollowers(artist.followers_count)}</dd>
          {/if}

          {#if artist.is_verified !== null && artist.is_verified !== undefined}
            <dt>Verified</dt>
            <dd>{artist.is_verified ? "Yes" : "No"}</dd>
          {/if}

          {#if artist.alternate_names.length > 0}
            <dt>Also known as</dt>
            <dd>{artist.alternate_names.join(", ")}</dd>
          {/if}
        </dl>

        <div class="release-footer">
          <span class="release-id">#{artist.id}</span>
        </div>
      </article>

      {#if artist.description_preview}
        <article class="album-info" class:stretch={stretchBlock === "description"}>
          <h5>Description</h5>

          <div
            class="description"
            bind:this={descRef}
            style="max-height: {descExpanded
              ? descFullHeight + 'px'
              : DESCRIPTION_COLLAPSED_HEIGHT + 'px'}"
          >
            <p>{artist.description_preview}</p>
          </div>

          {#if descNeedsToggle}
            <button class="show-more-btn" onclick={() => (descExpanded = !descExpanded)}>
              {descExpanded ? "Show less" : "Show more"}
            </button>
          {/if}
        </article>
      {/if}
    </section>
  </div>

  {#if albumGroups.length === 0}
    <section class="page-block">
      <h3 class="page-title">Albums</h3>
      <p class="text-soft">No albums yet.</p>
    </section>
  {:else}
    {#each albumGroups as group (group.key)}
      <section class="page-block">
        <div class="page-title-row">
          <h3 class="page-title">{group.title}</h3>
          {#if hasCollab(group)}
            <button
              class="collab-toggle"
              class:active={collabFilters[group.key]}
              onclick={() => toggleCollab(group.key)}
            >
              Collab
            </button>
          {/if}
        </div>

        {#if visibleAlbums(group).length === 0}
          <p class="text-soft">No collaborative albums.</p>
        {:else}
          <div class="album-grid">
            {#each visibleAlbums(group) as album (album.id)}
              <AlbumCard {album} />
            {/each}
          </div>
        {/if}
      </section>
    {/each}
  {/if}
{/if}

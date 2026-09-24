<script>
  import { link } from "svelte-spa-router";
  import { api } from "../lib/api.js";

  let { params } = $props();

  let song = $state(null);
  let loading = $state(true);
  let error = $state(null);

  $effect(() => {
    loading = true;
    error = null;
    api
      .getSong(params.id)
      .then((data) => (song = data))
      .catch((e) => (error = e.message))
      .finally(() => (loading = false));
  });
</script>

{#if loading}
  <p class="text-soft">Loading…</p>
{:else if error}
  <p class="text-soft">Failed to load track: {error}</p>
{:else if song}
  <div class="release-layout">
    <aside class="release-aside">
      <section class="release-summary">
        <figure class="cover">
          {#if song.song_art_image_url}
            <img src={song.song_art_image_url} width="240" height="240" alt="{song.title} cover" />
          {/if}
        </figure>
      </section>
    </aside>

    <section class="release-details">
      <article class="main-info">
        <div class="release-header">
          <h2 class="release-title">
            {#if song.url}
              <a href={song.url} target="_blank" rel="noreferrer">{song.title}</a>
            {:else}
              {song.title}
            {/if}
          </h2>
        </div>

        {#if song.artists.length > 0}
          <p class="release-artist-line">
            {#each song.artists as artist, i (artist.id)}
              <a href="/artists/{artist.id}" use:link class="release-artist">{artist.name}</a
              >{#if i < song.artists.length - 1}<span>,&nbsp;</span>{/if}
            {/each}
          </p>
        {/if}

        <dl class="release-meta">
          {#if song.release_date}
            <dt>Released</dt>
            <dd>{song.release_date}</dd>
          {/if}

          {#if song.country}
            <dt>Country</dt>
            <dd>{song.country}</dd>
          {/if}

          {#if song.language_name}
            <dt>Language</dt>
            <dd>{song.language_name}</dd>
          {/if}

          {#if song.pageviews}
            <dt>Views</dt>
            <dd>{song.pageviews.toLocaleString("en-US")}</dd>
          {/if}

          {#if song.instrumental}
            <dt>Instrumental</dt>
            <dd>Yes</dd>
          {/if}

          <!-- Genres — всегда последними -->
          {#if song.genres.length > 0}
            <dt>Genres</dt>
            <dd class="genres">{song.genres.join(", ")}</dd>
          {/if}
        </dl>
      </article>

      {#if song.description_preview}
        <article class="album-info">
          <h5>Description</h5>
          <section class="description">
            <p>{song.description_preview}</p>
          </section>
        </article>
      {/if}

      {#if Object.keys(song.credits).length > 0}
        <article class="album-info">
          <h5>Credits</h5>
          <dl class="release-meta">
            {#each Object.keys(song.credits) as role (role)}
              <dt>{role}</dt>
              <dd>{song.credits[role].join(", ")}</dd>
            {/each}
          </dl>
        </article>
      {/if}

      {#if song.albums.length > 0}
        <article class="album-info">
          <h5>Appears on</h5>
          <p>
            {#each song.albums as a, i (a.id)}
              <a href="/albums/{a.id}" use:link>{a.name}</a
              >{#if i < song.albums.length - 1}<span>,&nbsp;</span>{/if}
            {/each}
          </p>
        </article>
      {/if}

      <article class="album-info">
        <h5>Lyrics</h5>
        <section class="description lyrics-placeholder">
          <p>Lyrics for this track haven't been loaded yet.</p>
        </section>
      </article>
    </section>
  </div>
{/if}

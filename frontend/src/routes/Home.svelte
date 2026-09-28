<script>
  import { api } from "../lib/api.js";
  import { useApiResource } from "../lib/useApiResource.svelte.js";
  import { sortArtists } from "../lib/format.js";
  import ArtistCard from "../lib/ArtistCard.svelte";
  import SortSelect from "../lib/SortSelect.svelte";

  const artistsResource = useApiResource(api.listArtists);
  artistsResource.load();

  let loading = $derived(artistsResource.loading);
  let error = $derived(artistsResource.error);

  const SORT_OPTIONS = [
    { value: "popularity", label: "Popularity" },
    { value: "alphabet", label: "Alphabet" },
  ];

  // Режим сортировки — отдельный для каждой секции. Ключ секции -> режим.
  let sortModes = $state({});

  // Три группы, в порядке приоритета: полностью распарсенные -> у кого хотя бы
  // есть альбомы -> все остальные (попали в базу только как соавторы/фиты).
  let artists = $derived(artistsResource.data ?? []);
  let sections = $derived(
    [
      { key: "full", title: "Fully parsed", list: artists.filter((a) => a.full) },
      {
        key: "withAlbums",
        title: "With albums",
        list: artists.filter((a) => !a.full && a.has_albums),
      },
      {
        key: "other",
        title: "Other artists",
        list: artists.filter((a) => !a.full && !a.has_albums),
      },
    ].filter((section) => section.list.length > 0),
  );
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
  {#each sections as section (section.key)}
    <section class="page-block">
      <div class="page-title-row">
        <h2 class="page-title">{section.title}</h2>
        {#if section.list.length > 1}
          <SortSelect
            options={SORT_OPTIONS}
            value={sortModes[section.key] ?? "popularity"}
            onchange={(mode) => (sortModes[section.key] = mode)}
          />
        {/if}
      </div>
      <div class="artist-grid">
        {#each sortArtists(section.list, sortModes[section.key] ?? "popularity") as artist (artist.id)}
          <ArtistCard {artist} />
        {/each}
      </div>
    </section>
  {/each}
{/if}

<script>
  import Router from "svelte-spa-router";
  import Header from "./lib/Header.svelte";
  import Home from "./routes/Home.svelte";
  import Artist from "./routes/Artist.svelte";
  import Album from "./routes/Album.svelte";
  import Song from "./routes/Song.svelte";

  const routes = {
    "/": Home,
    "/artists/:id": Artist,
    "/albums/:id": Album,
    "/songs/:id": Song,
  };
</script>

<Header />
<main>
  <Router {routes} />
</main>

<script>
  import { link } from "./router.js";
  import { theme, toggleTheme } from "./theme.js";
</script>

<header>
  <a href="/" use:link class="header-home-link" aria-label="Home"></a>

  <div class="theme-switcher">
    <input type="checkbox" id="theme-toggle" checked={$theme === "light"} onchange={toggleTheme} />
    <label for="theme-toggle"></label>
  </div>
</header>
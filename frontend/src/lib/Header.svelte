<script>
  import { theme, toggleTheme } from "./theme.js";
</script>

<header>
  <div class="theme-switcher">
    <input type="checkbox" id="theme-toggle" checked={$theme === "light"} onchange={toggleTheme} />
    <label for="theme-toggle"></label>
  </div>
</header>

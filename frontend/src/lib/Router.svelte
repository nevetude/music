<script>
  import { path } from "./router.js";

  let { routes } = $props();

  function compileRoute(pattern) {
    const paramNames = [];
    const regexStr = pattern.replace(/\/:([^/]+)/g, (_, name) => {
      paramNames.push(name);
      return "/([^/]+)";
    });
    return { regex: new RegExp(`^${regexStr}$`), paramNames };
  }

  let compiled = $derived(
    Object.entries(routes).map(([pattern, component]) => ({
      ...compileRoute(pattern),
      component,
    })),
  );

  let matched = $derived.by(() => {
    const pathname = $path.split("?")[0];
    for (const route of compiled) {
      const found = pathname.match(route.regex);
      if (found) {
        const params = {};
        route.paramNames.forEach((name, i) => (params[name] = found[i + 1]));
        return { component: route.component, params };
      }
    }
    return null;
  });
</script>

{#if matched}
  {@const Comp = matched.component}
  <Comp params={matched.params} />
{:else}
  <p class="text-soft">Page not found.</p>
{/if}

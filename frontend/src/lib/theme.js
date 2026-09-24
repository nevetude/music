import { writable } from "svelte/store";

const initial = document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";

export const theme = writable(initial);

theme.subscribe((value) => {
  document.documentElement.setAttribute("data-theme", value);
  localStorage.setItem("theme", value);
});

export function toggleTheme() {
  theme.update((current) => (current === "light" ? "dark" : "light"));
}

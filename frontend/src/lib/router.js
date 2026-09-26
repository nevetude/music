import { writable } from "svelte/store";

/**
 * Минимальный history-роутер без хэша. Заменяет svelte-spa-router:
 * тот же принцип (store + action), но URL вида /albums/1, а не #/albums/1.
 *
 * Требование к хостингу: сервер должен отдавать index.html на любой путь
 * (SPA-фолбэк) — Vite dev-сервер делает это из коробки, для прод-раздачи
 * нужен try_files/_redirects на стороне статического хостинга.
 */

function currentPath() {
  return window.location.pathname + window.location.search;
}

export const path = writable(currentPath());

window.addEventListener("popstate", () => path.set(currentPath()));

export function navigate(to) {
  if (to !== currentPath()) {
    history.pushState({}, "", to);
    path.set(currentPath());
  }
}

/**
 * Action для <a href="...">: перехватывает обычный клик и делает
 * pushState вместо перезагрузки документа. Ссылки с модификаторами
 * (ctrl/cmd/shift/alt), среднюю кнопку мыши, target и внешние домены
 * не трогает — браузер обрабатывает их сам.
 */
export function link(node) {
  function onClick(event) {
    if (
      event.defaultPrevented ||
      event.button !== 0 ||
      event.metaKey ||
      event.ctrlKey ||
      event.shiftKey ||
      event.altKey ||
      node.hasAttribute("target") ||
      node.hasAttribute("download") ||
      node.origin !== window.location.origin
    ) {
      return;
    }
    event.preventDefault();
    navigate(node.pathname + node.search);
  }

  node.addEventListener("click", onClick);
  return {
    destroy() {
      node.removeEventListener("click", onClick);
    },
  };
}

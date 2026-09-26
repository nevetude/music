/**
 * Оборачивает асинхронный запрос (обычно один из методов api.js) в
 * реактивный объект {data, loading, error} + метод load(...args).
 *
 * Раньше в каждом роуте повторялся один и тот же блок:
 *   let data = $state(null);
 *   let loading = $state(true);
 *   let error = $state(null);
 *   ...then/catch/finally...
 * Теперь это в одном месте, плюс защита от гонки: если params поменялись
 * до того как пришёл предыдущий ответ, устаревший результат тихо
 * игнорируется (актуален для Artist/Album/Song — там params.id меняется
 * при навигации между двумя страницами одного роута).
 *
 * Использование:
 *   const artist = useApiResource(api.getArtist);
 *   $effect(() => { artist.load(params.id); });
 *   ...
 *   {#if artist.loading} ... {:else if artist.error} ... {:else if artist.data} ...
 */
export function useApiResource(fetcher) {
  let data = $state(null);
  let loading = $state(true);
  let error = $state(null);
  let requestId = 0;

  async function load(...args) {
    const id = ++requestId;
    loading = true;
    error = null;

    try {
      const result = await fetcher(...args);
      if (id === requestId) data = result;
    } catch (e) {
      if (id === requestId) error = e.message;
    } finally {
      if (id === requestId) loading = false;
    }
  }

  return {
    get data() {
      return data;
    },
    get loading() {
      return loading;
    },
    get error() {
      return error;
    },
    load,
  };
}

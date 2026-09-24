const BASE = "/api";

async function get(path) {
  const response = await fetch(`${BASE}${path}`);
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
}

export const api = {
  listArtists: () => get("/artists"),
  getArtist: (id) => get(`/artists/${id}`),
  getAlbum: (id) => get(`/albums/${id}`),
  getSong: (id) => get(`/songs/${id}`),
};

from fastapi import APIRouter, HTTPException

from ..deps import SessionDep
from ..lookups import country_name, language_name
from ..naming import display_name
from ..repository import albums as albums_repo
from ..repository import songs as repo
from ..schemas import AlbumListItem, ArtistBrief, SongDetail

router = APIRouter(prefix="/api/songs", tags=["songs"])


def _artist_brief(artist) -> ArtistBrief:
    return ArtistBrief(id=artist.id, name=display_name(artist.name, artist.base_name))


@router.get("/{song_id}", response_model=SongDetail)
def get_song(song_id: int, session: SessionDep):
    song = repo.get_song(session, song_id)
    if song is None:
        raise HTTPException(status_code=404, detail="Песня не найдена")

    return SongDetail(
        **song.model_dump(),
        language_name=language_name(song.language),
        country=country_name(song.language),
        artists=[_artist_brief(a) for a in repo.get_song_artists(session, song_id)],
        genres=repo.get_song_genres(session, song_id),
        credits=repo.get_song_credits(session, song_id),
        albums=[
            AlbumListItem(
                **a.model_dump(),
                status=albums_repo.album_status(a.release_date),
                artists=[_artist_brief(ar) for ar in albums_repo.get_album_artists(session, a.id)],
            )
            for a in repo.get_song_albums(session, song_id)
        ],
    )

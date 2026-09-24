from fastapi import APIRouter, HTTPException

from ..database import SessionDep
from ..repository import albums as albums_repo
from ..repository import artists as repo
from ..schemas import AlbumListItem, ArtistBrief, ArtistDetail, ArtistListItem

router = APIRouter(prefix="/api/artists", tags=["artists"])


@router.get("", response_model=list[ArtistListItem])
def list_artists(session: SessionDep):
    artists = repo.list_artists(session)
    with_albums = repo.artist_ids_with_albums(session)
    return [
        ArtistListItem(**artist.model_dump(), has_albums=artist.id in with_albums)
        for artist in artists
    ]


@router.get("/{artist_id}", response_model=ArtistDetail)
def get_artist(artist_id: int, session: SessionDep):
    artist = repo.get_artist(session, artist_id)
    if artist is None:
        raise HTTPException(status_code=404, detail="Артист не найден")

    albums = repo.list_artist_albums(session, artist_id)
    album_items = [
        AlbumListItem(
            **album.model_dump(),
            artists=[
                ArtistBrief.model_validate(a)
                for a in albums_repo.get_album_artists(session, album.id)
            ],
        )
        for album in albums
    ]
    return ArtistDetail(**artist.model_dump(), albums=album_items)

from fastapi import APIRouter, HTTPException

from ..deps import SessionDep
from ..naming import display_name
from ..repository import albums as albums_repo
from ..repository import artists as repo
from ..schemas import AlbumListItem, ArtistBrief, ArtistDetail, ArtistListItem, TrackItem

router = APIRouter(prefix="/api/artists", tags=["artists"])


def _artist_brief(artist) -> ArtistBrief:
    return ArtistBrief(id=artist.id, name=display_name(artist.name, artist.base_name))


@router.get("", response_model=list[ArtistListItem])
def list_artists(session: SessionDep):
    artists = repo.list_artists(session)
    with_albums = repo.artist_ids_with_albums(session)
    items = []
    for artist in artists:
        fields = artist.model_dump()
        fields["name"] = display_name(artist.name, artist.base_name)
        items.append(ArtistListItem(**fields, has_albums=artist.id in with_albums))
    return items


@router.get("/{artist_id}", response_model=ArtistDetail)
def get_artist(artist_id: int, session: SessionDep):
    artist = repo.get_artist(session, artist_id)
    if artist is None:
        raise HTTPException(status_code=404, detail="Артист не найден")

    albums = repo.list_artist_albums(session, artist_id)
    album_items = [
        AlbumListItem(
            **album.model_dump(),
            status=albums_repo.album_status(album.release_date),
            artists=[_artist_brief(a) for a in albums_repo.get_album_artists(session, album.id)],
        )
        for album in albums
    ]
    artist_fields = artist.model_dump()
    artist_fields["name"] = display_name(artist.name, artist.base_name)
    return ArtistDetail(
        **artist_fields,
        alternate_names=repo.get_artist_alternate_names(session, artist_id),
        top_tracks=[TrackItem(**t) for t in repo.get_artist_top_tracks(session, artist_id)],
        albums=album_items,
    )

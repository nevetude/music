from fastapi import APIRouter, HTTPException

from ..deps import SessionDep
from ..lookups import country_name, language_name
from ..repository import albums as repo
from ..schemas import AlbumDetail, ArtistBrief, CoverArtItem, TrackItem

router = APIRouter(prefix="/api/albums", tags=["albums"])

# Genius отдаёт album_type строчными ("album", "single", "ep", "mixtape"...).
# EP — устоявшаяся аббревиатура, её не капитализируем как обычное слово.
ALBUM_TYPE_LABELS = {"ep": "EP"}


def format_album_type(value: str | None) -> str | None:
    if not value:
        return value
    return ALBUM_TYPE_LABELS.get(value.lower(), value.capitalize())


@router.get("/{album_id}", response_model=AlbumDetail)
def get_album(album_id: int, session: SessionDep):
    album = repo.get_album(session, album_id)
    if album is None:
        raise HTTPException(status_code=404, detail="Альбом не найден")

    credits = repo.get_album_performances(session, album_id)
    label = credits.pop("Label", [])  # Label показываем в основном блоке, не в Credits

    fields = album.model_dump()
    fields["album_type"] = format_album_type(fields["album_type"])

    return AlbumDetail(
        **fields,
        language_name=language_name(album.language),
        country=country_name(album.language),
        label=label,
        artists=[ArtistBrief.model_validate(a) for a in repo.get_album_artists(session, album_id)],
        genres=repo.get_album_genres(session, album_id),
        tracks=[TrackItem(**t) for t in repo.get_album_tracks(session, album_id)],
        credits=credits,
        cover_arts=[
            CoverArtItem.model_validate(c) for c in repo.get_album_cover_arts(session, album_id)
        ],
    )

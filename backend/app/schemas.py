from pydantic import BaseModel, ConfigDict


class ArtistListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    image_url: str | None = None
    followers_count: int | None = None
    full: bool = False
    has_albums: bool = False


class ArtistBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class AlbumListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    album_type: str | None = None
    release_date: str | None = None
    cover_art_url: str | None = None
    artists: list[ArtistBrief] = []


class ArtistDetail(ArtistListItem):
    url: str | None = None
    header_image_url: str | None = None
    description_preview: str | None = None
    albums: list[AlbumListItem] = []


class TrackItem(BaseModel):
    song_id: int
    number: int | None = None
    disc_number: int | None = None
    title: str
    url: str | None = None
    cover_thumbnail_url: str | None = None
    pageviews: int | None = None
    instrumental: bool | None = None
    producers: list[str] = []
    featuring: list[str] = []


class CoverArtItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    image_url: str | None = None
    thumbnail_image_url: str | None = None
    label: str | None = None


class AlbumDetail(BaseModel):
    id: int
    name: str
    full_title: str | None = None
    url: str | None = None
    album_type: str | None = None
    release_date: str | None = None
    language: str | None = None
    language_name: str | None = None
    country: str | None = None
    label: list[str] = []
    description_preview: str | None = None
    cover_art_url: str | None = None
    album_art_primary_color: str | None = None
    album_art_secondary_color: str | None = None
    song_pageviews: int | None = None
    artists: list[ArtistBrief] = []
    genres: list[str] = []
    tracks: list[TrackItem] = []
    credits: dict[str, list[str]] = {}
    cover_arts: list[CoverArtItem] = []


class SongDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    url: str | None = None
    release_date: str | None = None
    language: str | None = None
    language_name: str | None = None
    country: str | None = None
    pageviews: int | None = None
    instrumental: bool | None = None
    song_art_image_url: str | None = None
    description_preview: str | None = None
    artists: list[ArtistBrief] = []
    genres: list[str] = []
    credits: dict[str, list[str]] = {}
    albums: list[AlbumListItem] = []

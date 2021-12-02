from typing import Optional


class AnilistComicInfo:
    def __init__(
            self,
            tracker_id: int,
            title: str,  # userPreferred
            manga_format: str,  # format
            status: str,
            description: str,
            country_of_origin: str,
            original_source: str,
            genres: [str],
            writer: Optional[str],
            penciller: Optional[str],
            inker: Optional[str],
            synonyms: [str],
            is_adult: bool,
            site_url: str,
            chapters: Optional[int],  # Chapters is null if an ongoing series
            volumes: Optional[int],   # Volumes is null if ongoing
            tags: [str]
    ):
        self.tracker_id = tracker_id

        self.title = title
        self.altTitles = synonyms
        self.summary = description
        self.genres = ", ".join(genres+tags)

        self.status = status.lower()
        self.format = manga_format.lower().replace("_", " ")
        self.country_of_origin = country_of_origin
        self.original_source = original_source.lower()

        if is_adult:
            self.age_rating = "Adults Only 18+"
        else:
            self.age_rating = "G"

        if writer == "":
            self.writer = None
        else:
            self.writer = writer

        if penciller == "":
            self.penciller = None
        else:
            self.penciller = penciller

        if inker == "":
            self.inker = None
        else:
            self.inker = inker

        self.chapters = chapters
        self.volumes = volumes

        self.site_url = site_url
        self.scan_information = ""

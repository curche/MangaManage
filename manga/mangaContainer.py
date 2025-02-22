from manga.gateways.filesystem import FilesystemInterface
from manga.gateways.anilist import AnilistGateway
from manga.gateways.mangaupd import MangaUpdatesGateway
from manga.gateways.database import DatabaseGateway
from manga.mangagetchapter import CalculateChapterName
from manga.updateAnilistIds import UpdateTrackerIds
from manga.missingChapters import CheckGapsInChapters
from manga.createMetadata import CreateMetadata
from manga.createMetadata2 import CreateMetadata2
from manga.createMetadata3 import CreateMetadata3
from manga.deleteReadAnilist import DeleteReadChapters
from manga.checkMissingSQL import CheckMissingChaptersInSQL
from manga.checkForUpdates import CheckForUpdates


class MangaContainer:
    def __init__(
        self,
        config,
        database: DatabaseGateway,
        tracker: AnilistGateway,
        filesystem: FilesystemInterface,
        mangaUpdates: MangaUpdatesGateway,
    ) -> None:
        self.config = config
        self.database = database
        self.tracker = tracker
        self.filesystem = filesystem

        self.checkMissingSQL = CheckMissingChaptersInSQL(
            self.database,
            self.config["manga"]["sourcefolder"],
            self.config["manga"]["archivefolder"],
        )

        # parser = self.config["system"]["xmlParser"]
        # if parser == "lxml":
        #    self.createMetadata = CreateMetadata2(
        #        filesystem=self.filesystem, anilist=self.tracker)
        # elif parser == "ElementTree":
        #    self.createMetadata = CreateMetadata(filesystem=self.filesystem)
        self.createMetadata = CreateMetadata3(
            filesystem=self.filesystem, anilist=self.tracker
        )

        self.updateTrackerIds = UpdateTrackerIds(self.database, self.tracker)

        self.calculateChapterName = CalculateChapterName(self.tracker)

        self.deleteReadChapters = DeleteReadChapters(
            self.tracker, self.filesystem, self.database
        )

        self.checkGapsInChapters = CheckGapsInChapters(
            self.database, self.filesystem, self.tracker
        )

        self.checkForUpdates = CheckForUpdates(
            mangaUpdates, self.database, self.tracker
        )
        pass

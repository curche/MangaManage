import datetime
import glob
import re
import html
from typing import List, Optional, Set
from pathlib import Path
from cross.decorators import Logger
from manga.updateAnilistIds import UpdateTrackerIds
from manga.mangagetchapter import CalculateChapterName
from manga.deleteReadAnilist import DeleteReadChapters
from manga.missingChapters import CheckGapsInChapters
from manga.createMetadata import CreateMetadataInterface
from manga.gateways.pushover import PushServiceInterface
from manga.gateways.database import DatabaseGateway
from manga.gateways.filesystem import FilesystemInterface
from models.manga import Chapter, MissingChapter


# for each folder in sources
# database -> select anilist id where series=x
# getChapter -> title


@Logger
class MainRunner:
    def __init__(
        self,
        sourceFolder: str,
        archiveFolder: str,
        database: DatabaseGateway,
        filesystem: FilesystemInterface,
        push: PushServiceInterface,
        missingChapters: CheckGapsInChapters,
        deleteReadChapters: DeleteReadChapters,
        calcChapterName: CalculateChapterName,
        updateTrackerIds: UpdateTrackerIds,
        createMetadata: CreateMetadataInterface,
    ) -> None:
        self.database = database
        self.pushNotification = push
        self.filesystem = filesystem
        self.sourceFolder = sourceFolder
        self.archiveFolder = archiveFolder
        self.missingChapters = missingChapters
        self.deleteReadChapters = deleteReadChapters
        self.calcChapterName = calcChapterName
        self.updateTrackerIds = updateTrackerIds
        self.createMetadata = createMetadata

    def execute(self, interactive=False):
        try:
            new_chapters: Set[Chapter] = set()
            dateScriptStart = datetime.datetime.now()
            # Globs chapters
            for chapterPathStr in glob.iglob(f"{self.sourceFolder}/*/*/*/*"):
                self.logger.info(f"Parsing: {chapterPathStr}")
                # Inferring information from files
                chapterPath = Path(chapterPathStr)

                chapterName = html.unescape(chapterPath.name)
                seriesName = html.unescape(chapterPath.parent.name)

                regexParseResults = self.calcChapterName.calc_from_filename(chapterName)
                if regexParseResults is None:
                    self.logger.debug(f"{chapterPathStr} does not have a valid filename. Quarantining...")
                    self.filesystem.simple_quarantine(chapterPathStr)
                    continue

                [chapter_name, chapter_number, year, scan_info] = regexParseResults
                anilistId = self.database.getAnilistIDForSeries(chapter_name)
                # chapterNumber = self.calcChapterName.execute(chapterName, anilistId)

                estimatedArchivePath = self.generate_simple_archive_path(chapterPathStr)

                chapterData = Chapter(
                    anilistId,
                    seriesName,
                    chapter_number,
                    chapter_name,
                    chapterPath,
                    estimatedArchivePath,
                    scan_info,
                    year
                )
                self.logger.debug(f"Already had tracker ID: {anilistId}")

                isChapterOnDB = self.database.doesExistChapterAndAnilist(
                    anilistId, chapter_number
                )
                if not anilistId or anilistId is None:
                    foundAnilistId = self.findAnilistIdForSeries(
                        chapter_name, interactive=interactive
                    )
                    estimatedArchivePath = self.generate_simple_archive_path(chapterPathStr)
                    chapterData.archivePath = estimatedArchivePath
                    if not foundAnilistId or foundAnilistId is None:
                        self.logger.error(f"No anilistId for {chapterData.seriesName}")
                        return
                    chapterData.anilistId = foundAnilistId
                if not isChapterOnDB:
                    self.setupMetadata(chapterData)
                    self.compressChapter(chapterData)
                    # self.insertInDatabase(chapterData)
                    new_chapters.add(chapterData)
                    self.filesystem.deleteFolder(location=chapterPathStr)
                else:
                    self.logger.info("Source exists but chapter's already in db")
                    # self.filesystem.deleteFolder(location=chapterPathStr)
            # deleted_chapters = self.deleteReadChapters.execute()
            # for deleted_chapter in deleted_chapters:
            #     if deleted_chapter in new_chapters:
            #         new_chapters.remove(deleted_chapter)

            # if len(new_chapters) > 0:
            #     gaps = self.missingChapters.getGapsFromChaptersSince(dateScriptStart)
            #     self.send_push(new_chapters, gaps)
        except Exception as thrown_exception:
            self.logger.error("Exception thrown")
            self.logger.error(str(thrown_exception))
            # self.send_error(thrown_exception)

    def generate_simple_archive_path(self, chapterPathStr):
        chapterPath = chapterPathStr.replace(self.sourceFolder, self.archiveFolder)
        extension = "cbz"
        return Path(f"{chapterPath}.{extension}")

    def generateArchivePath(self, anilistId, chapterName):
        return Path(self.archiveFolder).joinpath(f"{anilistId}/{chapterName}.cbz")

    def findAnilistIdForSeries(self, series: str, interactive=False):
        return self.updateTrackerIds.updateFor(series, interactive=interactive)

    def setupMetadata(self, chapter: Chapter):
        self.createMetadata.execute(chapter)

    def compressChapter(self, chapter: Chapter):
        self.filesystem.compress_chapter(chapter.archivePath, chapter.sourcePath)

    def insertInDatabase(self, chapter: Chapter):
        self.database.insertChapter(
            chapter.seriesName,
            chapter.chapterNumber,
            str(chapter.archivePath.resolve()),
            str(chapter.sourcePath.resolve()),
        )

    def send_push(self, chapters: Set[Chapter], gaps: List[MissingChapter]):
        chapters_plural = "chapters" if len(chapters) > 1 else "chapter"

        base = f"{len(chapters)} new {chapters_plural} downloaded\n\n"

        titles = map(lambda x: f"{x.seriesName} {x.chapterNumber}", chapters)
        sorted_titles = sorted(titles)

        chapters_body = "\n".join(sorted_titles)

        if len(gaps) > 0:
            missing_title = "Updated in quarantine:"
            missing_chapters = map(lambda x: f"{x.series_name}", gaps)
            missing_body = "\n".join(missing_chapters)
            chapters_body += "\n\n" + missing_title + "\n" + missing_body

        self.pushNotification.sendPush(base + chapters_body)

    def send_error(self, value: Exception):
        self.pushNotification.sendPush(str(value))

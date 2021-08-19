from datetime import datetime
import sqlite3
from typing import List
from .utils.databaseModels import AnilistSeries


class DatabaseGateway:
    def __init__(self, databaseLocation: str) -> None:
        self.conn = sqlite3.connect(databaseLocation)
        super().__init__()

    def __getCursor(self):
        cur = self.conn.cursor()
        return cur

    def getSeriesForAnilist(self, anilistId):
        cur = self.__getCursor()

        #Remember that anilist only stores integers for chapter numbers!
        query = '''
        SELECT series
        FROM anilist 
        WHERE anilistId = ?
        '''
        cur.execute(query, (anilistId,))
        row = cur.fetchone()
        return row[0]

    def doesExistChapterAndAnilist(self, anilistId, chapterNumber):
        cur = self.__getCursor()

        #Remember that anilist only stores integers for chapter numbers!
        query = '''
        SELECT a.series
        FROM manga a
        INNER JOIN anilist b
        ON a.series = b.series
        WHERE chapter = ? AND anilistId = ?
        '''
        cur.execute(query, (chapterNumber, anilistId))
        row = cur.fetchone()
        return row

    def deleteChapter(self, seriesName, chapterNumber):
        cur = self.__getCursor()

        #Remember that anilist only stores integers for chapter numbers!
        query = '''
        DELETE FROM manga
        WHERE chapter = ? AND series = ?'''
        cur.execute(query, (chapterNumber, seriesName))
        self.conn.commit()

    def insertChapter(self, seriesName, chapterNumber: str, archivePath, sourcePath):
        cur = self.__getCursor()

        query = '''
        INSERT INTO manga(series, chapter, archive, source)
        VALUES(?,?,?,?)
        '''
        cur.execute(query, (seriesName, chapterNumber,
                    archivePath, sourcePath))
        self.conn.commit()

    def insertTracking(self, seriesName, anilistId: int):
        cur = self.__getCursor()

        query = '''
        INSERT OR REPLACE INTO anilist(series, anilistId)
        VALUES(?, ?)
        '''
        cur.execute(query, (seriesName, anilistId))
        self.conn.commit()

    def getAllSeries(self) -> List[AnilistSeries]:
        cur = self.__getCursor()
        cur.execute('''SELECT DISTINCT b.anilistId, a.series FROM manga a
                        INNER JOIN anilist b
                        ON a.series = b.series''')
        rows = cur.fetchall()
        return map(lambda a: AnilistSeries(a[0], a[1]), rows)

    def getAllSeriesWithoutTrackerIds(self) -> List[str]:
        cur = self.__getCursor()
        cur.execute('''SELECT DISTINCT a.series FROM manga a
                        LEFT JOIN anilist b
                        ON a.series = b.series
                    WHERE anilistId IS NULL''')
        rows = cur.fetchall()
        return rows

    def getChaptersForSeriesBeforeNumber(self, series, chapter):
        cur = self.__getCursor()
        cur.execute('''
            SELECT chapter
            FROM manga
            WHERE series = ?
            AND CAST(chapter AS REAL) <= ?
                        ''', (series, chapter))
        rows = cur.fetchall()
        return rows

    def getSourceForChapter(self, series, chapter):
        cur = self.__getCursor()
        cur.execute('''SELECT source FROM manga
                        WHERE series = ? AND chapter = ? ''', (series, chapter))
        row = cur.fetchone()
        if row is not None:
            return row[0]
        else:
            return None

    def getArchiveForChapter(self, series, chapter):
        cur = self.__getCursor()
        series = series
        cur.execute('''SELECT archive FROM manga
                        WHERE series = ? AND chapter = ? ''', (series, chapter))
        row = cur.fetchone()
        if row is not None:
            return row[0]
        else:
            return None

    def getAnilistIDForSeries(self, series):
        cur = self.__getCursor()
        series = series
        cur.execute('''SELECT anilistId FROM anilist
                        WHERE series = ?''', (series,))
        row = cur.fetchone()
        if row is not None:
            return row[0]
        else:
            return None

    def getLowestChapterForSeriesUpdatedSinceDate(self, date: datetime):
        cur = self.__getCursor()
        cur.execute('''
            SELECT MIN(CAST(chapter AS INT)), a.series, anilistId
            FROM manga a
            INNER JOIN anilist b
            ON a.series = b.series
                WHERE a.series IN (
                SELECT DISTINCT series
                FROM manga
                WHERE creation_date > ?
            )
            GROUP BY a.series
                        ''', (date,))
        return cur.fetchall()

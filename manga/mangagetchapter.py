from typing import Optional
from cross.decorators import Logger
from manga.gateways.anilist import TrackerGatewayInterface
import os
from pathlib import Path
import re
import glob


@Logger
class CalculateChapterName:
    def __init__(self, anilist: TrackerGatewayInterface) -> None:
        self.anilist = anilist
        pass

    def __formatNumber(self, num: float):
        if num % 1 == 0:
            return int(num)
        else:
            return num

    def _getNewestFileIn(self, folder):
        list_of_files = glob.glob(
            folder + "/*"
        )
        latest_file = max(list_of_files, key=os.path.getctime)
        return Path(latest_file).stem

    def _getNewestChAnilistFor(self, anilistId):
        progress = self.anilist.getProgressFor(int(anilistId))
        return progress

    def execute(self, chapterName, anilistId):
        """ Infers the chapter number from a chapter name
            (chapter, volume, volChapter)
        """

        detectedChapter: Optional[str] = None

        chapterFunctions = [
            self.__volNotation
            #self.__exNotation,
            #self.__defaultChapterNotation,
            #self.__anyOtherNumberNotation
        ]

        for func in chapterFunctions:
            detectedChapter = func(chapterName, anilistId)
            if detectedChapter is not None:
                break

        return detectedChapter

    def __volNotation(self, chapterName: str, anilistId: int) -> Optional[str]:
        volRegex = r"v([0-9]+\.?[0-9]*)"
        matchObj = re.search(volRegex, chapterName)
        if matchObj:
            return matchObj.group(1).lstrip("0") or ("0")
        return None

    def __exNotation(self, chapterName: str, anilistId: int) -> Optional[str]:
        exRegex = r"^(\w+_|\#)?ex\ -\ .*?([0-9]+)?"
        matchObj = re.search(exRegex, chapterName)
        if matchObj:
            result = self._getNewestChAnilistFor(anilistId)
            if result:
                return str(result) + ".8"
        return None

    def __defaultChapterNotation(self,
                                 chapterName: str,
                                 anilistId: int) -> Optional[str]:
        chRegex = r"Ch\.\ ?([0-9]+\.?[0-9]*)"
        matchObj = re.search(chRegex, chapterName)
        if matchObj:
            return matchObj.group(1).lstrip("0") or "0"
        return None

    def __anyOtherNumberNotation(self,
                                 chapterName: str,
                                 anilistId: int) -> Optional[str]:
        largeNumRegex = r"[0-9]+\.?[0-9]*"
        matchObj = re.findall(largeNumRegex, chapterName)
        if matchObj:
            intMatch = map(lambda x: float(x), matchObj)
            result = sorted(intMatch, reverse=True)
            bestValue = result[0]
            roundedValue = self.__formatNumber(bestValue)
            return str(roundedValue)
        return None

    def __latestAnilistNumber(self, chapterName: str, anilistId: int) -> Optional[str]:
        if anilistId:
            result = self._getNewestChAnilistFor(anilistId)
            if result:
                return str(result) + ".8"
        return None

    def calc_from_filename(self, file_name):
        """for an explanation of the regex, check the bottom of the file"""
        expected_filename_regex = r"^(.+)\sv([0-9]+\.?[0-9]*)\s(\((\d+)\))?\s\(Digital\)[\(F\d\)\s]+\(([\w\s\-]+)\)$"
        match_obj = re.search(expected_filename_regex, file_name)
        if match_obj is None:
            # try to grab only volume number
            match_another_obj = re.search(r"^(.+)\sv([0-9]+\.?[0-9]*)", file_name)
            if match_another_obj is None:
                # give up all hope in this rip
                self.logger.debug(f"No Regex matched switching to defaults")
                return [file_name, 1, 2022, ""]
            else:
                chapter_name = match_another_obj.group(1)
                chapter_number = match_another_obj.group(2)
                self.logger.debug(f"Regex results for {file_name}: [ {chapter_name}, {chapter_number}, 2021, \"\"]")
                return [chapter_name, chapter_number, 2021, ""]

        chapter_name = match_obj.group(1)
        chapter_number = match_obj.group(2).lstrip("0") or "0"
        # group(3) is just `(group(4))`
        year = match_obj.group(4)
        scan_info = match_obj.group(5)

        self.logger.debug(f"Regex results for {file_name}: [ {chapter_name}, {chapter_number}, {year}, {scan_info} ]")
        return [chapter_name, chapter_number, year, scan_info]


"""
 Explaining the mammoth of a regex
 Regex = ^(.+)\\sv([0-9]+\\.?[0-9]*)\\s(\\((\\d+)\\))?\\s\\(Digital\\)[\\(F\\d\\)\\s]+\\(([\\w\\s\\-]+)\\)$
 there are 5 groups (4 useful ones) captured
 ignoring the groups, the regex = ^(group1)v(group2)\\s+(group3)?\\s+\\(Digital\\)[\\(F\\d\\)\\s]+(group5)$
 which basically is looking for `v`, `Digital` in the filename and everything else is grouped
 sometimes there are Fixed releases too and those come up as F1, F3 etc
 now the groups:
     (.+) - capture everything
     v([0-9]+\\.?[0-9]*) - capture's the volume number, eg: v01, v2, v13, v100.5
     ( (\\((\\d+)\\))? ) - matches the year, can do \\d{4} but eh
     \\(([\\w\\s\\-]+)\\) - this is usually the scan grp
"""
import string
from typing import Optional
from lxml import etree
from models.manga import Chapter
from cross.decorators import Logger
from manga.gateways.filesystem import FilesystemInterface
from manga.gateways.anilist import AnilistGateway
from .createMetadata import CreateMetadataInterface


@Logger
class CreateMetadata3(CreateMetadataInterface):
    """lxml implementation of CreateMetadataInterface.
       grabs more info from Anilist to help create better comicinfo.xml"""

    def __init__(self, filesystem: FilesystemInterface, anilist: AnilistGateway):
        self.filesystem = filesystem
        self.anilist = anilist

    def execute(self, chapter: Chapter):
        result = self.__generate_metadata(chapter)
        destination = chapter.sourcePath.joinpath("ComicInfo.xml")
        self.filesystem.saveFile(stringData=result, filepath=destination)

    def __generate_metadata(self, chapter: Chapter) -> str:
        anilistData = self.anilist.search_media_by_id(chapter.anilistId)

        root = etree.Element("ComicInfo")
        etree.SubElement(root, "Title").text = chapter.chapterName
        etree.SubElement(root, "Series").text = anilistData.title
        etree.SubElement(root, "Chapter").text = chapter.chapterNumber
        etree.SubElement(root, "Volume").text = chapter.chapterNumber
        etree.SubElement(root, "AlternateSeries").text = anilistData.altTitles
        etree.SubElement(root, "Summary").text = anilistData.summary
        etree.SubElement(root, "Notes").text = anilistData.status
        etree.SubElement(root, "Year").text = chapter.year
        etree.SubElement(root, "Writer").text = anilistData.writer
        etree.SubElement(root, "Penciller").text = anilistData.penciller
        etree.SubElement(root, "Inker").text = anilistData.inker
        etree.SubElement(root, "Genre").text = anilistData.genres
        etree.SubElement(root, "Web").text = anilistData.site_url
        etree.SubElement(root, "Format").text = anilistData.format
        if anilistData.country_of_origin == "JP":
            etree.SubElement(root, "BlackAndWhite").text = "Yes"
            etree.SubElement(root, "Manga").text = "YesAndRightToLeft"
        etree.SubElement(root, "ScanInformation").text = chapter.scan_info
        etree.SubElement(root, "AgeRating").text = anilistData.age_rating

        return etree.tostring(
            root, pretty_print=True, xml_declaration=True, encoding="utf-8"
        )

    @staticmethod
    def simplify_str(value: str) -> str:
        result = value
        for char in string.punctuation + string.whitespace:
            result = result.replace(char, "")
        return result.lower()

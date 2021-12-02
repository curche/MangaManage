import http.client
import json
from functools import reduce
from typing import List, Mapping
from models.tracker import TrackerSeries
from models.anilistToComicInfo import AnilistComicInfo


class TrackerGatewayInterface:
    def getProgressFor(self, mediaId):
        pass

    def searchMediaBy(self, title):
        pass

    def getAllEntries(self) -> Mapping[int, TrackerSeries]:
        pass

    def search_media_by_id(self, id) -> AnilistComicInfo:
        pass


class AnilistGateway(TrackerGatewayInterface):
    def __init__(self, authToken: str, userId: str) -> None:
        self.token = authToken
        self.userId = userId
        self.cache = {}

    def __prepareRequest(self, query, variables):
        query_key = (query, str(variables))
        cache_value = self.cache.get(query_key)
        if cache_value is not None:
            return cache_value

        conn = http.client.HTTPSConnection("graphql.anilist.co")
        headers = {"Content-Type": "application/json", "Authorization": self.token}

        body = json.dumps({"query": query, "variables": variables})
        conn.request("POST", "", body, headers)
        res = conn.getresponse()
        data = res.read()
        utfData = data.decode("utf-8")

        result = json.loads(utfData)

        if res.status == 200:
            self.cache[query_key] = result

        return result

    def getProgressFor(self, mediaId):
        try:
            query = """
          query($mediaId: Int, $userId: Int) {
  MediaList(userId: $userId, mediaId: $mediaId) {
      mediaId,
      progress,
      status
    }
    }
  """
            variables = {"mediaId": mediaId, "userId": self.userId}
            result = self.__prepareRequest(query, variables)
            errors = result.get("errors")
            if errors is not None:
                print("Error in getProgressFor %s" % mediaId)
                print(result["errors"])
                return
            entries = result["data"]["MediaList"]["progress"]
            return entries
        except Exception as e:
            print("Error in getProgressFor %s" % mediaId)
            print(e)

    def searchMediaBy(self, title):
        query = """
      query($searchId: String) {
    Media(search: $searchId) {
      id,
      title {
        romaji
        english
        native
        userPreferred
      }
    }
  }"""
        variables = {"searchId": title}

        result = self.__prepareRequest(query, variables)
        print(result)
        media = result["data"]["Media"]
        titleObj = media["title"]
        titles = [
            titleObj["romaji"],
            titleObj["english"],
            titleObj["native"],
            titleObj["userPreferred"],
        ]
        return (media["id"], titles)

    def getAllEntries(self) -> Mapping[int, TrackerSeries]:
        query = """
      query($userId: Int) {
    MediaListCollection(userId: $userId, type: MANGA) {
      lists {
        entries {
          ...mediaListEntry
        }
      }
    }
  }

  fragment mediaListEntry on MediaList {
    progress
    media {
      id
      synonyms
      countryOfOrigin
      title {
        romaji
        english
      }
      status
      chapters
    }
  }
      """

        variables = {"userId": self.userId}

        result = self.__prepareRequest(query, variables)
        errors = result.get("errors")
        if errors is not None:
            print(result["errors"])
            return

        # Merge all of the user's manga lists
        lists = result["data"]["MediaListCollection"]["lists"]
        mapped = map((lambda x: x["entries"]), lists)
        reduced = reduce((lambda x, y: x + y), mapped)

        models: List[TrackerSeries] = []
        for series in reduced:
            main_titles = [
                series["media"]["title"]["english"],
                series["media"]["title"]["romaji"],
            ]
            all_titles = main_titles + series["media"]["synonyms"]
            non_empty_all_titles = list(filter(None, all_titles))

            models.append(
                TrackerSeries(
                    series["media"]["id"],
                    non_empty_all_titles,
                    series["media"]["status"],
                    series["media"]["chapters"],
                    series["media"]["countryOfOrigin"],
                    series["progress"],
                )
            )

        # Create anilist ID keyed dictionary
        model_dictionary = dict((v.tracker_id, v) for v in models)
        return model_dictionary

    def search_media_by_id(self, id):

        cache_value = self.cache.get(id)
        if cache_value is not None:
            return cache_value

        query = """query ($anilistId: Int) {
          Media(id: $anilistId, type: MANGA, sort: POPULARITY_DESC) {
            id
            idMal
            title {
              userPreferred
              romaji
            }
            format
            status(version: 2)
            description
            countryOfOrigin
            source(version: 2)
            genres
            staff(sort: RELEVANCE, page: 1, perPage: 3) {
              edges {
                node {
                  name {
                    userPreferred
                  }
                  languageV2
                }
                role
              }
            }
            isAdult
            siteUrl
            chapters
            volumes
            tags {
              name
              category
              isGeneralSpoiler
            }
          }
        }"""

        variable = {"anilistId": id}

        result = self.__prepareRequest(query, variable)
        errors = result.get("errors")
        if errors is not None:
            print(result["errors"])
            return

        media = result["data"]["Media"]

        staff = media["staff"]
        writer = ""
        penciller = ""
        inker = ""

        for edge in staff["edges"]:
            node = edge["node"]
            language = node["languageV2"]
            if language != "Japanese":
                continue

            role = edge["role"]
            name = node["name"]["userPreferred"]
            if role.startswith("Story"):
                writer = name
            if role.endswith("Art"):
                penciller = name
                inker = name

        all_tags = media["tags"]
        tags = []
        for tag in all_tags:
            tag_name = tag["name"]
            tag_category = tag["category"]
            is_spoiler = tag["isGeneralSpoiler"]
            if is_spoiler:
                continue
            tags.append(f"{tag_category}: {tag_name}")

        anilistData = AnilistComicInfo(
            tracker_id=id,
            title=media["title"]["userPreferred"],
            manga_format=media["format"],
            status=media["status"],
            description=media["description"],
            country_of_origin=media["countryOfOrigin"],
            original_source=media["source"],
            genres=media["genres"],
            writer=writer,
            penciller=penciller,
            inker=inker,
            synonyms=media["title"]["romaji"],
            is_adult=media["isAdult"],
            site_url=media["siteUrl"],
            chapters=media["chapters"],
            volumes=media["volumes"],
            tags=tags
        )
        self.cache[id] = anilistData

        return anilistData

"""Fetch the latest releases from your favorite artists"""

import time
import deezer
import argparse
from notion.client import NotionClient
from notion.block import TodoBlock, DividerBlock, ImageBlock
from notion.collection import NotionDate
from datetime import datetime, timedelta, date, timezone
from auth import USER_ID, TOKEN_V2, COLLECTION_URL

parser = argparse.ArgumentParser(description="Fetch the latest releases from your favorite artists")
parser.add_argument("-d", "--nb-days", default=2, help="how far you want to go (days)", type=int)
parser.add_argument("-u", "--utc-offset", default=2, help="offset with UTC time zone (hours)", type=int)
parser.add_argument("-r", "--remove-checked", action="store_true", help="remove checked elements even if they are recent")
args = parser.parse_args()


nb_days = args.nb_days
nb_days_delta = timedelta(days=nb_days)
utc_offset = args.utc_offset
utc_offset_delta = timedelta(hours=utc_offset)
remove_all_checked = args.remove_checked


## DEEZER ##

def make_dict(client, album):
    album_dict = {}
    # basic info
    album_dict["artist"] = album.artist.name
    album_dict["title"] = album.title
    album_dict["type"] = album.record_type
    # length of tracklist
    album_dict["tracks"] = len(album.get_tracks())
    # 1st genre of album
    album_genre = client.get_genre(album.genre_id).name
    album_dict["genre"] = album_genre if album_genre != -1 else None
    # url
    album_dict["url"] = album.link
    # release date
    release_datetime = datetime.strptime(album.release_date, '%Y-%m-%d')
    release_date = release_datetime.date()  # to get rid of release time
    album_dict["released_on"] = NotionDate(start=release_date)

    return album_dict

def get_artist_from_album_search(client, artist_request_name):
    """Get artist using an album search. Used if the artist search failed."""
    track_list = client.search(artist_request_name, relation='album')
    track_result = track_list[0]
    artist_result = track_result.artist
    return artist_result

def get_new_releases():
    """Fetch latest releases from Deezer."""
    new_releases = []
    client = deezer.Client()

    # get user
    user = client.get_user(USER_ID)
    print(f"## Hello, {user.name}! ##\n")

    now = datetime.now()
    print(f"------\tFetching releases from last {nb_days} days...")

    for artist_request in user.get_artists(limit=100):
        # artist search
        artist_list = client.search(artist_request.name, relation='artist')
        # if no result
        if len(artist_list) == 0:
            artist_result = get_artist_from_album_search(client, artist_request.name)
        else:
            artist_result = artist_list[0]
        # if bad result
        if artist_request.name != artist_result.name:  # often because artist_request makes compilations
            artist_result = get_artist_from_album_search(client, artist_request.name)
        for album in artist_result.get_albums():
            release_date = datetime.strptime(album.release_date, '%Y-%m-%d')
            delta = now - release_date
            if delta < nb_days_delta:
                new_releases.append(make_dict(client, album))
        time.sleep(.1)  # to avoid 'API request return error'

    nb_releases = len(new_releases)
    if nb_releases == 0:
        print("-info-\tNo release found :(")
    elif nb_releases == 1:
        print(f"-info-\tOne release found in last {nb_days} days!")
    else:
        print(f"-info-\t{nb_releases} releases found in last {nb_days} days!")
    return new_releases


## NOTION.SO ##

def remove_old_checked_elements(cv):
    """"""
    now = datetime.now()
    nb_cleaned = 0

    for row in cv.collection.get_rows():
        if row.done:
            delta = now - (row.added + utc_offset_delta)
            if remove_all_checked or delta > nb_days_delta - timedelta(hours=12):  # to be sure there is no overlapping
                row.remove()
                nb_cleaned += 1

    if nb_cleaned >= 1:
        print(f"-info-\tCleaned 1 checked element." if nb_cleaned == 1 else f"-info-\tCleaned {nb_cleaned} checked elements.")

def already_in_database(cv, album_dict):
    for row in cv.collection.get_rows():
        if row.url == album_dict["url"]:
            return True
    return False

def add_to_notion(new_releases):
    """Add new releases to the Notion.so page in the right collection."""
    print(f"------\tAdding to Notion...")
    client = NotionClient(token_v2=TOKEN_V2)
    cv = client.get_collection_view(COLLECTION_URL)

    nb_releases_to_add = len(new_releases)

    for album_dict in new_releases:  # for each new release

        # test if already in database using the url
        if already_in_database(cv, album_dict):
            nb_releases_to_add -= 1
            continue

        # if new
        row = cv.collection.add_row()
        for key, value in album_dict.items():
            if key == "genre":
                try:
                    if value is None:  # i.e. if no genre on Deezer
                        raise NoGenreFound()
                    else:
                        setattr(row, key, value)
                except NoGenreFound:
                    pass
                except ValueError:  # i.e. if genre does not exist yet in Notion
                    print(f"-warn-\tPlease add genre {value} to database!")
            else:
                setattr(row, key, value)

    if nb_releases_to_add == 0:
        print("-info-\tAlbums already added.")
    elif nb_releases_to_add == 1:
        print("-info-\tAdded 1 album to Notion.so!")
    else:
        print(f"-info-\tAdded {nb_releases_to_add} albums to Notion.so!")

    # remove checked elements of last week
    remove_old_checked_elements(cv)
    print()
    print("-info-\tDone!")


## EXCEPTIONS

class NoGenreFound(Exception):
    pass


if __name__ == "__main__":
    new_releases = get_new_releases()
    add_to_notion(new_releases)

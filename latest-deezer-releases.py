"""Fetch the latest releases from your favorite artists"""

import time
import deezer
import argparse
from notion.client import NotionClient
from notion.block import TodoBlock, DividerBlock, ImageBlock
from datetime import datetime, timedelta
from auth import USER_ID, TOKEN_V2, PAGE_URL

parser = argparse.ArgumentParser(description="Fetch the latest releases from your favorite artists")
parser.add_argument("-d", "--nb-days", default=7, help="how far you want to go in days", type=int)
args = parser.parse_args()

nb_days_delta = args.nb_days


## UTILS ##

def format_release(album):
    """Prettily display album in Notion."""
    return f"__{album.artist.name}__ - [{album.title}]({album.link})"


## DEEZER ##

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
    print(f"Fetching releases from last {nb_days_delta} days...")

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
            delta_limit = timedelta(days=nb_days_delta)
            if delta < delta_limit:
                new_releases.append(album)
        time.sleep(.1)  # to avoid 'API request return error'

    nb_releases = len(new_releases)
    if nb_releases == 0:
        print("No new release found :(")
    elif nb_releases == 1:
        print("A new release found!")
    else:
        print(f"{nb_releases} new releases found!")
    return new_releases


## NOTION.SO ##

def find_releases_section(page):
    """Find the 'New releases' section on page."""
    in_releases_section = False
    start_id = None
    already_in_notion = []
    for child in page.children:
        if hasattr(child, 'title') and 'New releases' in child.title:
            in_releases_section = True
            start_id = child.id
        elif in_releases_section and type(child) == TodoBlock:
            already_in_notion.append(child.title)
    if start_id is None:
        print("Cannot find the 'New releases' section in this page!")
        raise NewReleasesSectionNotFound()

    return start_id, already_in_notion

def remove_ticked_elements(page, start_id):
    """Browse blocks and remove the checked todo [] blocks if they are in the
    'New releases' section."""
    in_releases_section = False
    nb_cleaned = 0

    for child in page.children:
        if child.id == start_id:
            in_releases_section = True
            continue

        elif in_releases_section and type(child) is TodoBlock:
            if child.checked:  # already listened
                child.remove(permanently=True)
                nb_cleaned += 1
        elif in_releases_section and type(child) is ImageBlock:
            child.remove(permanently=True)

    if nb_cleaned >= 1:
        print(f"Cleaned 1 checked element." if nb_cleaned == 1 else f"Cleaned {nb_cleaned} checked elements.")

def add_to_notion(new_releases):
    """Add new releases to the Notion.so page at the right place."""
    client = NotionClient(token_v2=TOKEN_V2)
    page = client.get_block(PAGE_URL)

    start_id, already_in_notion = find_releases_section(page)
    start_block = client.get_block(start_id)

    # add new titles
    for album in new_releases:
        block_title = format_release(album)
        if block_title not in already_in_notion:
            release_block = page.children.add_new(block_type=TodoBlock, title=block_title)
            # todo: move this block to before the next section
    if len(new_releases) >= 1:
        print("Added albums to Notion.so!")
    # remove ticked elements
    remove_ticked_elements(page, start_id)

    # add a random photo among new albums at the bottom of the page
    if len(new_releases) >= 1:  # at least one new album
        photo_block = page.children.add_new(block_type=ImageBlock, width=300)
        photo_block.set_source_url(album.cover_big)
        print("... and a little cover :)")


class NewReleasesSectionNotFound(Exception):
    pass


if __name__ == "__main__":
    new_releases = get_new_releases()
    add_to_notion(new_releases)

# latest-deezer-releases
Fetch the latest releases from my favorite Deezer artists and put them on a Notion.so page, using the [Deezer Python Client](https://github.com/browniebroke/deezer-python) and a [Python Notion.so API](https://github.com/jamalex/notion-py).

> :warning: This code is quite specific to my own needs, so use it at your own risk!

### What it does
It takes my favorite artists and fetches their latest releases (the default value of `--nb-days` can be changed in the [argument parser](./latest-deezer-releases.py)). Then, it puts them in a page in my Notion.so account, in which I have a ":fire: New releases" section. This code is automatically executed each week. Hopefully, I'll be kept up to date!

### How to use
```bash
$ python latest-deezer-releases.py  # 7 days by default
$ python latest-deezer-releases.py -d 50  # custom period
```

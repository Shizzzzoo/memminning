# Optional character artwork

The roster includes Steve, Alex, Jonesy, Peely, Jett, Sage, Phoenix and Reyna using existing character artwork. Generated substitutes are not used.

Full portrait image files are excluded from Git and release archives. To fetch them explicitly, use:

```bash
/usr/bin/python3 install.py --with-character-art
# Or download into a source checkout before installing:
/usr/bin/python3 scripts/fetch_character_art.py
```

The downloader accepts the documented HTTPS source hosts, limits image size, validates PNG signatures and verifies the committed SHA-256 checksums before replacing files. It never executes downloaded content. Offline installs show generic icons and retain custom-image support. Ordinary app use never fetches images.

| Characters | Source | Credits |
| --- | --- | --- |
| Steve, Alex | [Nintendo's official fighter page](https://www.smashbros.com/en_US/fighter/77.html) | Mojang / Microsoft characters; Nintendo promotional renders |
| Jonesy, Peely | [Fortnite-API](https://fortnite-api.com/) | Epic Games artwork via a community mirror |
| Jett, Sage, Phoenix, Reyna | [VALORANT-API](https://valorant-api.com/) | Riot Games artwork via a community mirror |

[characters/sources.json](characters/sources.json) records exact image URLs, filenames and hashes. Source artwork belongs to its respective owners and is not covered by Memminning's MIT license; see [third-party notices](../THIRD_PARTY_NOTICES.md).

Downloaded image bytes are preserved. GTK downscales images and frames the full-body Steve/Alex renders at display time. Personal PNG/JPEG avatar import remains available in Preferences.

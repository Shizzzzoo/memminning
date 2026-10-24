"""Explicit, checksum-verified downloads of optional third-party character artwork."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ALLOWED_HOSTS = {'www.smashbros.com', 'fortnite-api.com', 'media.valorant-api.com'}
MAX_IMAGE_BYTES = 10 * 1024 * 1024


def fetch_artwork(assets: Path, opener=urlopen):
    assets = Path(assets)
    records = json.loads((assets / 'characters/sources.json').read_text())
    installed = []
    for record in records:
        name, expected, url = record['file'], record['sha256'], record['url']
        if not re.fullmatch(r'characters/[a-z]+\.png', name):
            raise ValueError('Invalid artwork filename in source manifest')
        if not re.fullmatch(r'[a-f0-9]{64}', expected):
            raise ValueError('Invalid artwork checksum in source manifest')
        parsed = urlsplit(url)
        if parsed.scheme != 'https' or parsed.hostname not in ALLOWED_HOSTS:
            raise ValueError('Unsupported artwork source in manifest')
        target = assets / name
        if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == expected:
            installed.append(target)
            continue
        request = Request(url, headers={'User-Agent': 'Memminning-artwork-installer/1.0'})
        with opener(request, timeout=30) as response:
            final = urlsplit(response.geturl())
            if final.scheme != 'https' or final.hostname not in ALLOWED_HOSTS:
                raise ValueError('Artwork source redirected to an unexpected host')
            image = response.read(MAX_IMAGE_BYTES + 1)
        if len(image) > MAX_IMAGE_BYTES or not image.startswith(b'\x89PNG\r\n\x1a\n'):
            raise ValueError(f'Invalid or oversized PNG for {record["id"]}')
        if hashlib.sha256(image).hexdigest() != expected:
            raise ValueError(f'Artwork checksum changed for {record["id"]}; original file was preserved')
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix='.artwork-', dir=target.parent)
        try:
            with os.fdopen(fd, 'wb') as handle:
                handle.write(image)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        installed.append(target)
    return installed

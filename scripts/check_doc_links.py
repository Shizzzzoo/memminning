#!/usr/bin/env python3
"""Validate relative Markdown targets without network access."""
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

root = Path(__file__).resolve().parents[1]
errors = []
for document in root.rglob('*.md'):
    if any(part in {'.git', 'dist', 'archive'} for part in document.relative_to(root).parts):
        continue
    for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', document.read_text()):
        target = target.split(' "', 1)[0].strip('<>')
        parsed = urlsplit(target)
        if parsed.scheme or target.startswith('#'):
            continue
        path = unquote(parsed.path)
        if path and not (document.parent / path).exists():
            errors.append(f'{document.relative_to(root)}: {target}')
if errors:
    raise SystemExit('\n'.join(errors))
print('Relative Markdown links resolve.')

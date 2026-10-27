#!/usr/bin/env python3
"""Read-only structural checks. Does not curate sources or write wiki pages."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

HEADERS = {
    'sources.csv': ['source_id', 'relative_path', 'source_group', 'source_type',
                    'publication_date', 'data_period', 'origin_url',
                    'reading_depth', 'content_sha256'],
    'processing.csv': ['unit_id', 'source_id', 'scope', 'status', 'source_sha256',
                       'outputs', 'next_step', 'reason', 'updated_at'],
    'issues.csv': ['issue_id', 'source_refs', 'kind', 'description', 'status',
                   'wiki_paths', 'next_step'],
}
DEPTHS = {'none', 'metadata', 'snippet', 'abstract', 'sections', 'full'}
STATES = {'pending', 'in_progress', 'partial', 'processed', 'reused',
          'excluded', 'blocked', 'outdated'}
PAGE_STATES = {'draft', 'reviewed', 'needs_review'}


def split_values(value):
    return [x.strip() for x in value.split(';') if x.strip()]


def local_path(base, value, errors, context):
    if not value or Path(value).is_absolute():
        errors.append(context + ': expected a relative path')
        return None
    path = (base / value).resolve()
    if base.resolve() not in path.parents:
        errors.append(context + ': path escapes its assigned root')
        return None
    if not path.is_file():
        errors.append(context + ': missing file ' + value)
    return path


def load_csv(path, expected, errors):
    try:
        with path.open(encoding='utf-8-sig', newline='') as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != expected:
                errors.append(str(path) + ': unexpected CSV header')
                return []
            rows = list(reader)
    except (OSError, csv.Error, UnicodeError) as exc:
        errors.append(str(path) + ': ' + str(exc))
        return []
    valid = []
    for row in rows:
        if None in row or any(value is None for value in row.values()):
            errors.append(str(path) + ': malformed CSV row')
        else:
            valid.append(row)
    return valid


def unique_rows(rows, field, errors):
    result = {}
    for row in rows:
        key = row[field]
        if not key or key in result:
            errors.append(field + ': empty or duplicate ID ' + key)
        else:
            result[key] = row
    return result


def check_links(path, errors):
    fenced = False
    checked = 0
    for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        if line.lstrip().startswith(('```', '~~~')):
            fenced = not fenced
            continue
        if fenced:
            continue
        for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', line):
            target = target.split(' "', 1)[0].strip('<>')
            if urlsplit(target).scheme or target.startswith('//'):
                continue
            filename, _, fragment = target.partition('#')
            dest = path.parent / unquote(filename) if filename else path
            checked += 1
            if not dest.exists():
                errors.append(str(path) + ':' + str(number) + ': broken link ' + target)
            elif fragment.startswith(('pdf-', 'url-')) and dest.suffix == '.md':
                anchor = 'id="' + unquote(fragment) + '"'
                if anchor not in dest.read_text(encoding='utf-8'):
                    errors.append(str(path) + ': missing explicit anchor ' + target)
    return checked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, default=Path.cwd())
    parser.add_argument('--verify-source-hashes', action='store_true',
                        help='Read registered raw files only to check their SHA-256.')
    args = parser.parse_args()
    root = args.project_root.resolve()
    wiki = root / 'knowledge/wiki'
    raw = root / 'knowledge/raw'
    errors = []
    for filename in ['INDEX.md', 'AGENTS.md', 'meta/progress.md']:
        if not (wiki / filename).is_file():
            errors.append('Missing scaffold file: ' + filename)
    tables = {name: load_csv(wiki / 'meta' / name, fields, errors)
              for name, fields in HEADERS.items()}
    sources = unique_rows(tables['sources.csv'], 'source_id', errors)
    units = unique_rows(tables['processing.csv'], 'unit_id', errors)
    unique_rows(tables['issues.csv'], 'issue_id', errors)
    seen_paths = set()
    for sid, row in sources.items():
        path = local_path(raw, row['relative_path'], errors, sid)
        if path in seen_paths:
            errors.append(sid + ': same file registered twice')
        seen_paths.add(path)
        if row['reading_depth'] not in DEPTHS:
            errors.append(sid + ': invalid reading_depth')
        digest = row['content_sha256']
        if digest and not re.fullmatch(r'[0-9a-f]{64}', digest):
            errors.append(sid + ': invalid SHA-256')
        if args.verify_source_hashes and path and path.is_file():
            hasher = hashlib.sha256()
            with path.open('rb') as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b''):
                    hasher.update(chunk)
            if digest != hasher.hexdigest():
                errors.append(sid + ': source version changed or hash missing')
    for uid, row in units.items():
        sid = row['source_id']
        if sid not in sources:
            errors.append(uid + ': unknown source_id ' + sid)
        if not row['scope'] or row['status'] not in STATES:
            errors.append(uid + ': missing scope or invalid status')
        outputs = split_values(row['outputs'])
        for value in outputs:
            local_path(wiki, value, errors, uid)
        if row['status'] in {'processed', 'reused'}:
            source = sources.get(sid, {})
            digest = row['source_sha256']
            if not digest or digest != source.get('content_sha256'):
                errors.append(uid + ': completed unit must match its registered source hash')
            substantive = [x for x in outputs if x.startswith(('case/', 'topics/', 'methods/'))
                           and x.endswith('.md') and Path(x).name != 'README.md']
            if not substantive:
                errors.append(uid + ': completed unit needs a thematic output')
            if row['status'] == 'processed' and source.get('reading_depth') == 'none':
                errors.append(uid + ': processed source has not been read')
        if row['status'] in {'excluded', 'blocked', 'reused'} and not row['reason']:
            errors.append(uid + ': status requires an explanation')
        if row['status'] in {'partial', 'blocked'} and not row['next_step']:
            errors.append(uid + ': specify how to continue')
    for row in tables['issues.csv']:
        for sid in split_values(row['source_refs']):
            if sid not in sources:
                errors.append(row['issue_id'] + ': unknown source ' + sid)
        if row['status'] not in {'open', 'resolved', 'accepted_limitation'}:
            errors.append(row['issue_id'] + ': invalid issue status')
        for value in split_values(row['wiki_paths']):
            local_path(wiki, value, errors, row['issue_id'])
    pages = []
    for folder in ['case', 'topics', 'methods']:
        pages.extend(p for p in (wiki / folder).rglob('*.md') if p.name != 'README.md')
    page_refs = {}
    for path in pages:
        text = path.read_text(encoding='utf-8')
        front = re.match(r'^---\n(.*?)\n---(?:\n|$)', text, re.S)
        if not front:
            errors.append(str(path) + ': missing frontmatter')
            continue
        meta = front.group(1)
        status = re.search(r'^status:\s*(\S+)\s*$', meta, re.M)
        refs = re.search(r'^source_refs:\s*(\[[^\n]*\])\s*$', meta, re.M)
        if not status or status.group(1) not in PAGE_STATES:
            errors.append(str(path) + ': invalid page status')
        try:
            source_ids = json.loads(refs.group(1)) if refs else None
            if not isinstance(source_ids, list) or not source_ids:
                raise ValueError('expected non-empty source_refs array')
            if any(not isinstance(sid, str) or sid not in sources for sid in source_ids):
                raise ValueError('unknown source_refs ID')
            page_refs[str(path.relative_to(wiki))] = source_ids
        except (ValueError, TypeError) as exc:
            errors.append(str(path) + ': ' + str(exc))
    for uid, row in units.items():
        if row['status'] in {'processed', 'reused'}:
            if not any(row['source_id'] in page_refs.get(value, [])
                       for value in split_values(row['outputs'])):
                errors.append(uid + ': no thematic output cites its source_id')
    links = sum(check_links(path, errors) for path in wiki.rglob('*.md'))
    print(json.dumps({'sources': len(sources), 'units': len(units),
                      'thematic_pages': len(pages), 'local_links_checked': links,
                      'source_hash_check_requested': args.verify_source_hashes,
                      'scope': 'structural only; no curation or factual verification',
                      'errors': errors}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())

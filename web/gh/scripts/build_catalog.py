#!/usr/bin/env python3
"""Rebuild data/apps.json from the latest GitHub Releases of the repos in data/repos.txt.

Reads only public GitHub data. No scraping, no third-party API.

Usage:
    GITHUB_TOKEN=... python3 scripts/build_catalog.py

In GitHub Actions the token comes from secrets.GITHUB_TOKEN.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPOS_FILE = os.path.join(ROOT, 'data', 'repos.txt')
OVERRIDES_FILE = os.path.join(ROOT, 'data', 'overrides.json')
OUT_FILE = os.path.join(ROOT, 'data', 'apps.json')

API = 'https://api.github.com'
TOKEN = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN') or ''


def api(path):
    req = urllib.request.Request(API + path)
    req.add_header('Accept', 'application/vnd.github+json')
    req.add_header('X-GitHub-Api-Version', '2022-11-28')
    req.add_header('User-Agent', 'swadeshi-gh-store')
    if TOKEN:
        req.add_header('Authorization', 'Bearer ' + TOKEN)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        print('  HTTP %s for %s' % (e.code, path), file=sys.stderr)
        return None
    except Exception as e:
        print('  %s for %s' % (e, path), file=sys.stderr)
        return None


def human(n):
    if n >= 1048576:
        return '%.1f MB' % (n / 1048576.0)
    if n >= 1024:
        return '%.0f KB' % (n / 1024.0)
    return '%d B' % n


def title_from_repo(repo):
    name = repo.split('/')[-1]
    return ' '.join(w.capitalize() if w.islower() else w for w in name.replace('_', '-').split('-'))


def load_repos():
    out = []
    with open(REPOS_FILE, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.count('/') != 1:
                print('  skip malformed line: %s' % line, file=sys.stderr)
                continue
            out.append(line)
    return out



PLATFORM_EXT = {
    '.apk': 'android',
    '.exe': 'windows', '.msi': 'windows',
    '.dmg': 'macos', '.pkg': 'macos',
    '.appimage': 'linux', '.deb': 'linux', '.rpm': 'linux', '.snap': 'linux', '.flatpak': 'linux',
}
PLATFORM_ORDER = ['android', 'windows', 'macos', 'linux']


def platform_of(name):
    low = name.lower()
    for ext, plat in PLATFORM_EXT.items():
        if low.endswith(ext):
            return plat
    return None


DENS = ['xxxhdpi', 'xxhdpi', 'xhdpi', 'hdpi', 'mdpi', 'anydpi']


def find_icon(repo, branch):
    """Look for a raster launcher icon in the repo tree. Returns a raw URL or ''."""
    tree = api('/repos/%s/git/trees/%s?recursive=1' % (repo, branch))
    if not tree or 'tree' not in tree:
        return ''
    paths = [x['path'] for x in tree['tree'] if x['path'].lower().endswith(('.png', '.webp', '.jpg', '.jpeg'))]
    allic = [p for p in paths if 'ic_launcher' in p.lower()]

    def score(p):
        lp = p.lower()
        s = 0
        for i, d in enumerate(DENS):
            if d in lp:
                s = len(DENS) - i
                break
        if 'playstore' in lp:
            s += 10
        if 'mipmap' in lp:
            s += 5
        if 'drawable' in lp:
            s += 2
        return s

    cands = []
    for p in paths:
        lp = p.lower()
        if 'ic_launcher' in lp or '/icon' in lp or lp.endswith('appicon.png'):
            if 'round' in lp and len(allic) > 2:
                continue
            cands.append((score(p), p))
    if not cands:
        for p in paths:
            lp = p.lower()
            if any(k in lp for k in ('icon', 'logo', 'launcher', 'appicon', 'brand')) and \
               not any(k in lp for k in ('splash', 'notification', 'banner', 'screenshot', 'feature', 'promo')):
                cands.append((score(p) - 20 - p.count('/'), p))
    if not cands:
        return ''
    cands.sort(key=lambda c: (-c[0], len(c[1])))
    return 'https://raw.githubusercontent.com/%s/%s/%s' % (repo, branch, cands[0][1].replace(' ', '%20'))


def main():
    overrides = {}
    if os.path.exists(OVERRIDES_FILE):
        with open(OVERRIDES_FILE, encoding='utf-8') as f:
            overrides = {k: v for k, v in json.load(f).items() if not k.startswith('_')}

    apps = []
    for repo in load_repos():
        print('  %s' % repo)
        release = api('/repos/%s/releases/latest' % repo)
        if not release or 'assets' not in release:
            print('    no published release, skipped', file=sys.stderr)
            continue
        files = []
        for a in release['assets']:
            p = platform_of(a['name'])
            if p:
                files.append({'name': a['name'], 'size': a['size'],
                              'download_url': a['browser_download_url'], 'platform': p})
        if not files:
            print('    latest release has no supported build, skipped', file=sys.stderr)
            continue

        def rank(a):
            n = a['name'].lower()
            arch = 3
            if 'arm64' in n or 'aarch64' in n or 'universal' in n:
                arch = 0
            elif 'armeabi' in n:
                arch = 1
            elif 'x86' in n or 'x64' in n:
                arch = 2
            return (PLATFORM_ORDER.index(a['platform']), arch, -a['size'])

        files.sort(key=rank)
        per = {}
        for f in files:
            per.setdefault(f['platform'], f)
        platforms = [p for p in PLATFORM_ORDER if p in per]
        meta = api('/repos/%s' % repo) or {}
        ov = overrides.get(repo, {})
        primary = files[0]
        apps.append({
            'name': ov.get('name') or title_from_repo(repo),
            'description': (ov.get('description') or meta.get('description') or '')[:297].rstrip() + ('...' if len(ov.get('description') or meta.get('description') or '') > 297 else ''),
            'developer': (meta.get('owner') or {}).get('login') or repo.split('/')[0],
            'repo': repo,
            'repo_url': meta.get('html_url') or ('https://github.com/' + repo),
            'version': release.get('tag_name') or '',
            'platforms': platforms,
            'file_size': primary['size'],
            'size_human': human(primary['size']),
            'release_url': release.get('html_url') or '',
            'download_url': primary['download_url'],
            'downloads': [{
                'platform': p,
                'name': per[p]['name'],
                'size': per[p]['size'],
                'size_human': human(per[p]['size']),
                'download_url': per[p]['download_url'],
            } for p in platforms],
            'assets': [{
                'name': f['name'],
                'size': f['size'],
                'size_human': human(f['size']),
                'platform': f['platform'],
                'download_url': f['download_url'],
            } for f in files],
            'updated': (release.get('published_at') or '')[:10],
            'license': (meta.get('license') or {}).get('spdx_id') or '',
            'stars': meta.get('stargazers_count') or 0,
            'language': meta.get('language') or '',
            'icon': find_icon(repo, meta.get('default_branch') or 'main'),
        })

    apps.sort(key=lambda a: (-a['stars'], a['name'].lower()))
    doc = {
        'generated': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'source': 'GitHub Releases',
        'count': len(apps),
        'apps': apps,
    }
    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print('wrote %s with %d apps' % (OUT_FILE, len(apps)))


if __name__ == '__main__':
    main()

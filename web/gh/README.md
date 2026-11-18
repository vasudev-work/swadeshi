# Swadeshi GitHub

A static catalog of Android apps whose APK ships in a **public GitHub Release**.
No store, no account, no tracking, no APK hosted here.

Live: https://vasudev-work.github.io/swadeshi-gh-store/

This is a separate project from the Swadeshi Appstore page. Nothing is shared with it.

## How it works

```
data/repos.txt          one owner/repo per line, the only thing a human adds
        |
        v
scripts/build_catalog.py   GitHub REST API: repo + latest release + .apk assets
        |
        v
data/apps.json          the catalog, validated against schema/app.schema.json
        |
        v
index.html              fetches data/apps.json and renders the cards
```

A scheduled GitHub Actions workflow runs the script, checks the output against the schema, and commits `data/apps.json` only when it changed.

## The JSON schema

`schema/app.schema.json` is a JSON Schema 2020-12 document. Per app:

| Field | Type | Comes from |
|---|---|---|
| `name` | string | `data/overrides.json`, else derived from the repo name |
| `description` | string | repo description, or the override |
| `developer` | string | repo owner login |
| `repo` | `owner/repo` | `data/repos.txt` |
| `repo_url` | uri | repo `html_url` |
| `version` | string | release `tag_name`, exactly as published |
| `file_size` | integer | size of the primary APK asset, bytes |
| `size_human` | string | derived, e.g. `21.3 MB` |
| `release_url` | uri | release `html_url` |
| `download_url` | uri | asset `browser_download_url` of the primary APK |
| `assets[]` | array | every `.apk` on that release, largest first |
| `updated` | `YYYY-MM-DD` | release `published_at` |
| `license` | string | repo SPDX id, or empty |
| `stars` | integer | repo stargazers |
| `language` | string | repo primary language |

The top level is `{ generated, source, count, apps }`, and `count` must equal `apps.length`.

## Adding an app

1. Open `data/repos.txt` and add `owner/repo`.
2. Commit. The workflow runs, checks that the latest release actually carries an `.apk`, and rebuilds the catalog.
3. If the repo name is not a good app name, add an entry to `data/overrides.json`.

Nothing else is needed. There is no review queue and no hand-written metadata beyond the display name.

## Rules the workflow enforces

- A repo is skipped when its latest release is missing or has no `.apk` asset
- `count` must equal `apps.length`
- Every app must validate against the schema
- No duplicate `repo`
- The commit only happens when `data/apps.json` actually changed



## Platforms

The catalog is not Android only. A repo qualifies when its latest release ships any of:

| Platform | Extensions |
|---|---|
| Android | `.apk` |
| Windows | `.exe`, `.msi` |
| macOS | `.dmg`, `.pkg` |
| Linux | `.AppImage`, `.deb`, `.rpm`, `.snap`, `.flatpak` |

Each app carries `platforms[]` and one best download per platform in `downloads[]`; `assets[]` keeps every file. The page has a platform filter and labels the primary button per platform (Download APK / .exe / .dmg / .AppImage).

When several files exist for one platform, the picker prefers `arm64`/`universal`, then `armeabi`, then `x86`, then the largest.

## Icons

Each app's icon is the launcher PNG the developer already committed to their own repo. The builder walks the repo tree, prefers `mipmap-xxxhdpi/ic_launcher.png`, then falls back to any playstore icon, then to any file whose name contains icon/logo/launcher. The URL points at `raw.githubusercontent.com`, so nothing is copied here.

When a repo only ships a vector `ic_launcher.xml`, there is no raster to show and the card falls back to a coloured letter tile. That is why some cards show a letter: it is the honest state, not a bug.

## What this deliberately does not do

- No APK is copied here. Every download link is the developer's own GitHub Release URL, so the bytes come from them and the download counter stays theirs.
- No ratings, no download counts, no "trusted by" claims. GitHub does not publish per-release download counts in a form worth showing, and inventing them would be a lie.
- No automatic signature verification. The page says which release the APK came from; verifying the signing certificate is the user's job, and the app's own repo is one click away.
- No backend, no analytics, no cookies.

## Running it locally

```
python3 -m http.server 8000
# open http://localhost:8000
```

`data/apps.json` is fetched over HTTP, so opening `index.html` from the filesystem will show the error state instead.

To rebuild the catalog yourself:

```
GITHUB_TOKEN=ghp_... python3 scripts/build_catalog.py
```

Without a token you get 60 requests an hour, which is enough for about 25 repos.

## License

MIT. The apps listed keep their own licenses, shown per card.

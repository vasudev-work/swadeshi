# Swadeshi

One repo for the whole Swadeshi project. Five things used to live in five repos; they are
here as folders, each with its own job.

```
swadeshi/
├── android/            the Android app            (native Java, 1,489-app Play catalogue)
├── web/
│   ├── play/           web page for the Play catalogue
│   └── gh/             engine + page for the GitHub Releases catalogue
├── data/               the 1,489-app list as CSV / JSON / per-category files
└── .github/workflows/  one workflow, rebuilds the catalog daily
```

## The three web faces

| Path | Question it answers | Apps |
|---|---|---|
| `/web/play/` | Which Indian apps exist on the **Play Store**? | 1,489 |
| `/web/gh/` | Which Indian apps ship a build in a **public GitHub Release**? | 201 |

`web/play` and `web/gh` share **zero apps by name**. They are not duplicates.

## The data flows one way

```
web/gh/data/repos.txt          the only file a human edits
        |
        v
web/gh/scripts/build_catalog.py    GitHub API: repo, latest release, assets, icon
        |
        v
web/gh/data/apps.json          validated against web/gh/schema/app.schema.json
```

A workflow runs daily at 03:17 UTC, on any change to the list or the script, and on
demand. It validates the output against the schema and commits only when something
actually changed.

## Android app

`android/` is the full Gradle project. It reads `app/src/main/assets/indian_apps.json`,
which is the Play catalogue. Build with the usual
`./gradlew assembleRelease` and your own `keystore.properties`.

## Where things came from

Kosha is deliberately **not** here. It lists apps from anywhere, including non-Indian
projects, so it is a different product with a different rule. It stays in its own repo.

This repo merges what used to be four separate repositories. The old ones still exist and
still serve their Pages sites; nothing broke. Treat this one as the source of truth from
now on.

MIT.

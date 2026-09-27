# Vernesystems/.github

The public profile of [Verne](https://vernesystems.com) on GitHub.

| Path                                   | What it does                                                                        |
| -------------------------------------- | ----------------------------------------------------------------------------------- |
| `profile/README.md`                    | Shown at [github.com/Vernesystems](https://github.com/Vernesystems)                 |
| `profile/assets/`                      | Animated hero and footer SVGs, dark and light                                       |
| `scripts/render_assets.py`             | Regenerates the SVGs (`pip install fonttools uharfbuzz`)                            |
| `scripts/update_notes.py`              | Refreshes the Field notes list from `blog.vernesystems.com/feed.xml` (stdlib only)  |
| `.github/workflows/field-notes.yml`    | Runs the refresh daily and commits only when the list changes                       |

GitHub pauses scheduled workflows after 60 days without repository activity. If the list stops updating, run the workflow once from the Actions tab.

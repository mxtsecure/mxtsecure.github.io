# mxtsecure.github.io

A lightweight static site for Xiangtao Meng's research profile. Content is centrally managed in `data/site.json` and rendered into the `docs/` directory for GitHub Pages.

## Build
The build script uses only Python's standard library and reads content from `data/site.json`.
```bash
python build.py
```

### Layout toggles and assets

- Optional sections (news, publications, projects, resources, blog, essays, legacy archive) are gated by the `toggles` map in `data/site.json`.
- Navigation items and hero actions share the same toggle keys to keep optional entrances consistent.
- Images, downloads, and archived jemdoc placeholders live under `static/assets/` and are referenced via relative paths (for example `assets/downloads/cv.pdf`).

### Styles

- `static/assets/styles.scss` documents the tokenized theme (light/dark ready) and component primitives; `static/assets/styles.css` is the compiled output copied into `docs/` during the build.

## Deploy
Set GitHub Pages to serve from the `docs/` folder on the default branch. The build step copies assets and photos while filling missing links/images with placeholders so the page can always render.

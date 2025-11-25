# mxtsecure.github.io

A lightweight static site for Xiangtao Meng's research profile. Content is centrally managed in `data/site.json` and rendered into the `docs/` directory for GitHub Pages.

## Build
The build script uses only Python's standard library.
```bash
python build.py
```

## Deploy
Set GitHub Pages to serve from the `docs/` folder on the default branch. The build step copies assets and photos while filling missing links/images with placeholders so the page can always render.

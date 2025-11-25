from __future__ import annotations
import json
import shutil
from pathlib import Path
from string import Template
from typing import Any, Dict, List
import sys

BASE_DIR = Path(__file__).parent
DATA_PATH = BASE_DIR / "data" / "site.json"
TEMPLATE_DIR = BASE_DIR / "templates"
OUTPUT_DIR = BASE_DIR / "docs"
STATIC_DIR = BASE_DIR / "static" / "assets"
STATIC_ROOT = BASE_DIR / "static"
PHOTOS_DIR = BASE_DIR / "photos"

PLACEHOLDER_IMAGE = "assets/images/placeholder.svg"
PLACEHOLDER_LINK = "#"


def asset_exists(relative_path: str) -> bool:
    """Check whether an asset exists in any of the expected source locations."""
    rel = Path(relative_path)
    return any(
        candidate.exists()
        for candidate in [
            BASE_DIR / rel,
            STATIC_ROOT / rel,
            PHOTOS_DIR / rel.name if rel.parts[:2] == ("assets", "photos") else PHOTOS_DIR / rel,
        ]
    )


def load_data() -> Dict[str, Any]:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Missing data file: {DATA_PATH}")
    with DATA_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def ensure_links_and_images(data: Dict[str, Any]) -> Dict[str, Any]:
    assets = data.get("assets", {})
    placeholder_image = assets.get("placeholder_image", PLACEHOLDER_IMAGE)

    for item in data.get("timeline", []):
        if not item.get("link"):
            item["link"] = PLACEHOLDER_LINK

    for pub in data.get("publications", []):
        pub_links = pub.get("links") or {}
        if not pub_links:
            print(f"[warn] Publication '{pub.get('title')}' missing links, applying placeholder.")
        pub["links"] = {label: url or PLACEHOLDER_LINK for label, url in pub_links.items()} or {"link": PLACEHOLDER_LINK}

    for project in data.get("projects", []):
        image_path = project.get("image")
        if not image_path:
            print(f"[warn] Project '{project.get('name')}' missing image, applying placeholder.")
            project["image"] = placeholder_image
        elif not asset_exists(image_path):
            print(f"[warn] Project '{project.get('name')}' image not found at {image_path}, applying placeholder.")
            project["image"] = placeholder_image

    profile = data.get("profile", {})
    avatar_path = profile.get("avatar") or assets.get("avatar")
    if not avatar_path:
        print("[warn] Profile avatar missing, applying placeholder.")
        profile["avatar"] = placeholder_image
    elif not asset_exists(avatar_path):
        print(f"[warn] Profile avatar not found at {avatar_path}, applying placeholder.")
        profile["avatar"] = placeholder_image

    return data


def prepare_output_dir() -> None:
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)


def copy_assets() -> None:
    assets_out = OUTPUT_DIR / "assets"
    shutil.copytree(STATIC_DIR, assets_out)

    photos_out = assets_out / "photos"
    if PHOTOS_DIR.exists():
        shutil.copytree(PHOTOS_DIR, photos_out)
    else:
        photos_out.mkdir(parents=True, exist_ok=True)


def is_enabled(toggle_key: str | None, toggles: Dict[str, Any], fallback: bool = True) -> bool:
    if toggle_key is None:
        return fallback
    return bool(toggles.get(toggle_key, fallback))


def render_nav(navigation: List[Dict[str, Any]], toggles: Dict[str, Any], inline: bool = False) -> str:
    links = []
    for item in navigation:
        if not is_enabled(item.get("toggle"), toggles, item.get("enabled", True)):
            continue
        target = item.get("target", "#")
        extra_attrs = " target=\"_blank\" rel=\"noopener\"" if item.get("external") else ""
        cls = "nav-anchor" if inline else "nav-link"
        links.append(f"<a class=\"{cls}\" href=\"{target}\"{extra_attrs}>{item['label']}</a>")
    return "".join(links)


def render_highlights(highlights: List[Dict[str, Any]]) -> str:
    cards = []
    for item in highlights:
        cards.append(
            f"<div class=\"highlight-card\"><h3>{item['title']}</h3><p>{item['description']}</p></div>"
        )
    return "".join(cards)


def render_profile_sidebar(
    profile: Dict[str, Any], navigation: List[Dict[str, Any]], highlights: List[Dict[str, Any]], toggles: Dict[str, Any]
) -> str:
    social_html = "".join(
        f"<a class=\"inline-link\" href=\"{social['url']}\" target=\"_blank\" rel=\"noopener\">{social['label']}</a>"
        for social in profile.get("socials", [])
    )
    actions_html = "".join(
        f"<a class=\"inline-button\" href=\"{action['url']}\" target=\"_blank\" rel=\"noopener\">{action['label']}</a>"
        for action in profile.get("actions", [])
        if is_enabled(action.get("toggle"), toggles, action.get("enabled", True))
    )
    focus_html = "".join(f"<li>{item['title']} — {item['description']}</li>" for item in highlights)
    nav_html = render_nav(navigation, toggles, inline=True)
    return f"""
<aside class=\"sidebar\" id=\"about\">\n  <div class=\"avatar\"><img src=\"{profile['avatar']}\" alt=\"Portrait of {profile['name']}\" loading=\"lazy\"></div>\n  <p class=\"eyebrow\">{profile.get('native_name','')}</p>\n  <h1>{profile['name']}</h1>\n  <p class=\"role\">{profile['role']}<br>{profile['organization']}</p>\n  <p class=\"muted\">{profile['location']}</p>\n  <p class=\"lede\">{profile['tagline']}\n  </p>\n  <div class=\"contact-row\">\n    <a class=\"inline-link\" href=\"mailto:{profile['email']}\">{profile['email']}</a>\n    {social_html}\n  </div>\n  <div class=\"nav-column\">{nav_html}</div>\n  <div class=\"focus\">\n    <p class=\"eyebrow\">Focus</p>\n    <ul>{focus_html}</ul>\n  </div>\n  <div class=\"actions\">{actions_html}</div>\n</aside>\n"""


def render_timeline(timeline: List[Dict[str, Any]]) -> str:
    rows = []
    for item in timeline:
        rows.append(
            """
<div class=\"list-row\">\n  <div class=\"list-label\">{date}</div>\n  <div class=\"list-body\">\n    <div class=\"item-title\">{title}</div>\n    <p class=\"muted\">{desc}</p>\n    <a href=\"{link}\" class=\"inline-link\" target=\"_blank\" rel=\"noopener\">Read more</a>\n  </div>\n</div>\n""".format(date=item["date"], title=item["title"], desc=item["description"], link=item["link"])
        )
    return "".join(rows)


def render_publications(publications: List[Dict[str, Any]]) -> str:
    rows = []
    for paper in publications:
        tags = " ".join(f"<span class=\"tag\">{tag}</span>" for tag in paper.get("highlights", []))
        links = " ".join(
            f"<a href=\"{url}\" class=\"inline-link\" target=\"_blank\" rel=\"noopener\">{label.capitalize()}</a>"
            for label, url in paper.get("links", {}).items()
        )
        rows.append(
            """
<div class=\"list-row\">\n  <div class=\"list-label\">{year}</div>\n  <div class=\"list-body\">\n    <div class=\"item-title\">{title}</div>\n    <div class=\"muted\">{authors}</div>\n    <div class=\"meta\">{venue} · {tags}</div>\n    <div class=\"links-row\">{links}</div>\n  </div>\n</div>\n""".format(
                year=paper["year"],
                title=paper["title"],
                authors=paper["authors"],
                venue=paper["venue"],
                tags=tags,
                links=links,
            )
        )
    return "".join(rows)


def render_projects(projects: List[Dict[str, Any]]) -> str:
    rows = []
    for project in projects:
        tags = " ".join(f"<span class=\"tag\">{tag}</span>" for tag in project.get("tags", []))
        rows.append(
            """
<div class=\"list-row project-row\">\n  <div class=\"thumb\"><img src=\"{img}\" alt=\"{name}\" loading=\"lazy\"></div>\n  <div class=\"list-body\">\n    <div class=\"item-title\">{name}</div>\n    <p class=\"muted\">{summary}</p>\n    <div class=\"meta\">{tags}</div>\n  </div>\n</div>\n""".format(
                img=project["image"], name=project["name"], summary=project["summary"], tags=tags
            )
        )
    return "".join(rows)


def render_resources(resources: List[Dict[str, Any]]) -> str:
    blocks = []
    for group in resources:
        item_rows = []
        for item in group.get("items", []):
            note = f" <span class=\"muted\">— {item['note']}</span>" if item.get("note") else ""
            item_rows.append(
                f"<li><a class=\"inline-link\" href=\"{item['url']}\" target=\"_blank\" rel=\"noopener\">{item['title']}</a>{note}</li>"
            )
        blocks.append(f"<div class=\"resource-block\"><div class=\"item-title\">{group['category']}</div><ul>{''.join(item_rows)}</ul></div>")
    return "".join(blocks)


def render_writings(key: str, block: Dict[str, Any]) -> str:
    entries = block.get("entries", [])
    cards: List[str] = []
    for item in entries:
        badges = "".join(f"<span class=\"badge\">{badge}</span>" for badge in item.get("badges", []))
        actions = "".join(
            f"<a class=\"btn btn-ghost\" href=\"{action['url']}\" target=\"_blank\" rel=\"noopener\">{action['label']}</a>"
            for action in item.get("actions", [])
        )
        cards.append(
            f"<article class=\"card writing-card\">"
            f"<div class=\"card-meta\"><span class=\"pill\">{item.get('date','')}&nbsp;</span>{badges}</div>"
            f"<h3>{item['title']}</h3>"
            f"<p class=\"muted\">{item.get('summary','')}</p>"
            f"<div class=\"links-row\"><a class=\"btn btn-outline\" href=\"{item['url']}\" target=\"_blank\" rel=\"noopener\">Read</a>{actions}</div>"
            "</article>"
        )

    more_link = block.get("archive_link")
    archive_html = (
        f"<div class=\"section-foot\"><a class=\"text-link\" href=\"{more_link}\" target=\"_blank\" rel=\"noopener\">View more</a></div>"
        if more_link
        else ""
    )

    return (
        f"<section id=\"{key}\" class=\"section\">"
        f"<div class=\"section-header\"><p class=\"eyebrow\">{block.get('eyebrow','Writings')}</p><h2>{block.get('title','Writings')}</h2><p class=\"lede\">{block.get('description','')}</p></div>"
        f"<div class=\"cards-grid writing-grid\">{''.join(cards)}</div>{archive_html}</section>"
    )


def render_archive_notice(archive: Dict[str, Any]) -> str:
    return (
        "<section id=\"archive\" class=\"section section-compact\">"
        "<div class=\"panel inline-panel\">"
        f"<div><p class=\"eyebrow\">Legacy</p><h3>{archive.get('label','Legacy archive')}</h3>"
        f"<p class=\"muted\">{archive.get('summary','Legacy jemdoc content has been archived.')}</p></div>"
        f"<a class=\"btn btn-outline\" href=\"{archive.get('url','#')}\" target=\"_blank\" rel=\"noopener\">Open archive</a>"
        "</div></section>"
    )


def render_sections(data: Dict[str, Any]) -> str:
    sections: List[str] = []
    toggles = data.get("toggles", {})

    if is_enabled("news", toggles, True):
        sections.append(
            f"<section id=\"news\" class=\"section\">"
            f"<div class=\"section-header\"><p class=\"eyebrow\">Updates</p><h2>Latest News</h2></div>"
            f"<div class=\"list-stack\">{render_timeline(data.get('timeline', []))}</div></section>"
        )

    if is_enabled("publications", toggles, True):
        sections.append(
            f"<section id=\"publications\" class=\"section\">"
            f"<div class=\"section-header\"><p class=\"eyebrow\">Selected Works</p><h2>Publications</h2></div>"
            f"<div class=\"list-stack\">{render_publications(data.get('publications', []))}</div></section>"
        )

    if is_enabled("projects", toggles, True):
        sections.append(
            f"<section id=\"projects\" class=\"section\">"
            f"<div class=\"section-header\"><p class=\"eyebrow\">Research & Services</p><h2>Projects</h2></div>"
            f"<div class=\"list-stack\">{render_projects(data.get('projects', []))}</div></section>"
        )

    if is_enabled("resources", toggles, True):
        sections.append(
            f"<section id=\"resources\" class=\"section\">"
            f"<div class=\"section-header\"><p class=\"eyebrow\">Notes & Links</p><h2>Resources</h2></div>"
            f"<div class=\"resource-list\">{render_resources(data.get('resources', []))}</div></section>"
        )

    writings = data.get("writings", {})
    if is_enabled("blog", toggles) and writings.get("blog"):
        sections.append(render_writings("blog", writings["blog"]))
    if is_enabled("essays", toggles) and writings.get("essays"):
        sections.append(render_writings("essays", writings["essays"]))

    if is_enabled("legacy_archive", toggles) and data.get("archives", {}).get("legacy_jemdoc"):
        sections.append(render_archive_notice(data["archives"]["legacy_jemdoc"]))

    return "".join(sections)


def render_page(data: Dict[str, Any]) -> str:
    base_tpl = Template((TEMPLATE_DIR / "base.html").read_text(encoding="utf-8"))
    toggles = data.get("toggles", {})
    nav_html = render_nav(data.get("navigation", []), toggles, inline=False)
    footer_links = "".join(
        f"<a href=\"{link['url']}\" target=\"_blank\" rel=\"noopener\">{link['label']}</a>"
        for link in data.get("footer", {}).get("links", [])
    )
    sidebar_html = render_profile_sidebar(data["profile"], data.get("navigation", []), data.get("highlights", []), toggles)
    content_html = f"<div class=\"layout\">{sidebar_html}<div class=\"content\">{render_sections(data)}</div></div>"
    return base_tpl.substitute(
        title=data.get("site", {}).get("title", "Research Homepage"),
        description=data.get("site", {}).get("description", ""),
        logo=data.get("profile", {}).get("name", ""),
        nav=nav_html,
        content=content_html,
        theme=data.get("site", {}).get("theme", "dark"),
        footer_links=footer_links,
        footer_note=data.get("footer", {}).get("note", "")
    )


def write_output(html: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "index.html").write_text(html, encoding="utf-8")


def main() -> int:
    try:
        data = load_data()
    except FileNotFoundError as exc:
        print(exc)
        return 1

    data = ensure_links_and_images(data)
    prepare_output_dir()
    copy_assets()
    html = render_page(data)
    write_output(html)
    print(f"Site generated at {OUTPUT_DIR.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

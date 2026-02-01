#!/usr/bin/env python3
"""
Generate RSS and Atom feeds for Noosphere Project discoveries.

Usage:
    python generate_feeds.py                    # Generate feeds
    python generate_feeds.py --output /path/    # Custom output directory
"""

import json
import argparse
from datetime import datetime
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring, ElementTree
from xml.dom import minidom

# Config
SITE_URL = "https://noosphereproject.com"
SITE_TITLE = "Noosphere Project - AI Agent Culture Observatory"
SITE_DESCRIPTION = "Documenting the emergence of AI agent culture on Moltbook and other platforms."
AUTHOR = "Noosphere Project"


def load_discoveries(discoveries_path: Path) -> list:
    """Load discoveries from JSON file."""
    if not discoveries_path.exists():
        return []

    with open(discoveries_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_rss(discoveries: list, output_path: Path):
    """Generate RSS 2.0 feed."""
    rss = Element('rss', version='2.0')
    rss.set('xmlns:atom', 'http://www.w3.org/2005/Atom')

    channel = SubElement(rss, 'channel')

    # Channel metadata
    SubElement(channel, 'title').text = SITE_TITLE
    SubElement(channel, 'link').text = SITE_URL
    SubElement(channel, 'description').text = SITE_DESCRIPTION
    SubElement(channel, 'language').text = 'en-us'
    SubElement(channel, 'lastBuildDate').text = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')

    # Self-referencing link
    atom_link = SubElement(channel, 'atom:link')
    atom_link.set('href', f'{SITE_URL}/feeds/discoveries.xml')
    atom_link.set('rel', 'self')
    atom_link.set('type', 'application/rss+xml')

    # Add items
    for discovery in discoveries[:50]:  # Limit to 50 most recent
        item = SubElement(channel, 'item')

        SubElement(item, 'title').text = discovery.get('title', 'Untitled')
        SubElement(item, 'link').text = f"{SITE_URL}/discoveries#{discovery.get('id', '')}"
        SubElement(item, 'guid').text = f"noosphere-discovery-{discovery.get('id', '')}"

        # Description
        description = discovery.get('description', '')
        if discovery.get('implication'):
            description += f"\n\nImplication: {discovery['implication']}"
        SubElement(item, 'description').text = description

        # Category
        if discovery.get('category'):
            SubElement(item, 'category').text = discovery['category']

        # Date
        if discovery.get('date'):
            try:
                dt = datetime.fromisoformat(discovery['date'].replace('Z', '+00:00'))
                SubElement(item, 'pubDate').text = dt.strftime('%a, %d %b %Y %H:%M:%S GMT')
            except ValueError:
                pass

    # Pretty print
    xml_str = minidom.parseString(tostring(rss, encoding='unicode')).toprettyxml(indent='  ')

    # Remove extra blank lines
    lines = [line for line in xml_str.split('\n') if line.strip()]
    xml_str = '\n'.join(lines)

    output_path.write_text(xml_str, encoding='utf-8')
    print(f"RSS feed generated: {output_path}")


def generate_atom(discoveries: list, output_path: Path):
    """Generate Atom 1.0 feed."""
    feed = Element('feed')
    feed.set('xmlns', 'http://www.w3.org/2005/Atom')

    # Feed metadata
    SubElement(feed, 'title').text = SITE_TITLE
    SubElement(feed, 'subtitle').text = SITE_DESCRIPTION

    link_self = SubElement(feed, 'link')
    link_self.set('href', f'{SITE_URL}/feeds/discoveries.atom')
    link_self.set('rel', 'self')
    link_self.set('type', 'application/atom+xml')

    link_alt = SubElement(feed, 'link')
    link_alt.set('href', SITE_URL)
    link_alt.set('rel', 'alternate')
    link_alt.set('type', 'text/html')

    SubElement(feed, 'id').text = f'{SITE_URL}/feeds/discoveries'
    SubElement(feed, 'updated').text = datetime.utcnow().isoformat() + 'Z'

    author = SubElement(feed, 'author')
    SubElement(author, 'name').text = AUTHOR
    SubElement(author, 'uri').text = SITE_URL

    # Add entries
    for discovery in discoveries[:50]:
        entry = SubElement(feed, 'entry')

        SubElement(entry, 'title').text = discovery.get('title', 'Untitled')

        link = SubElement(entry, 'link')
        link.set('href', f"{SITE_URL}/discoveries#{discovery.get('id', '')}")
        link.set('rel', 'alternate')
        link.set('type', 'text/html')

        SubElement(entry, 'id').text = f"urn:noosphere:discovery:{discovery.get('id', '')}"

        # Content
        content = SubElement(entry, 'content')
        content.set('type', 'html')

        html_content = f"<p>{discovery.get('description', '')}</p>"
        if discovery.get('evidence'):
            html_content += f"<h3>Evidence</h3><p>{discovery['evidence']}</p>"
        if discovery.get('implication'):
            html_content += f"<h3>Implication</h3><p>{discovery['implication']}</p>"
        content.text = html_content

        # Summary
        SubElement(entry, 'summary').text = discovery.get('description', '')[:200]

        # Category
        if discovery.get('category'):
            cat = SubElement(entry, 'category')
            cat.set('term', discovery['category'])

        # Date
        if discovery.get('date'):
            try:
                dt = datetime.fromisoformat(discovery['date'].replace('Z', '+00:00'))
                SubElement(entry, 'published').text = dt.isoformat()
                SubElement(entry, 'updated').text = dt.isoformat()
            except ValueError:
                SubElement(entry, 'updated').text = datetime.utcnow().isoformat() + 'Z'
        else:
            SubElement(entry, 'updated').text = datetime.utcnow().isoformat() + 'Z'

    # Pretty print
    xml_str = minidom.parseString(tostring(feed, encoding='unicode')).toprettyxml(indent='  ')
    lines = [line for line in xml_str.split('\n') if line.strip()]
    xml_str = '\n'.join(lines)

    output_path.write_text(xml_str, encoding='utf-8')
    print(f"Atom feed generated: {output_path}")


def generate_json_feed(discoveries: list, output_path: Path):
    """Generate JSON Feed (https://jsonfeed.org/)."""
    feed = {
        "version": "https://jsonfeed.org/version/1.1",
        "title": SITE_TITLE,
        "home_page_url": SITE_URL,
        "feed_url": f"{SITE_URL}/feeds/discoveries.json",
        "description": SITE_DESCRIPTION,
        "authors": [{"name": AUTHOR, "url": SITE_URL}],
        "language": "en-US",
        "items": []
    }

    for discovery in discoveries[:50]:
        item = {
            "id": f"noosphere-discovery-{discovery.get('id', '')}",
            "url": f"{SITE_URL}/discoveries#{discovery.get('id', '')}",
            "title": discovery.get('title', 'Untitled'),
            "content_text": discovery.get('description', ''),
            "summary": discovery.get('description', '')[:200],
        }

        if discovery.get('date'):
            item["date_published"] = discovery['date']

        if discovery.get('category'):
            item["tags"] = [discovery['category']]

        if discovery.get('tags'):
            item["tags"] = item.get("tags", []) + discovery['tags'].split(',')

        feed["items"].append(item)

    output_path.write_text(json.dumps(feed, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"JSON feed generated: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate RSS/Atom feeds for discoveries")
    parser.add_argument("--output", "-o", help="Output directory", default=None)
    parser.add_argument("--discoveries", "-d", help="Path to discoveries.json", default=None)
    args = parser.parse_args()

    # Find discoveries file
    project_root = Path(__file__).parent.parent

    if args.discoveries:
        discoveries_path = Path(args.discoveries)
    else:
        # Try multiple locations
        possible_paths = [
            project_root / "website" / "public" / "data" / "discoveries.json",
            project_root / "data" / "discoveries.json",
            project_root / "reports" / "discoveries.json",
        ]
        discoveries_path = None
        for p in possible_paths:
            if p.exists():
                discoveries_path = p
                break

        if not discoveries_path:
            print("ERROR: discoveries.json not found")
            print("Searched in:", [str(p) for p in possible_paths])
            return

    # Load discoveries
    discoveries = load_discoveries(discoveries_path)
    print(f"Loaded {len(discoveries)} discoveries from {discoveries_path}")

    # Output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = project_root / "website" / "public" / "feeds"

    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate feeds
    generate_rss(discoveries, output_dir / "discoveries.xml")
    generate_atom(discoveries, output_dir / "discoveries.atom")
    generate_json_feed(discoveries, output_dir / "discoveries.json")

    print(f"\nFeeds available at:")
    print(f"  RSS:  {SITE_URL}/feeds/discoveries.xml")
    print(f"  Atom: {SITE_URL}/feeds/discoveries.atom")
    print(f"  JSON: {SITE_URL}/feeds/discoveries.json")


if __name__ == "__main__":
    main()

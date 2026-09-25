#!/usr/bin/env python3
"""Create normative rules from tag files.

Every normative tag (an AsciiDoc anchor whose name starts with "norm:") is one normative rule.
The rule's name is the tag's name without the "norm:" prefix. There is no separate definition
of normative rules and no mapping between rules and tags.
"""

import json
import sys
import argparse
from typing import Dict, List, Optional, Any, Tuple
from def_text_to_html import tag2html_link
from shared_utils import (
    load_json_object,
    make_log_helpers,
)
from tag_text_to_html import convert_tag_text_to_html

PN = "create_normative_rules.py"

NORM_PREFIX = "norm:"

# Names/prefixes for tables in HTML output.
NORM_RULES_CH_TABLE_NAME_PREFIX = "table-norm-rules-ch-"

# AsciiDoc section level of a chapter. Level 0 sections are parts (e.g., the volumes of a book).
CHAPTER_LEVEL = 1

error, info, fatal = make_log_helpers(PN)


class NormativeRule:
    """Holds all information for one normative rule (i.e., one normative tag)."""

    def __init__(self, tag_name: str, tag_filename: str, text: str, chapter_name: str, chapter_key: str):
        if not isinstance(tag_name, str):
            fatal(f"Need String for tag_name but passed a {type(tag_name).__name__}")
        if not isinstance(tag_filename, str):
            fatal(f"Need String for tag_filename but passed a {type(tag_filename).__name__}")
        if not isinstance(text, str):
            fatal(f"Need String for text but passed a {type(text).__name__}")
        if not isinstance(chapter_name, str):
            fatal(f"Need String for chapter_name but passed a {type(chapter_name).__name__}")
        if not isinstance(chapter_key, str):
            fatal(f"Need String for chapter_key but passed a {type(chapter_key).__name__}")

        self.tag_name = tag_name
        self.name = tag_name[len(NORM_PREFIX):]
        self.tag_filename = tag_filename
        self.text = text
        self.chapter_name = chapter_name
        # Unique key for the chapter (chapter titles such as "Introduction" can repeat).
        self.chapter_key = chapter_key


def parse_argv() -> Tuple[List[str], Dict[str, str], str, str]:
    """Parse command line arguments.

    Returns:
        Tuple of (tag_fnames, tag_fname2url, output_fname, output_format)
    """
    parser = argparse.ArgumentParser(
        description='Creates list of normative rules and stores them in <output-filename> (JSON format).',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('-j', action='store_const', const='json', dest='output_format',
                        default='json', help='Set output format to JSON (default)')
    parser.add_argument('--html', action='store_const', const='html', dest='output_format',
                        help='Set output format to HTML')
    parser.add_argument('-t', action='append', dest='tag_fnames', metavar='fname',
                        help='Normative tag filename (JSON format)')
    parser.add_argument('-tag2url', action='append', nargs=2, dest='tag2url_list',
                        metavar=('tag-fname', 'url'),
                        help='Maps from tag fname to corresponding URL to stds doc')
    parser.add_argument('output_fname', help='Output filename')

    args = parser.parse_args()

    # Validate required arguments
    if not args.tag_fnames:
        info("Missing normative tag filename(s)")
        parser.print_help()
        sys.exit(1)

    # Build tag_fname2url dictionary
    tag_fname2url = {}
    if args.tag2url_list:
        for tag_fname, url in args.tag2url_list:
            tag_fname2url[tag_fname] = url

    if not tag_fname2url:
        info("Missing -tag2url command line options")
        parser.print_help()
        sys.exit(1)

    return (args.tag_fnames, tag_fname2url, args.output_fname, args.output_format)


def find_tag_chapters(tag_fname: str, sections: Dict[str, Any]) -> Dict[str, Tuple[str, str]]:
    """Return a Dict from tag name to (chapter name, chapter key) using the section tree in a tag file.

    A tag's chapter is its nearest enclosing section of level CHAPTER_LEVEL. A tag outside any
    chapter (e.g., directly in a part or in the preamble) uses its nearest enclosing section instead.
    """
    if not isinstance(sections, dict):
        fatal(f"'sections' must be an object in {tag_fname}")

    tag2chapter: Dict[str, Tuple[str, str]] = {}

    def walk(node: Dict[str, Any], chapter: Optional[Dict[str, Any]], nearest: Optional[Dict[str, Any]]):
        for key in ("children", "tags"):
            if not isinstance(node.get(key), list):
                fatal(f"Section {node.get('title')!r} in {tag_fname} has no '{key}' list")

        if node is not sections:
            nearest = node
            level = node.get("level")
            if not isinstance(level, int):
                fatal(f"Section {node.get('title')!r} in {tag_fname} has no integer 'level'. "
                      f"Rebuild the tag file with the current tags.rb backend.")
            if level == CHAPTER_LEVEL:
                chapter = node

        owner = chapter if chapter is not None else nearest
        for tag_name in node["tags"]:
            if owner is None:
                tag2chapter[tag_name] = ("", f"{tag_fname}#")
            else:
                tag2chapter[tag_name] = (owner.get("title") or "", f"{tag_fname}#{owner.get('id')}")

        for child in node["children"]:
            walk(child, chapter, nearest)

    walk(sections, None, None)
    return tag2chapter


def load_rules(tag_fnames: List[str]) -> List[NormativeRule]:
    """Load the contents of all normative tag files in JSON format.

    Returns:
        List of NormativeRule objects in tag file order and document order within each tag file.
    """
    if not isinstance(tag_fnames, list):
        fatal(f"Need List[String] for tag_fnames but passed a {type(tag_fnames).__name__}")

    rules: List[NormativeRule] = []
    tag_name2fname: Dict[str, str] = {}

    for tag_fname in tag_fnames:
        info(f"Loading tag file {tag_fname}")
        file_data = load_json_object(tag_fname, fatal)

        tags_data = file_data.get("tags")
        if tags_data is None:
            fatal(f"Missing 'tags' key in {tag_fname}")
        if not isinstance(tags_data, dict):
            fatal(f"'tags' must be an object in {tag_fname}")
        assert isinstance(tags_data, dict)

        sections = file_data.get("sections")
        if sections is None:
            fatal(f"Missing 'sections' key in {tag_fname}")
        tag2chapter = find_tag_chapters(tag_fname, sections)

        for tag_name, text in tags_data.items():
            if not isinstance(tag_name, str):
                fatal(f"Tag name {tag_name} in file {tag_fname} is a {type(tag_name).__name__} instead of a String")

            if not isinstance(text, str):
                fatal(f"Tag name {tag_name} in file {tag_fname} is a {type(text).__name__} instead of a String\n"
                      f"{PN}:   If the AsciiDoc anchor for {tag_name} is before an AsciiDoc 'Description List' term, "
                      f"move to after term on its own line.")

            if not tag_name.startswith(NORM_PREFIX):
                fatal(f"Tag name {tag_name} in file {tag_fname} doesn't start with \"{NORM_PREFIX}\"")

            if tag_name in tag_name2fname:
                fatal(f"Tag name {tag_name} in file {tag_fname} already defined in file {tag_name2fname[tag_name]}")
            tag_name2fname[tag_name] = tag_fname

            if tag_name not in tag2chapter:
                fatal(f"Tag name {tag_name} in file {tag_fname} isn't in the file's section tree")
            chapter_name, chapter_key = tag2chapter[tag_name]

            rules.append(NormativeRule(tag_name, tag_fname, text, chapter_name, chapter_key))

    return rules


def create_normative_rules_hash(rules: List[NormativeRule],
                                tag_fname2url: Dict[str, str]) -> Dict[str, List[Dict[str, Any]]]:
    """Returns a Dict with just one entry called "normative_rules" that contains a List of Dicts of all normative rules.

    Dict is suitable for JSON/YAML serialization.
    """
    if not isinstance(rules, list):
        fatal(f"Need List[NormativeRule] for rules but was passed a {type(rules).__name__}")
    if not isinstance(tag_fname2url, dict):
        fatal(f"Need Dict for tag_fname2url but passed a {type(tag_fname2url).__name__}")

    info("Creating normative rules from tag files")

    ret: Dict[str, List[Dict[str, Any]]] = {"normative_rules": []}

    for nr in rules:
        url = tag_fname2url.get(nr.tag_filename)
        if url is None:
            fatal(f"No fname tag to URL mapping (-tag2url cmd line arg) for tag fname {nr.tag_filename} for tag name {nr.tag_name}")

        ret["normative_rules"].append({
            "name": nr.name,
            "chapter_name": nr.chapter_name,
            "text": nr.text,
            "tag_filename": nr.tag_filename,
            "stds_doc_url": url
        })

    return ret


def output_json(filename: str, normative_rules_hash: Dict[str, List[Dict[str, Any]]]):
    """Store normative rules in JSON output file."""
    if not isinstance(filename, str):
        fatal(f"Need String for filename but passed a {type(filename).__name__}")
    if not isinstance(normative_rules_hash, dict):
        fatal(f"Need Dict for normative_rules_hash but passed a {type(normative_rules_hash).__name__}")

    # Serialize normative_rules_hash to JSON format String.
    serialized_string = json.dumps(normative_rules_hash, indent=2, ensure_ascii=False)

    # Write serialized string to desired output file.
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(serialized_string)
    except Exception as e:
        fatal(f"Error writing to {filename}: {e}")


def output_html(filename: str, rules: List[NormativeRule], tag_fname2url: Dict[str, str]):
    """Store normative rules in HTML output file."""
    if not isinstance(filename, str):
        fatal(f"Need String for filename but passed a {type(filename).__name__}")
    if not isinstance(rules, list):
        fatal(f"Need List[NormativeRule] for rules but passed a {type(rules).__name__}")
    if not isinstance(tag_fname2url, dict):
        fatal(f"Need Dict for tag_fname2url but passed a {type(tag_fname2url).__name__}")

    # Organize rules by chapter, keeping document order. Each dict key is a chapter key.
    chapter_keys: List[str] = []
    chapter_names: Dict[str, str] = {}
    rules_by_chapter: Dict[str, List[NormativeRule]] = {}
    for nr in rules:
        if nr.chapter_key not in rules_by_chapter:
            chapter_keys.append(nr.chapter_key)
            chapter_names[nr.chapter_key] = nr.chapter_name
            rules_by_chapter[nr.chapter_key] = []
        rules_by_chapter[nr.chapter_key].append(nr)

    # Create list of all table names in order.
    table_names = [f"{NORM_RULES_CH_TABLE_NAME_PREFIX}{table_num}" for table_num in range(1, len(chapter_keys) + 1)]

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            html_head(f, table_names)
            f.write('<body>\n')
            f.write('  <div class="app">\n')

            html_sidebar(f, [chapter_names[key] for key in chapter_keys])
            f.write('    <main>\n')
            f.write('      <style>.grand-total-heading { font-size: 24px; font-weight: bold; }</style>\n')
            f.write(f'      <h1 class="grand-total-heading">{get_counts_str(rules)}</h1>\n')

            for table_num, key in enumerate(chapter_keys, start=1):
                html_norm_rule_table(f, f"{NORM_RULES_CH_TABLE_NAME_PREFIX}{table_num}",
                                     chapter_names[key], rules_by_chapter[key], tag_fname2url)

            f.write('    </main>\n')
            f.write('  </div>\n')

            html_script(f)

            f.write('</body>\n')
            f.write('</html>\n')
    except Exception as e:
        fatal(f"Error writing HTML to {filename}: {e}")


def html_head(f, table_names: List[str]):
    """Write HTML head section."""
    if not isinstance(table_names, list):
        fatal(f"Need List for table_names but passed a {type(table_names).__name__}")

    css = '''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Normative Rules per Chapter</title>
  <style>
    .underline {
      text-decoration: underline;
    }
    :root{
      --sidebar-width: 200px;
      --accent: #0366d6;
      --muted: #6b7280;
      --bg: #f8fafc;
      --card: #ffffff;
    }
    html{scroll-behavior:smooth}
    body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;margin:0;background:var(--bg);color:#111}

    /* Layout */
    .app{
      display:grid;
      grid-template-columns:var(--sidebar-width) 1fr;
      min-height:100vh;
    }

    /* Sidebar */
    .sidebar{
      position:sticky;top:0;height:100vh;padding:24px;background:linear-gradient(180deg,#ffffff, #f1f5f9);
      border-right:1px solid rgba(15,23,42,0.04);
      box-sizing:border-box;
      overflow-y:auto;
      scrollbar-width:auto; /* show only when needed in Firefox */
    }
    .sidebar::-webkit-scrollbar{
      width:8px;
    }
    .sidebar::-webkit-scrollbar-thumb{
      background:rgba(0,0,0,0.2);
      border-radius:4px;
    }
    .sidebar::-webkit-scrollbar-thumb:hover{
      background:rgba(0,0,0,0.3);
    }
    .sidebar ul {
      list-style: none;
      padding: 0;
      margin: 0;
    }
    .sidebar li {
      margin: 2px 0; /* reduce vertical gap between items */
    }
    .sidebar::-webkit-scrollbar-track{
      background:transparent;
    }
    .sidebar h2{margin:0 0 2px;font-size:18px}
    .nav{display:flex;flex-direction:column;gap:2px}
    .nav a{
      display:block;
      font-size: 14px;
      padding:2px 10px;
      border-radius:6px;
      text-decoration:none;
      color:var(--accent);
      font-weight:600;
    }
    .nav a .subtitle{display:block;font-weight:400;color:var(--muted);font-size:12px}
    .nav a.active{background:rgba(3,102,214,0.12);color:var(--accent)}

    /* Content */
    main{padding:28px 36px}
    .section{background:var(--card);border-radius:12px;padding:20px;margin-bottom:22px;box-shadow:0 1px 0 rgba(15,23,42,0.03)}
    .section h3{margin-top:0}

    /* Default table formatting for nested tables from adoc */
    table {
      border-collapse:collapse;
      margin-top:12px;
      table-layout: auto;
    }

    th,td {
      padding:10px 12px;
      border:1px solid #e6edf3;
      text-align:left;
      overflow-wrap: break-word;
      white-space: normal;
    }

    th {
      background:#f3f7fb;
      font-weight:700
    }

    /* Sticky caption */
    table caption.sticky-caption {
      position: sticky;
      top: 0;
      z-index: 20;
      background: #ffffff;
      padding: 8px 12px;
      font-weight: bold;
      text-align: left;
      border-bottom: 1px solid #e6edf3;
      white-space: nowrap;
    }

    /* Sticky table header BELOW caption */
    table thead th {
      position: sticky;
      top: 38px;     /* height of caption (adjust if needed) */
      z-index: 10;
      background: #f3f7fb;
    }

    .col-name { width: 20%; }
    .col-description { width: 60%; }
    .col-location { width: 20%; }

    /* Chapter tables use all available width and divvied up using the percentages above */
'''

    f.write(css)

    for table_name in table_names:
        f.write(f"    #{table_name} > table {{ table-layout: fixed; width: 100% }}\n")

    f.write('''
    /* Responsive */
    @media (max-width:820px){
      .app{grid-template-columns:1fr}
      .sidebar{position:relative;height:auto;display:flex;gap:8px;overflow:auto;border-right:none;border-bottom:1px solid rgba(15,23,42,0.04)}
      main{padding:18px}
    }
  </style>
</head>
''')



def html_sidebar(f, chapter_names: List[str]):
    """Write HTML sidebar section."""
    if not isinstance(chapter_names, list):
        fatal(f"Need List for chapter_names but passed a {type(chapter_names).__name__}")

    f.write('\n')
    f.write('  <aside class="sidebar">\n')
    f.write('    <h2>All Normative Rules</h2>\n')
    f.write('    <nav class="nav" id="nav-chapters">\n')

    for table_num, chapter_name in enumerate(chapter_names, start=1):
        f.write(f'      <a href="#{NORM_RULES_CH_TABLE_NAME_PREFIX}{table_num}" data-target="{NORM_RULES_CH_TABLE_NAME_PREFIX}{table_num}">{chapter_name}</a>\n')

    f.write('    </nav>\n')
    f.write('  </aside>\n')


def html_norm_rule_table(f, table_name: str, chapter_name: str,
                         rules: List[NormativeRule], tag_fname2url: Dict[str, str]):
    """Write HTML table for normative rules."""
    if not isinstance(table_name, str):
        fatal(f"Need String for table_name but passed a {type(table_name).__name__}")
    if not isinstance(chapter_name, str):
        fatal(f"Need String for chapter_name but passed a {type(chapter_name).__name__}")
    if not isinstance(rules, list):
        fatal(f"Need List for rules but passed a {type(rules).__name__}")
    if not isinstance(tag_fname2url, dict):
        fatal(f"Need Dict for tag_fname2url but passed a {type(tag_fname2url).__name__}")

    html_table_header(f, table_name, f"Chapter {chapter_name}: {get_counts_str(rules)}")
    for nr in rules:
        html_norm_rule_table_row(f, nr, tag_fname2url)
    html_table_footer(f)


def html_table_header(f, table_name: str, table_caption: str):
    """Write HTML table header."""
    if not isinstance(table_name, str):
        fatal(f"Need String for table_name but passed a {type(table_name).__name__}")
    if not isinstance(table_caption, str):
        fatal(f"Need String for table_caption but passed a {type(table_caption).__name__}")

    f.write('\n')
    f.write(f'      <section id="{table_name}" class="section">\n')
    f.write('        <table>\n')
    f.write(f'          <caption class="sticky-caption">{table_caption}</caption>\n')
    f.write('          <colgroup>\n')
    f.write('            <col class="col-name">\n')
    f.write('            <col class="col-description">\n')
    f.write('            <col class="col-location">\n')
    f.write('          </colgroup>\n')
    f.write('          <thead>\n')
    f.write('            <tr><th>Name</th><th>Text</th><th>Location</th></tr>\n')
    f.write('          </thead>\n')
    f.write('          <tbody>\n')


def html_norm_rule_table_row(f, nr: NormativeRule, tag_fname2url: Dict[str, str]):
    """Write HTML table row for normative rule."""
    if not isinstance(nr, NormativeRule):
        fatal(f"Need NormativeRule for nr but passed a {type(nr).__name__}")
    if not isinstance(tag_fname2url, dict):
        fatal(f"Need Dict for tag_fname2url but passed a {type(tag_fname2url).__name__}")

    target_html_fname = tag_fname2url.get(nr.tag_filename)
    if target_html_fname is None:
        fatal(f"No fname tag to HTML mapping (-tag2url cmd line arg) for tag fname {nr.tag_filename} for tag name {nr.tag_name}")

    tag_text = convert_tag_text_to_html(nr.text, target_html_fname)
    tag_link = tag2html_link(nr.tag_name, nr.tag_name, target_html_fname)

    f.write('            <tr>\n')
    f.write(f'              <td id="{nr.name}">{nr.name}</td>\n')
    f.write(f'              <td>{tag_text}</td>\n')
    f.write(f'              <td>{tag_link}</td>\n')
    f.write('            </tr>\n')


def html_table_footer(f):
    """Write HTML table footer."""
    f.write('          </tbody>\n')
    f.write('        </table>\n')
    f.write('      </section>\n')


def html_script(f):
    """Write HTML script section."""
    script = '''  <script>
    // Highlight active link as the user scrolls
    const sections = document.querySelectorAll('section[id]');
    const navLinks = document.querySelectorAll('.nav a');

    const io = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        const id = entry.target.id;
        const link = document.querySelector('.nav a[data-target="'+id+'"]');
        if(entry.isIntersecting){
          navLinks.forEach(a=>a.classList.remove('active'));
          if(link) link.classList.add('active');
        }
      });
    }, {root:null,rootMargin:'-40% 0px -40% 0px',threshold:0});

    sections.forEach(s=>io.observe(s));

    // Smooth scroll for older browsers fallback
    document.querySelectorAll('.nav a').forEach(a=>{
      a.addEventListener('click', (e)=>{
        // close mobile nav or similar — none here, but keep behavior predictable
      });
    });
  </script>
</body>
</html>
'''
    f.write(script)



def get_counts_str(rules: List[NormativeRule]) -> str:
    """Get string describing the number of normative rules."""
    if not isinstance(rules, list):
        fatal(f"Need List for rules but passed a {type(rules).__name__}")

    num_rules = len(rules)
    return f"{num_rules} Normative Rule{'s' if num_rules != 1 else ''}"


def main():
    """Main function."""
    info(f"Passed command-line: {' '.join(sys.argv[1:])}")

    tag_fnames, tag_fname2url, output_fname, output_format = parse_argv()

    info(f"Normative tag filenames = {tag_fnames}")
    for tag_fname, url in tag_fname2url.items():
        info(f"Normative tag file {tag_fname} links to URL {url}")
    info(f"Output filename = {output_fname}")
    info(f"Output format = {output_format}")

    rules = load_rules(tag_fnames)

    info(f"Storing {len(rules)} normative rules into file {output_fname}")

    if output_format == "json":
        normative_rules_hash = create_normative_rules_hash(rules, tag_fname2url)
        output_json(output_fname, normative_rules_hash)
    elif output_format == "html":
        output_html(output_fname, rules, tag_fname2url)
    else:
        raise ValueError(f"Unknown output_format of {output_format}")

    sys.exit(0)


if __name__ == "__main__":
    main()

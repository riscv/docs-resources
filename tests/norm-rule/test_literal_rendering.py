#!/usr/bin/env python3
"""Exercise tagged verbatim and prose rendering through both pipeline stages."""

import json
import re
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).with_name("literal-rendering.adoc").resolve()


def rule_cell(rendered, rule):
    cell = re.search(rf'<td id="{rule}">{rule}</td>\s*<td>(.*?)</td>', rendered, re.DOTALL)
    assert cell is not None, f"Missing rule cell {rule}"
    return cell.group(1)


def main():
    with TemporaryDirectory() as directory:
        workdir = Path(directory)
        subprocess.run([
            "asciidoctor", "-r", str(REPO_ROOT / "converters/tags.rb"),
            "-b", "tags", "-a", "tags-match-prefix=norm:", "--failure-level=WARN",
            "-o", "tags.json", str(FIXTURE),
        ], cwd=workdir, check=True)
        generator = [
            sys.executable, str(REPO_ROOT / "tools/create_normative_rules.py"),
            "-t", "tags.json", "-tag2url", "tags.json", "spec.html",
        ]
        subprocess.run(generator + ["--html", "norm-rules.html"], cwd=workdir, check=True)
        subprocess.run(generator + ["-j", "norm-rules.json"], cwd=workdir, check=True)
        extracted = json.loads((workdir / "tags.json").read_text(encoding="utf-8"))
        rendered = (workdir / "norm-rules.html").read_text(encoding="utf-8")
        published = json.loads((workdir / "norm-rules.json").read_text(encoding="utf-8"))

    expected_code = (
        '<pre><code>result = (word &lt;&lt; 1) | (word &gt;&gt; 3);\n'
        '    if (left &lt; right &amp;&amp; right &gt; 0) print("&lt;b&gt;&amp;lt;&lt;/b&gt;");'
        '</code></pre>'
    )
    assert rule_cell(rendered, "shift-listing") == expected_code
    assert rule_cell(rendered, "shift-literal") == expected_code
    assert rule_cell(rendered, "shift-substituted") == (
        "<pre><code>result = (word &lt;&lt; 4) | (word &gt;&gt; 3);</code></pre>"
    )
    assert rule_cell(rendered, "shift-unescaped") == (
        '<pre><code>result = (word &lt;&lt; 1) | (word &gt;&gt; 3);\n'
        'print("&lt;b&gt;&amp;lt;&lt;/b&gt;");\n'
        "unexpanded: {code-comparison}, {code-entity}</code></pre>"
    )
    assert rule_cell(rendered, "attributes-only") == (
        "<pre><code>x = value &lt;&lt; 1;\n"
        "raw: &lt; &lt; &lt;b&gt;\n"
        "expanded: a &lt; b &amp; c &gt; d, &amp;lt;\n"
        "state: left &amp; right, 1</code></pre>"
    )
    assert rule_cell(rendered, "attributes-and-callouts") == (
        "<pre><code>state: left &amp; right, 2</code></pre>"
    )
    assert rule_cell(rendered, "specialcharacters-first") == (
        "<pre><code>raw: &amp;lt; &amp;#60; &lt;b&gt;\n"
        "expanded: a &lt; b &amp; c &gt; d, &amp;lt;</code></pre>"
    )
    assert rule_cell(rendered, "specialcharacters-last") == (
        "<pre><code>raw: &amp;lt; &amp;#60; &lt;b&gt;\n"
        "expanded: a &amp;lt; b &amp;amp; c &amp;gt; d, &amp;amp;lt;</code></pre>"
    )
    assert rule_cell(rendered, "prose-xref") == (
        'see <a href="spec.html#norm:shift-listing">listing rule</a> for the operation.'
    )
    assert extracted["tag_contexts"] == {
        "norm:shift-listing": {"context": "listing", "decode_entities": True},
        "norm:shift-literal": {"context": "literal", "decode_entities": True},
        "norm:shift-substituted": {"context": "listing", "decode_entities": True},
        "norm:shift-unescaped": {"context": "listing", "decode_entities": False},
        "norm:attributes-only": {"context": "listing", "decode_entities": True},
        "norm:attributes-and-callouts": {"context": "listing", "decode_entities": True},
        "norm:specialcharacters-first": {"context": "listing", "decode_entities": True},
        "norm:specialcharacters-last": {"context": "listing", "decode_entities": True},
    }
    assert set(published) == {"normative_rules"}
    assert {
        f"norm:{rule['name']}": rule["text"] for rule in published["normative_rules"]
    } == extracted["tags"]
    for rule in published["normative_rules"]:
        assert set(rule) == {"name", "chapter_name", "text", "tag_filename", "stds_doc_url"}
    print("test_literal_rendering.py: all tests passed")


if __name__ == "__main__":
    main()

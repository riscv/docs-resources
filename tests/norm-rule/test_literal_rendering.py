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
        'print("&lt;b&gt;&lt;&lt;/b&gt;");\n'
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
    assert rule_cell(rendered, "replacements-only") == (
        "<pre><code>Copyright © and trademark ™.</code></pre>"
    )
    assert rule_cell(rendered, "macros-listing") == (
        'x = (a &#60;&#60; 1) | (b &#62;&#62; 2); see '
        '<a href="spec.html#norm:shift-listing">norm:shift-listing</a>'
    )
    assert rule_cell(rendered, "empty-listing") == "(No text available)"
    assert rule_cell(rendered, "prose-shift") == (
        "the result is (a &#60;&#60; 1) | (b &#62;&#62; 2) here."
    )
    assert rule_cell(rendered, "prose-xref") == (
        'see <a href="spec.html#norm:shift-listing">listing rule</a> for the operation.'
    )
    assert extracted["tag_contexts"] == {
        f"norm:{name}": {"context": context}
        for name, context in (
            ("shift-listing", "listing"),
            ("shift-literal", "literal"),
            ("shift-substituted", "listing"),
            ("shift-unescaped", "listing"),
            ("attributes-only", "listing"),
            ("attributes-and-callouts", "listing"),
            ("specialcharacters-first", "listing"),
            ("specialcharacters-last", "listing"),
            ("replacements-only", "listing"),
            ("empty-listing", "listing"),
        )
    }
    # The context only affects the HTML: the published rules keep the extracted text.
    assert "tag_contexts" not in published
    assert {
        f"norm:{rule['name']}": rule["text"] for rule in published["normative_rules"]
    } == extracted["tags"]
    assert not any("context" in rule for rule in published["normative_rules"])
    print("test_literal_rendering.py: all tests passed")


if __name__ == "__main__":
    main()

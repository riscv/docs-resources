import re
import sys
import subprocess
import tempfile
import os

def detect_diagram_type(content):
    if '[bytefield]' in content:
        return 'bytefield'
    elif '[wavedrom' in content:
        return 'wavedrom'
    else:
        return 'unknown'

def extract_content(edn_path):
    with open(edn_path, 'r', encoding='utf-8') as f:
        content = f.read()

    diagram_type = detect_diagram_type(content)

    # Check for manual a11y-desc comment
    a11y_desc_match = re.search(r'//\s*a11y-desc:\s*(.+)', content)
    a11y_desc = a11y_desc_match.group(1).strip() if a11y_desc_match else None

    # Try to extract title from section comment (e.g. //## 9.4 Atomic Memory Operations)
    comment_match = re.search(r'//#+\s*(.+)', content)
    if comment_match:
        comment_title = comment_match.group(1).strip()
    else:
        basename = os.path.splitext(os.path.basename(edn_path))[0]
        comment_title = basename.replace('-', ' ').replace('_', ' ').upper() + " instruction encoding"

    if diagram_type == 'wavedrom':
        match = re.search(r'\.\.\.\.(.+?)\.\.\.\.', content, re.DOTALL)
        if not match:
            raise ValueError(f"No wavedrom JSON found in {edn_path}")
        json_text = match.group(1).strip()
    else:
        json_text = None

    return diagram_type, json_text, comment_title, a11y_desc, content

def build_accessibility_text(diagram_type, json_text, comment_title=None, a11y_desc=None):
    # Get title
    if json_text:
        label_match = re.search(r'label\s*:\s*\{[^}]*right\s*:\s*[\'"]([^\'"]+)[\'"]', json_text)
        if label_match:
            title = f"{label_match.group(1)} instruction encoding"
        elif comment_title:
            title = comment_title
        else:
            title = "Instruction encoding"
    else:
        title = comment_title if comment_title else "Instruction encoding"

    # Get description
    if a11y_desc:
        desc = a11y_desc
    elif diagram_type == 'wavedrom' and json_text:
        fields = re.findall(r'\{bits\s*:\s*(\d+)\s*,\s*name\s*:\s*[\'"]([^\'"]+)[\'"]', json_text)
        desc_parts = [f"{bits} bit{'s' if int(bits) > 1 else ''}: {name}" for bits, name in fields]
        desc = "Fields from bit 0: " + ", ".join(desc_parts)
    else:
        desc = "No description available. Please add an // a11y-desc: comment to this file."

    return title, desc

def inject_accessibility(svg_text, title, desc):
    insertion = f'<title>{title}</title><desc>{desc}</desc>'
    return svg_text.replace('<svg ', f'<svg role="img" aria-label="{title}" ', 1)\
                   .replace('>', f'>{insertion}', 1)

def update_edn_alt_text(edn_path, content, title):
    # Replace [wavedrom, ,svg] with [wavedrom, TITLE, svg]
    updated = re.sub(
        r'\[wavedrom,\s*,\s*svg\]',
        f'[wavedrom, {title}, svg]',
        content
    )
    if updated != content:
        with open(edn_path, 'w', encoding='utf-8') as f:
            f.write(updated)
        print(f"Updated alt text in: {edn_path}")
    else:
        print(f"Alt text already set or pattern not found in: {edn_path}")

def process(edn_path, output_svg_path):
    diagram_type, json_text, comment_title, a11y_desc, content = extract_content(edn_path)

    if diagram_type == 'bytefield' and not a11y_desc:
        print(f"WARNING: {edn_path} is a bytefield diagram with no a11y-desc comment.")
        print("Please add: // a11y-desc: <description of this diagram>")

    title, desc = build_accessibility_text(diagram_type, json_text, comment_title, a11y_desc)

    # Update alt text in the edn file itself
    update_edn_alt_text(edn_path, content, title)

    if diagram_type == 'wavedrom' and json_text:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tmp:
            tmp.write(json_text)
            tmp_path = tmp.name
        try:
            result = subprocess.run(
                ['npx.cmd', 'wavedrom-cli', '-i', tmp_path, '-o', '-'],
                capture_output=True, text=True
            )
            svg = result.stdout
        finally:
            os.unlink(tmp_path)

        svg = inject_accessibility(svg, title, desc)

        with open(output_svg_path, 'w', encoding='utf-8') as f:
            f.write(svg)

        print(f"Done: {output_svg_path}")
        print(f"Title: {title}")
        print(f"Desc:  {desc}")
    else:
        print(f"Skipping SVG generation for {diagram_type} diagram — handled by build system.")

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python wavedrom_a11y.py <input.edn> <output.svg>")
        sys.exit(1)
    process(sys.argv[1], sys.argv[2])
    
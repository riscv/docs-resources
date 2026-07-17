import re
import sys
import subprocess
import tempfile
import os

def detect_diagram_type(content):
    if '[bytefield' in content:
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
        clean_name = basename.replace('-', ' ').replace('_', ' ')
        if diagram_type == 'bytefield':
            # strip a trailing "reg" (e.g. "misareg" -> "misa") since these are register layouts
            clean_name = re.sub(r'\s*reg$', '', clean_name, flags=re.IGNORECASE).strip()
            comment_title = f"{clean_name.upper()} register field layout"
        else:
            comment_title = clean_name.upper() + " instruction encoding"

    if diagram_type == 'wavedrom':
        match = re.search(r'\.\.\.\.(.+?)\.\.\.\.', content, re.DOTALL)
        if not match:
            raise ValueError(f"No wavedrom JSON found in {edn_path}")
        json_text = match.group(1).strip()
        bytefield_text = None
    elif diagram_type == 'bytefield':
        match = re.search(r'-{4,}(.+?)-{4,}', content, re.DOTALL)
        if not match:
            raise ValueError(f"No bytefield body found in {edn_path}")
        bytefield_text = match.group(1).strip()
        json_text = None
    else:
        json_text = None
        bytefield_text = None

    return diagram_type, json_text, bytefield_text, comment_title, a11y_desc, content

def build_accessibility_text(diagram_type, json_text, bytefield_text=None, comment_title=None, a11y_desc=None):
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
    elif diagram_type == 'bytefield' and bytefield_text:
        raw_labels = re.findall(r'draw-box\s+(?:\(text\s+)?"([^"]+)"', bytefield_text)
        seen = set()
        field_labels = []
        for label in raw_labels:
            if label in ('(WARL)', '(WPRI)', '(WLRL)', '(R)', '(RO)'):
                continue
            if re.fullmatch(r'-?\d+', label):
                continue
            if re.fullmatch(r'[A-Z]*XLEN[+-]?\d*', label):
                continue
            if label in seen:
                continue
            seen.add(label)
            field_labels.append(label)
        if field_labels:
            desc = "Fields: " + ", ".join(field_labels)
        else:
            desc = "No description available. Please add an // a11y-desc: comment to this file."
    else:
        desc = "No description available. Please add an // a11y-desc: comment to this file."

    return title, desc

def inject_accessibility(svg_text, title, desc):
    insertion = f'<title>{title}</title><desc>{desc}</desc>'
    return svg_text.replace('<svg ', f'<svg role="img" aria-label="{title}" ', 1)\
                   .replace('>', f'>{insertion}', 1)

def update_edn_alt_text(edn_path, content, title):
    # Escape any double quotes in the title so it doesn't break the attribute string
    safe_title = title.replace('"', '&quot;')

    updated = content

    # wavedrom: [wavedrom, ,svg]  =>  [wavedrom, ,svg, alt="TITLE"]
    updated, n = re.subn(
        r'\[wavedrom,\s*,\s*svg\]',
        f'[wavedrom, ,svg, alt="{safe_title}"]',
        updated
    )
    if n == 0:
        updated, n = re.subn(
            r'(\[wavedrom,\s*,\s*svg,\s*alt=")[^"]*(")',
            rf'\g<1>{safe_title}\g<2>',
            updated
        )

    # bytefield: [bytefield]  =>  [bytefield, ,svg, alt="TITLE"]
    updated, n2 = re.subn(
        r'\[bytefield\]',
        f'[bytefield, ,svg, alt="{safe_title}"]',
        updated
    )
    if n2 == 0:
        updated, n2 = re.subn(
            r'(\[bytefield,\s*,\s*svg,\s*alt=")[^"]*(")',
            rf'\g<1>{safe_title}\g<2>',
            updated
        )

    if updated != content:
        with open(edn_path, 'w', encoding='utf-8') as f:
            f.write(updated)
        print(f"Updated alt text in: {edn_path}")
    else:
        print(f"Alt text already set or pattern not found in: {edn_path}")

def process(edn_path, output_svg_path):
    diagram_type, json_text, bytefield_text, comment_title, a11y_desc, content = extract_content(edn_path)

    if diagram_type == 'bytefield' and not a11y_desc:
        print(f"NOTE: {edn_path} has no a11y-desc comment; using auto-generated field list instead.")

    title, desc = build_accessibility_text(diagram_type, json_text, bytefield_text, comment_title, a11y_desc)

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

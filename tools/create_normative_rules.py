#!/usr/bin/env python3
"""Create normative rules from tag and definition files."""

import json
import sys
import re
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

PN = "create_normative_rules.py"

# Global constants
LT_UNICODE_DECIMAL = 60  # "<" Unicode decimal value
GT_UNICODE_DECIMAL = 62  # ">" Unicode decimal value

LT_UNICODE_STR = f"&#{LT_UNICODE_DECIMAL};"  # "<" Unicode string
GT_UNICODE_STR = f"&#{GT_UNICODE_DECIMAL};"  # ">" Unicode string

NORM_PREFIX = "norm:"

MAX_TABLE_ROWS = 12  # Max rows of a table displayed in a cell.

# Names/prefixes for tables in HTML output.
NORM_RULES_CH_TABLE_NAME_PREFIX = "table-norm-rules-ch-"
IMPLDEFS_NO_CAT_TABLE_NAME_PREFIX = "table-impldefs-no-cat"
IMPLDEFS_CAT_TABLE_NAME_PREFIX = "table-impldefs-impl-cat-"
IMPLDEFS_CH_TABLE_NAME_PREFIX = "table-impldefs-ch-"

# Enums
KINDS = ["extension", "extension_dependency", "instruction", "csr", "csr_field"]
IMPLDEF_CATEGORIES = ["WARL", "WLRL"]

# Norm rule name checking
NORM_RULE_NAME_PATTERN = r"^[a-zA-Z][a-zA-Z0-9_-]+$"
IMPLDEF_NAME_PATTERN = r"^[A-Z][A-Z0-9_]+$"


###################################
# Classes for Normative Rule Tags #
###################################


class NormativeTag:
    """Holds all information for one tag."""

    def __init__(self, name: str, tag_filename: str, text: str):
        if not isinstance(name, str):
            fatal(f"Need String for name but passed a {type(name).__name__}")
        if not isinstance(tag_filename, str):
            fatal(f"Need String for tag_filename but passed a {type(tag_filename).__name__}")
        if not isinstance(text, str):
            fatal(f"Need String for text but passed a {type(text).__name__}")

        self.name = name
        self.tag_filename = tag_filename
        self.text = text


class NormativeTags:
    """Holds all the normative rule tags for a RISC-V standard."""

    def __init__(self):
        # Contains tag entries as a flat hash for the entire standard (across multiple tag files).
        # The hash key is the tag name and the hash value is a NormativeTag object
        # The tag names must be unique across the standard.
        self.tag_map: Dict[str, NormativeTag] = {}

    def add_tags(self, tag_filename: str, tags: Dict[str, str]):
        """Add tags for specified standards document.

        Args:
            tag_filename: Name of the tag file
            tags: Hash key is tag name (AKA anchor name) and value is tag text.
        """
        if not isinstance(tag_filename, str):
            fatal(f"Need String for tag_filename but was passed a {type(tag_filename).__name__}")
        if not isinstance(tags, dict):
            fatal(f"Need Dict for tags but was passed a {type(tags).__name__}")

        for name, text in tags.items():
            if not isinstance(name, str):
                fatal(f"Tag name {name} in file {tag_filename} is a {type(name).__name__} instead of a String")

            if not isinstance(text, str):
                fatal(f"Tag name {name} in file {tag_filename} is a {type(text).__name__} instead of a String\n"
                      f"{PN}:   If the AsciiDoc anchor for {name} is before an AsciiDoc 'Description List' term, "
                      f"move to after term on its own line.")

            if name in self.tag_map:
                fatal(f"Tag name {name} in file {tag_filename} already defined in file {self.tag_map[name].tag_filename}")

            self.tag_map[name] = NormativeTag(name, tag_filename, text)

    def get_tag(self, name: str) -> Optional[NormativeTag]:
        """Get normative tag object corresponding to tag name. Returns None if not found."""
        return self.tag_map.get(name)

    def get_tags(self) -> List[NormativeTag]:
        """Return all normative tags for the standard."""
        return list(self.tag_map.values())


##########################################
# Classes for Normative Rule Definitions #
##########################################


class TagRef:
    """Holds reference to one tag in a normative rule definition."""

    def __init__(self, name: str, context: bool = False):
        if not isinstance(name, str):
            fatal(f"Need String for name but was passed a {type(name).__name__}")
        if not isinstance(context, bool):
            fatal(f"Need Boolean for context but was passed a {type(context).__name__}")

        self.name = name
        self._context = context

    def is_context(self) -> bool:
        return self._context


class NormativeRuleDef:
    """Holds one normative rule definition."""

    def __init__(self, name: str, def_filename: str, chapter_name: str, data: Dict[str, Any]):
        if not isinstance(name, str):
            fatal(f"Need String for name but was passed a {type(name).__name__}")
        if not isinstance(def_filename, str):
            fatal(f"Need String for def_filename but was passed a {type(def_filename).__name__}")
        if not isinstance(chapter_name, str):
            fatal(f"Need String for chapter_name but was passed a {type(chapter_name).__name__}")
        if not isinstance(data, dict):
            fatal(f"Need Dict for data but was passed a {type(data).__name__}")

        self.name = name
        self.def_filename = def_filename
        self.chapter_name = chapter_name

        self.summary = data.get("summary")
        if self.summary is not None and not isinstance(self.summary, str):
            fatal(f"Provided {type(self.summary).__name__} class for summary in normative rule {name} but need a String")

        self.note = data.get("note")
        if self.note is not None and not isinstance(self.note, str):
            fatal(f"Provided {type(self.note).__name__} class for note in normative rule {name} but need a String")

        self.clarification_link = data.get("clarification-link")
        if self.clarification_link is not None and not isinstance(self.clarification_link, str):
            fatal(f"Provided {type(self.clarification_link).__name__} class for clarification_link in normative rule {name} but need a String")

        self.clarification_text = data.get("clarification-text")
        if self.clarification_text is not None and not isinstance(self.clarification_text, str):
            fatal(f"Provided {type(self.clarification_text).__name__} class for clarification_text in normative rule {name} but need a String")

        self.description = data.get("description")
        if self.description is not None and not isinstance(self.description, str):
            fatal(f"Provided {type(self.description).__name__} class for description in normative rule {name} but need a String")

        self.kind = data.get("kind")
        if self.kind is not None:
            if not isinstance(self.kind, str):
                fatal(f"Provided {type(self.kind).__name__} class for kind in normative rule {name} but need a String")
            check_kind(self.kind, self.name, None)

        self.impldef = data.get("impl-def-behavior", False)
        if not isinstance(self.impldef, bool):
            fatal(f"Provided {type(self.impldef).__name__} class for impl-def-behavior in normative rule {name} but need a Boolean")

        self.impldef_cat = data.get("impl-def-category")
        if self.impldef_cat is not None:
            if not isinstance(self.impldef_cat, str):
                fatal(f"Provided {type(self.impldef_cat).__name__} class for impldef_cat in normative rule {name} but need a String")
            check_impldef_cat(self.impldef_cat, self.name, None)

            if not self.impldef:
                fatal(f"Normative rule {name} has impl-def-category property but impl-def-behavior isn't true")

        self.instances: List[str] = []
        if "instance" in data and data["instance"] is not None:
            self.instances.append(data["instance"])
        if "instances" in data and data["instances"] is not None:
            self.instances.extend(data["instances"])

        if self.kind is None:
            # Not allowed to have instances without a kind.
            if self.instances:
                fatal(f"Normative rule {name} defines instances but no kind")
        else:
            if not isinstance(self.instances, list):
                fatal(f"Provided {type(self.instances).__name__} class for instances in normative rule {name} but need a List")

        self.tag_refs: List[TagRef] = []
        if "tag" in data and data["tag"] is not None:
            self.tag_refs.append(TagRef(data["tag"]))
        if "tags" in data and data["tags"] is not None:
            for tag_data in data["tags"]:
                if isinstance(tag_data, str):
                    self.tag_refs.append(TagRef(tag_data))
                elif isinstance(tag_data, dict):
                    tag_name = tag_data.get("name")
                    if tag_name is None:
                        fatal(f"Normative rule {name} tag reference {tag_data} missing name")

                    context = tag_data.get("context", False)
                    self.tag_refs.append(TagRef(tag_name, context))
                else:
                    fatal(f"Normative rule {name} has tag reference that's a {type(tag_data).__name__} instead of a String or Dict: {tag_data}")

        # Validate name (function of impldef).
        pattern = IMPLDEF_NAME_PATTERN if self.impldef else NORM_RULE_NAME_PATTERN
        if not re.match(pattern, self.name):
            fatal(f"Normative rule '{name}' doesn't match regex pattern '{pattern}'")


class NormativeRuleDefs:
    """Holds all the information for all normative rule definition files."""

    def __init__(self):
        self.norm_rule_defs: List[NormativeRuleDef] = []
        self._defs_by_name: Dict[str, NormativeRuleDef] = {}

    def add_file_contents(self, def_filename: str, chapter_name: str, array_data: List[Any]):
        if not isinstance(def_filename, str):
            fatal(f"Need String for def_filename but passed a {type(def_filename).__name__}")
        if not isinstance(chapter_name, str):
            fatal(f"Need String for chapter_name but passed a {type(chapter_name).__name__}")
        if not isinstance(array_data, list):
            fatal(f"Need List for array_data but passed a {type(array_data).__name__}")

        for data in array_data:
            if not isinstance(data, dict):
                fatal(f"File {def_filename} entry isn't a dict: {data}")

            if "name" in data and data["name"] is not None:
                # Add one definition object
                self._add_def(data["name"], def_filename, chapter_name, data)
            elif "names" in data and data["names"] is not None:
                # Add one definition object for each name in array
                names = data["names"]
                for name in names:
                    self._add_def(name, def_filename, chapter_name, data)
            else:
                fatal(f"File {def_filename} missing name/names in normative rule definition entry: {data}")

    def _add_def(self, name: str, def_filename: str, chapter_name: str, data: Dict[str, Any]):
        if not isinstance(name, str):
            fatal(f"Need String for name but passed a {type(name).__name__}")
        if not isinstance(def_filename, str):
            fatal(f"Need String for def_filename but passed a {type(def_filename).__name__}")
        if not isinstance(chapter_name, str):
            fatal(f"Need String for chapter_name but passed a {type(chapter_name).__name__}")
        if not isinstance(data, dict):
            fatal(f"Need Dict for data but passed a {type(data).__name__}")

        if name in self._defs_by_name:
            fatal(f"Normative rule definition {name} in file {def_filename} already defined in file {self._defs_by_name[name].def_filename}")

        # Create definition object and store reference to it in array (to maintain order) and defs_by_name (for convenient lookup by name).
        norm_rule_def = NormativeRuleDef(name, def_filename, chapter_name, data)
        self.norm_rule_defs.append(norm_rule_def)
        self._defs_by_name[name] = norm_rule_def


#############
# Functions #
#############


def check_kind(kind: str, nr_name: str, name: Optional[str]):
    """Create fatal if kind not recognized. The name is None if this is called in the normative rule definition."""
    if kind not in KINDS:
        tag_str = "" if name is None else f"tag {name} in "
        allowed_str = ",".join(KINDS)
        fatal(f"Don't recognize kind '{kind}' for {tag_str}normative rule {nr_name}\n{PN}: Allowed kinds are: {allowed_str}")


def check_impldef_cat(impldef_cat: str, nr_name: str, name: Optional[str]):
    """Create fatal if impldef_cat not recognized. The name is None if this is called in the normative rule definition."""
    if impldef_cat not in IMPLDEF_CATEGORIES:
        tag_str = "" if name is None else f"tag {name} in "
        allowed_str = ",".join(IMPLDEF_CATEGORIES)
        fatal(f"Don't recognize impl-def-category '{impldef_cat}' for {tag_str}normative rule {nr_name}\n{PN}: Allowed impl-def-categories are: {allowed_str}")


def fatal(msg: str):
    """Print error and exit."""
    error(msg)
    sys.exit(1)


def error(msg: str):
    """Print error message."""
    print(f"{PN}: ERROR: {msg}", file=sys.stderr)


def info(msg: str):
    """Print info message."""
    print(f"{PN}: {msg}")


def parse_argv() -> Tuple[List[str], List[str], Dict[str, str], str, str, bool]:
    """Parse command line arguments.

    Returns:
        Tuple of (def_fnames, tag_fnames, tag_fname2url, output_fname, output_format, warn_if_tags_no_rules)
    """
    parser = argparse.ArgumentParser(
        description='Creates list of normative rules and stores them in <output-filename> (JSON format).',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('-j', action='store_const', const='json', dest='output_format',
                        default='json', help='Set output format to JSON (default)')
    parser.add_argument('--html', action='store_const', const='html', dest='output_format',
                        help='Set output format to HTML')
    parser.add_argument('-w', action='store_true', dest='warn_if_tags_no_rules',
                        help='Warning instead of error if tags found without rules (Only use for debugging!)')
    parser.add_argument('-d', action='append', dest='def_fnames', metavar='fname',
                        help='Normative rule definition filename (YAML format)')
    parser.add_argument('-t', action='append', dest='tag_fnames', metavar='fname',
                        help='Normative tag filename (JSON format)')
    parser.add_argument('-tag2url', action='append', nargs=2, dest='tag2url_list',
                        metavar=('tag-fname', 'url'),
                        help='Maps from tag fname to corresponding URL to stds doc')
    parser.add_argument('output_fname', help='Output filename')

    args = parser.parse_args()

    # Validate required arguments
    if not args.def_fnames:
        info("Missing normative rule definition filename(s)")
        parser.print_help()
        sys.exit(1)

    if not args.tag_fnames:
        info("Missing normative tag filename(s)")
        parser.print_help()
        sys.exit(1)

    # Build tag_fname2url dictionary
    tag_fname2url = {}
    if args.tag2url_list:
        for tag_fname, url in args.tag2url_list:
            tag_fname2url[tag_fname] = url

    if (args.output_format in ['json', 'html']) and not tag_fname2url:
        info("Missing -tag2url command line options")
        parser.print_help()
        sys.exit(1)

    return (args.def_fnames, args.tag_fnames, tag_fname2url,
            args.output_fname, args.output_format, args.warn_if_tags_no_rules)


def load_tags(tag_fnames: List[str]) -> NormativeTags:
    """Load the contents of all normative rule tag files in JSON format.

    Returns:
        NormativeTags class with all the contents.
    """
    if not isinstance(tag_fnames, list):
        fatal(f"Need List[String] for tag_fnames but passed a {type(tag_fnames).__name__}")

    tags = NormativeTags()

    for tag_fname in tag_fnames:
        info(f"Loading tag file {tag_fname}")

        # Read in file to a String
        try:
            with open(tag_fname, 'r', encoding='utf-8') as f:
                file_contents = f.read()
        except FileNotFoundError as e:
            fatal(str(e))
        except Exception as e:
            fatal(f"Error reading {tag_fname}: {e}")

        # Convert String in JSON format to a Python dict.
        try:
            file_data = json.loads(file_contents)
        except json.JSONDecodeError as e:
            fatal(f"File {tag_fname} JSON parsing error: {e}")

        tags_data = file_data.get("tags")
        if tags_data is None:
            fatal(f"Missing 'tags' key in {tag_fname}")

        # Add tags from JSON file to Python class.
        tags.add_tags(tag_fname, tags_data)

    return tags


def load_definitions(def_fnames: List[str]) -> NormativeRuleDefs:
    """Load the contents of all normative rule definition files in YAML format.

    Returns:
        NormativeRuleDefs class with all the contents.
    """
    if not isinstance(def_fnames, list):
        fatal(f"Need List[String] for def_fnames but passed a {type(def_fnames).__name__}")

    try:
        import yaml
    except ImportError:
        fatal("PyYAML is required but not installed. Run: pip install PyYAML")

    defs = NormativeRuleDefs()

    for def_fname in def_fnames:
        info(f"Loading definition file {def_fname}")

        # Read in file to a String
        try:
            with open(def_fname, 'r', encoding='utf-8') as f:
                file_contents = f.read()
        except FileNotFoundError as e:
            fatal(str(e))
        except Exception as e:
            fatal(f"Error reading {def_fname}: {e}")

        # Convert String in YAML format to a Python dict.
        try:
            yaml_hash = yaml.safe_load(file_contents)
        except yaml.YAMLError as e:
            fatal(f"File {def_fname} YAML syntax error - {e}")

        chapter_name = yaml_hash.get("chapter_name")
        if chapter_name is None:
            fatal(f"Missing 'chapter_name' key in {def_fname}")

        array_data = yaml_hash.get("normative_rule_definitions")
        if array_data is None:
            fatal(f"Missing 'normative_rule_definitions' key in {def_fname}")
        if not isinstance(array_data, list):
            fatal(f"'normative_rule_definitions' isn't a list in {def_fname}")

        defs.add_file_contents(def_fname, chapter_name, array_data)

    return defs


def create_normative_rules_hash(defs: NormativeRuleDefs, tags: NormativeTags,
                                 tag_fname2url: Dict[str, str]) -> Dict[str, List[Dict[str, Any]]]:
    """Returns a Dict with just one entry called "normative_rules" that contains a List of Dicts of all normative rules.

    Dict is suitable for JSON/YAML serialization.
    """
    if not isinstance(defs, NormativeRuleDefs):
        fatal(f"Need NormativeRuleDefs for defs but was passed a {type(defs).__name__}")
    if not isinstance(tags, NormativeTags):
        fatal(f"Need NormativeTags for tags but was passed a {type(tags).__name__}")
    if not isinstance(tag_fname2url, dict):
        fatal(f"Need Dict for tag_fname2url but passed a {type(tag_fname2url).__name__}")

    info("Creating normative rules from definition files")

    ret = {"normative_rules": []}

    for d in defs.norm_rule_defs:
        # Create dict with mandatory definition file arguments.
        hash_entry = {
            "name": d.name,
            "def_filename": d.def_filename,
            "chapter_name": d.chapter_name
        }

        # Now add optional arguments.
        if d.kind is not None:
            hash_entry["kind"] = d.kind
        hash_entry["impl-def-behavior"] = d.impldef
        if d.instances:
            hash_entry["instances"] = d.instances
        if d.impldef_cat is not None:
            hash_entry["impl-def-category"] = d.impldef_cat
        if d.summary is not None:
            hash_entry["summary"] = d.summary
        if d.note is not None:
            hash_entry["note"] = d.note
        if d.clarification_text is not None:
            hash_entry["clarification-text"] = d.clarification_text
        if d.clarification_link is not None:
            hash_entry["clarification-link"] = d.clarification_link
        if d.description is not None:
            hash_entry["description"] = d.description

        # Always create tags array, even if empty
        hash_entry["tags"] = []

        # Add tag entries
        for tag_ref in d.tag_refs:
            # Lookup tag
            tag = tags.get_tag(tag_ref.name)
            if tag is None:
                fatal(f"Normative rule {d.name} defined in file {d.def_filename} references non-existent tag {tag_ref.name}")

            url = tag_fname2url.get(tag.tag_filename)
            if url is None:
                fatal(f"No fname tag to URL mapping (-tag2url cmd line arg) for tag fname {tag.tag_filename} for tag name {tag.name}")

            resolved_tag = {
                "name": tag.name,
                "context": tag_ref.is_context(),
                "text": tag.text,
                "tag_filename": tag.tag_filename,
                "stds_doc_url": url
            }

            hash_entry["tags"].append(resolved_tag)

        ret["normative_rules"].append(hash_entry)

    return ret


def validate_defs_and_tags(defs: NormativeRuleDefs, tags: NormativeTags, warn_if_tags_no_rules: bool):
    """Fatal error if any normative rule references a non-existent tag.

    Fatal error or warning (controlled by cmd line switch) if there are tags that no rule references.
    """
    if not isinstance(defs, NormativeRuleDefs):
        fatal(f"Need NormativeRuleDefs for defs but passed a {type(defs).__name__}")
    if not isinstance(tags, NormativeTags):
        fatal(f"Need NormativeTags for tags but was passed a {type(tags).__name__}")

    missing_tag_cnt = 0
    bad_norm_rule_name_cnt = 0
    unref_cnt = 0
    referenced_tags = {}  # Key is tag name and value is any non-None value

    # Go through each normative rule definition. Look for:
    #   - References to non-existent tags
    #   - Normative rule names starting with NORM_PREFIX (should only be for tags)
    for d in defs.norm_rule_defs:
        for tag_ref in d.tag_refs:
            # Lookup tag by its name
            tag = tags.get_tag(tag_ref.name)

            if tag is None:
                missing_tag_cnt += 1
                error(f"Normative rule {d.name} references non-existent tag {tag_ref.name} in file {d.def_filename}")
            else:
                referenced_tags[tag.name] = 1  # Any non-None value

        if d.name.startswith(NORM_PREFIX):
            bad_norm_rule_name_cnt += 1
            error(f"Normative rule {d.name} starts with \"{NORM_PREFIX}\" prefix. This prefix is only for tag names, not rule names.")

        if d.clarification_text is not None:
            if d.clarification_link is None:
                error(f"Normative rule {d.name} has clarification-text but no clarification-link")

        if d.clarification_link is not None:
            if not re.match(r'^https://(www\.)?github\.com/riscv/.+/issues/[0-9]+$', d.clarification_link):
                error(f"Normative rule {d.name} clarification-link of '{d.clarification_link}' doesn't look like a RISC-V GitHub issue link")

    # Look for any unreferenced tags.
    for tag in tags.get_tags():
        if tag.name not in referenced_tags:
            msg = f"Tag {tag.name} not referenced by any normative rule. Did you forget to define a normative rule?"
            if warn_if_tags_no_rules:
                info(msg)
            else:
                error(msg)
            unref_cnt += 1

    if missing_tag_cnt > 0:
        error(f"{missing_tag_cnt} reference{'s' if missing_tag_cnt != 1 else ''} to non-existing tags")

    if bad_norm_rule_name_cnt > 0:
        error(f"{bad_norm_rule_name_cnt} illegal normative rule name{'s' if bad_norm_rule_name_cnt != 1 else ''}")

    if unref_cnt > 0:
        msg = f"{unref_cnt} tag{'s' if unref_cnt != 1 else ''} have no normative rules referencing them"
        if warn_if_tags_no_rules:
            info(msg)
        else:
            error(msg)

    if (missing_tag_cnt > 0) or (bad_norm_rule_name_cnt > 0) or ((unref_cnt > 0) and not warn_if_tags_no_rules):
        fatal("Exiting due to errors")


class Adoc2HTML:
    """Convert AsciiDoc formatting to HTML."""

    @staticmethod
    def constrained_format_pattern(text: str, delimiter: str, recursive: bool,
                                   transform_func) -> str:
        """Apply constrained formatting pair transformation.

        Single delimiter, bounded by whitespace/punctuation
        Example: "That is *strong* stuff!" or "This is *strong*!"
        """
        escaped_delimiter = re.escape(delimiter)
        # (?:^|\s) - start of line or space before
        # \K would be used in perl - in Python we use a capture group
        # Single opening mark, text that doesn't start/end with space, single closing mark
        # Followed by punctuation, space, or end of line
        pattern = rf'(^|\s){escaped_delimiter}(\S(?:(?!\s).*?(?<!\s))?){escaped_delimiter}(?=[,;".?!\s]|$)'

        def replacer(match):
            prefix = match.group(1)
            content = match.group(2)
            if recursive:
                content = Adoc2HTML.convert_nested(content)
            return prefix + transform_func(content)

        return re.sub(pattern, replacer, text)

    @staticmethod
    def unconstrained_format_pattern(text: str, delimiter: str, recursive: bool,
                                    transform_func) -> str:
        """Apply unconstrained formatting pair transformation.

        Double delimiter, can be used anywhere
        Example: "Sara**h**" or "**man**ual"
        """
        escaped_delimiter = re.escape(delimiter)
        pattern = rf'{escaped_delimiter}{{2}}(.+?){escaped_delimiter}{{2}}'

        def replacer(match):
            content = match.group(1)
            if recursive:
                content = Adoc2HTML.convert_nested(content)
            return transform_func(content)

        return re.sub(pattern, replacer, text)

    @staticmethod
    def continuous_format_pattern(text: str, delimiter: str, transform_func) -> str:
        """Apply superscript/subscript formatting transformation.

        Single delimiter, can be used anywhere, but text must be continuous (no spaces)
        Example: "2^32^" or "X~i~"
        """
        escaped_delimiter = re.escape(delimiter)
        pattern = rf'{escaped_delimiter}(\S+?){escaped_delimiter}'

        def replacer(match):
            content = match.group(1)
            return transform_func(content)

        return re.sub(pattern, replacer, text)

    @staticmethod
    def convert_nested(text: str) -> str:
        """Convert formatting within already-captured content."""
        result = text
        # Process unconstrained first (double delimiters)
        result = Adoc2HTML.unconstrained_format_pattern(result, "*", True, lambda c: f"<b>{c}</b>")
        result = Adoc2HTML.unconstrained_format_pattern(result, "_", True, lambda c: f"<i>{c}</i>")
        result = Adoc2HTML.unconstrained_format_pattern(result, "`", True, lambda c: f"<code>{c}</code>")
        # Then process constrained (single delimiters)
        result = Adoc2HTML.constrained_format_pattern(result, "*", True, lambda c: f"<b>{c}</b>")
        result = Adoc2HTML.constrained_format_pattern(result, "_", True, lambda c: f"<i>{c}</i>")
        result = Adoc2HTML.constrained_format_pattern(result, "`", True, lambda c: f"<code>{c}</code>")
        return result

    @staticmethod
    def convert_unconstrained(text: str) -> str:
        """Convert unconstrained bold, italics, and monospace notation."""
        text = Adoc2HTML.unconstrained_format_pattern(text, "*", True, lambda c: f"<b>{c}</b>")
        text = Adoc2HTML.unconstrained_format_pattern(text, "_", True, lambda c: f"<i>{c}</i>")
        text = Adoc2HTML.unconstrained_format_pattern(text, "`", True, lambda c: f"<code>{c}</code>")
        return text

    @staticmethod
    def convert_constrained(text: str) -> str:
        """Convert constrained bold, italics, and monospace notation."""
        text = Adoc2HTML.constrained_format_pattern(text, "*", True, lambda c: f"<b>{c}</b>")
        text = Adoc2HTML.constrained_format_pattern(text, "_", True, lambda c: f"<i>{c}</i>")
        text = Adoc2HTML.constrained_format_pattern(text, "`", True, lambda c: f"<code>{c}</code>")
        return text

    @staticmethod
    def convert_superscript(text: str) -> str:
        """Convert superscript notation: 2^32^ -> 2<sup>32</sup>"""
        return Adoc2HTML.continuous_format_pattern(text, "^", lambda c: f"<sup>{c}</sup>")

    @staticmethod
    def convert_subscript(text: str) -> str:
        """Convert subscript notation: X~i~ -> X<sub>i</sub>"""
        return Adoc2HTML.continuous_format_pattern(text, "~", lambda c: f"<sub>{c}</sub>")

    @staticmethod
    def convert_underline(text: str) -> str:
        """Convert underline notation: [.underline]#text# -> <span class="underline">text</span>"""
        return re.sub(r'\[\.underline\]#([^#]+)#', r'<span class="underline">\1</span>', text)

    @staticmethod
    def convert_extra_amp(text: str) -> str:
        """Convert escaped ampersands back to normal entity format."""
        # Sometimes the tags backend converts "&foo;" to "&amp;foo;". Convert it to "&foo;".
        text = re.sub(r'&amp;(\w+);', r'&\1;', text)

        # Sometimes the tags backend converts "&#8800;" to "&amp;#8800;". Convert it to "&#8800;".
        text = re.sub(r'&amp;#(\d+);', r'&#\1;', text)

        # And now handle the hexadecimal variant.
        text = re.sub(r'&amp;#x([0-9a-fA-F]+);', r'&#x\1;', text)

        return text

    @staticmethod
    def convert_unicode_names(text: str) -> str:
        """Convert unicode character entity names to numeric codes."""
        entities = {
            'ge': 8805,    # ≥ greater than or equal
            'le': 8804,    # ≤ less than or equal
            'ne': 8800,    # ≠ not equal
            'equiv': 8801, # ≡ equivalent
            'lt': LT_UNICODE_DECIMAL,      # < less than
            'gt': GT_UNICODE_DECIMAL,      # > greater than
            'amp': 38,     # & ampersand
            'quot': 34,    # " quote
            'apos': 39,    # ' apostrophe
            'nbsp': 160,   # non-breaking space
            'times': 215,  # × multiplication
            'divide': 247, # ÷ division
            'plusmn': 177, # ± plus-minus
            'deg': 176,    # ° degree
            'micro': 181,  # µ micro
            'para': 182,   # ¶ paragraph
            'middot': 183, # · middle dot
            'raquo': 187,  # » right angle quote
            'laquo': 171,  # « left angle quote
            'frac12': 189, # ½ one half
            'frac14': 188, # ¼ one quarter
            'frac34': 190, # ¾ three quarters
        }

        def replacer(match):
            entity_name = match.group(1)
            if entity_name in entities:
                return f"&#{entities[entity_name]};"
            else:
                # Leave unknown entities as-is
                return f"&{entity_name};"

        return re.sub(r'&(\w+);', replacer, text)

    @staticmethod
    def convert(text: str) -> str:
        """Apply all format conversions (keeping numeric entities)."""
        result = text
        result = Adoc2HTML.convert_unconstrained(result)
        result = Adoc2HTML.convert_constrained(result)
        result = Adoc2HTML.convert_superscript(result)
        result = Adoc2HTML.convert_subscript(result)
        result = Adoc2HTML.convert_underline(result)
        result = Adoc2HTML.convert_extra_amp(result)
        result = Adoc2HTML.convert_unicode_names(result)
        return result


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


def output_html(filename: str, defs: NormativeRuleDefs, tags: NormativeTags,
                tag_fname2url: Dict[str, str]):
    """Store normative rules in HTML output file."""
    if not isinstance(filename, str):
        fatal(f"Need String for filename but passed a {type(filename).__name__}")
    if not isinstance(defs, NormativeRuleDefs):
        fatal(f"Need NormativeRuleDefs for defs but passed a {type(defs).__name__}")
    if not isinstance(tags, NormativeTags):
        fatal(f"Need NormativeTags for tags but passed a {type(tags).__name__}")
    if not isinstance(tag_fname2url, dict):
        fatal(f"Need Dict for tag_fname2url but passed a {type(tag_fname2url).__name__}")

    # Array of all chapter names
    chapter_names = []

    # Organize rules. Each dict key is chapter name. Each dict entry is a List[NormativeRuleDef].
    norm_rules_by_chapter_name = {}
    impldefs_by_chapter_name = {}

    # Are there any impldef normative rules?
    any_impldefs = False

    # Create list of all impldef normative rules that don't have a category.
    impldefs_no_cat = []

    # Organize rules by implementation-defined category.
    impldefs_by_cat = {cat: [] for cat in IMPLDEF_CATEGORIES}

    # Go through all normative rule definitions and put into appropriate data structures.
    for d in defs.norm_rule_defs:
        if d.chapter_name not in chapter_names:
            chapter_names.append(d.chapter_name)

        if d.chapter_name not in norm_rules_by_chapter_name:
            norm_rules_by_chapter_name[d.chapter_name] = []
        norm_rules_by_chapter_name[d.chapter_name].append(d)

        if d.impldef:
            any_impldefs = True

            if d.impldef_cat is None:
                impldefs_no_cat.append(d)
            else:
                impldefs_by_cat[d.impldef_cat].append(d)

            if d.chapter_name not in impldefs_by_chapter_name:
                impldefs_by_chapter_name[d.chapter_name] = []
            impldefs_by_chapter_name[d.chapter_name].append(d)

    # Sort alphabetically for consistent output.
    chapter_names.sort()
    impldefs_no_cat.sort(key=lambda p: p.name)
    for cat in IMPLDEF_CATEGORIES:
        impldefs_by_cat[cat].sort(key=lambda p: p.name)

    # Create list of all table names in order.
    table_names = []
    table_num = 1
    for _ in chapter_names:
        table_names.append(f"{NORM_RULES_CH_TABLE_NAME_PREFIX}{table_num}")
        table_num += 1

    if len(impldefs_no_cat) > 0:
        table_names.append(IMPLDEFS_NO_CAT_TABLE_NAME_PREFIX)

    for cat in IMPLDEF_CATEGORIES:
        if len(impldefs_by_cat[cat]) > 0:
            table_names.append(f"{IMPLDEFS_CAT_TABLE_NAME_PREFIX}{cat}")

    table_num = 1
    for chapter_name in chapter_names:
        if chapter_name in impldefs_by_chapter_name:
            table_names.append(f"{IMPLDEFS_CH_TABLE_NAME_PREFIX}{table_num}")
        table_num += 1

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            html_head(f, table_names)
            f.write('<body>\n')
            f.write('  <div class="app">\n')

            html_sidebar(f, chapter_names, defs.norm_rule_defs, any_impldefs,
                        impldefs_no_cat, impldefs_by_cat, impldefs_by_chapter_name)
            f.write('    <main>\n')
            f.write('      <style>.grand-total-heading { font-size: 24px; font-weight: bold; }</style>\n')

            counts_str = get_impldefs_counts_str(defs.norm_rule_defs)
            f.write(f'      <h1 class="grand-total-heading">{counts_str}</h1>\n')

            table_num = 1
            for chapter_name in chapter_names:
                nr_defs = norm_rules_by_chapter_name[chapter_name]
                html_norm_rule_table(f, f"{NORM_RULES_CH_TABLE_NAME_PREFIX}{table_num}",
                                   chapter_name, nr_defs, tags, tag_fname2url)
                table_num += 1

            if any_impldefs:
                if len(impldefs_no_cat) > 0:
                    html_impldef_table(f, IMPLDEFS_NO_CAT_TABLE_NAME_PREFIX,
                                     "No Category (A-Z)", impldefs_no_cat, tags, tag_fname2url)

                for cat in IMPLDEF_CATEGORIES:
                    nr_defs = impldefs_by_cat[cat]
                    if len(nr_defs) > 0:
                        html_impldef_cat_table(f, f"{IMPLDEFS_CAT_TABLE_NAME_PREFIX}{cat}",
                                             f"{cat} Category (A-Z)", nr_defs, tags, tag_fname2url)

                table_num = 1
                for chapter_name in chapter_names:
                    if chapter_name in impldefs_by_chapter_name:
                        nr_defs = impldefs_by_chapter_name[chapter_name]
                        html_impldef_table(f, f"{IMPLDEFS_CH_TABLE_NAME_PREFIX}{table_num}",
                                         f"Chapter {chapter_name}", nr_defs, tags, tag_fname2url)
                    table_num += 1

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


def html_sidebar(f, chapter_names: List[str], nrs: List[NormativeRuleDef],
                any_impldefs: bool, impldefs_no_cat: List[NormativeRuleDef],
                impldefs_by_cat: Dict[str, List[NormativeRuleDef]],
                impldefs_by_chapter_name: Dict[str, List[NormativeRuleDef]]):
    """Write HTML sidebar section."""
    if not isinstance(chapter_names, list):
        fatal(f"Need List for chapter_names but passed a {type(chapter_names).__name__}")
    if not isinstance(nrs, list):
        fatal(f"Need List[NormativeRuleDef] for nrs but passed a {type(nrs).__name__}")
    if not isinstance(any_impldefs, bool):
        fatal(f"Need Boolean for any_impldefs but passed a {type(any_impldefs).__name__}")
    if not isinstance(impldefs_no_cat, list):
        fatal(f"Need List[NormativeRuleDef] for impldefs_no_cat but passed a {type(impldefs_no_cat).__name__}")
    if not isinstance(impldefs_by_cat, dict):
        fatal(f"Need Dict for impldefs_by_cat but passed a {type(impldefs_by_cat).__name__}")
    if not isinstance(impldefs_by_chapter_name, dict):
        fatal(f"Need Dict for impldefs_by_chapter_name but passed a {type(impldefs_by_chapter_name).__name__}")

    f.write('\n')
    f.write('  <aside class="sidebar">\n')
    f.write('    <h2>All Normative Rules</h2>\n')
    f.write('    <nav class="nav" id="nav-chapters">\n')

    table_num = 1
    for chapter_name in chapter_names:
        f.write(f'      <a href="#{NORM_RULES_CH_TABLE_NAME_PREFIX}{table_num}" data-target="{NORM_RULES_CH_TABLE_NAME_PREFIX}{table_num}">{chapter_name}</a>\n')
        table_num += 1

    if any_impldefs:
        f.write('    </nav>\n')
        f.write('    <h2>Implementation-Defined Behaviors</h2>\n')
        f.write('    <nav class="nav" id="nav-impldefs-no-cat">\n')

        if len(impldefs_no_cat) > 0:
            f.write(f'      <a href="#{IMPLDEFS_NO_CAT_TABLE_NAME_PREFIX}" data-target="{IMPLDEFS_NO_CAT_TABLE_NAME_PREFIX}">No category</a>\n')

        for cat in IMPLDEF_CATEGORIES:
            count = len(impldefs_by_cat.get(cat, []))
            if count > 0:
                f.write(f'      <a href="#{IMPLDEFS_CAT_TABLE_NAME_PREFIX}{cat}" data-target="{IMPLDEFS_CAT_TABLE_NAME_PREFIX}{cat}">{cat} category</a>\n')

        table_num = 1
        for chapter_name in chapter_names:
            if chapter_name in impldefs_by_chapter_name:
                f.write(f'      <a href="#{IMPLDEFS_CH_TABLE_NAME_PREFIX}{table_num}" data-target="{IMPLDEFS_CH_TABLE_NAME_PREFIX}{table_num}">{chapter_name}</a>\n')
            table_num += 1

        f.write('    </nav>\n')

    f.write('  </aside>\n')


def html_norm_rule_table(f, table_name: str, chapter_name: str,
                        nr_defs: List[NormativeRuleDef], tags: NormativeTags,
                        tag_fname2url: Dict[str, str]):
    """Write HTML table for normative rules."""
    if not isinstance(table_name, str):
        fatal(f"Need String for table_name but passed a {type(table_name).__name__}")
    if not isinstance(chapter_name, str):
        fatal(f"Need String for chapter_name but passed a {type(chapter_name).__name__}")
    if not isinstance(nr_defs, list):
        fatal(f"Need List for nr_defs but passed a {type(nr_defs).__name__}")
    if not isinstance(tags, NormativeTags):
        fatal(f"Need NormativeTags for tags but passed a {type(tags).__name__}")
    if not isinstance(tag_fname2url, dict):
        fatal(f"Need Dict for tag_fname2url but passed a {type(tag_fname2url).__name__}")

    counts_str = get_impldefs_counts_str(nr_defs)

    html_table_header(f, table_name, f"Chapter {chapter_name}: {counts_str}")
    for nr in nr_defs:
        html_norm_rule_table_row(f, nr, tags, tag_fname2url)
    html_table_footer(f)


def html_impldef_table(f, table_name: str, caption_prefix: str,
                      nr_defs: List[NormativeRuleDef], tags: NormativeTags,
                      tag_fname2url: Dict[str, str]):
    """Write HTML table for implementation-defined behaviors."""
    if not isinstance(table_name, str):
        fatal(f"Need String for table_name but passed a {type(table_name).__name__}")
    if not isinstance(caption_prefix, str):
        fatal(f"Need String for caption_prefix but passed a {type(caption_prefix).__name__}")
    if not isinstance(nr_defs, list):
        fatal(f"Need List for nr_defs but passed a {type(nr_defs).__name__}")
    if not isinstance(tags, NormativeTags):
        fatal(f"Need NormativeTags for tags but passed a {type(tags).__name__}")
    if not isinstance(tag_fname2url, dict):
        fatal(f"Need Dict for tag_fname2url but passed a {type(tag_fname2url).__name__}")

    html_table_header(f, table_name, f"{caption_prefix}: All {len(nr_defs)} Implementation-Defined Behaviors")
    for nr in nr_defs:
        html_impldef_table_row(f, nr, tags, tag_fname2url)
    html_table_footer(f)


def html_impldef_cat_table(f, table_name: str, caption_prefix: str,
                           nr_defs: List[NormativeRuleDef], tags: NormativeTags,
                           tag_fname2url: Dict[str, str]):
    """Write HTML table for implementation-defined behaviors by category."""
    if not isinstance(table_name, str):
        fatal(f"Need String for table_name but passed a {type(table_name).__name__}")
    if not isinstance(caption_prefix, str):
        fatal(f"Need String for caption_prefix but passed a {type(caption_prefix).__name__}")
    if not isinstance(nr_defs, list):
        fatal(f"Need List for nr_defs but passed a {type(nr_defs).__name__}")
    if not isinstance(tags, NormativeTags):
        fatal(f"Need NormativeTags for tags but passed a {type(tags).__name__}")
    if not isinstance(tag_fname2url, dict):
        fatal(f"Need Dict for tag_fname2url but passed a {type(tag_fname2url).__name__}")

    html_table_header(f, table_name, f"{caption_prefix}: All {len(nr_defs)} Implementation-Defined Behaviors")
    for nr in nr_defs:
        html_impldef_cat_table_row(f, nr, tags, tag_fname2url)
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
    f.write('            <tr><th>Rule Name</th><th>Rule Description</th><th>Origin of Description</th></tr>\n')
    f.write('          </thead>\n')
    f.write('          <tbody>\n')


def html_norm_rule_table_row(f, nr: NormativeRuleDef, tags: NormativeTags,
                             tag_fname2url: Dict[str, str]):
    """Write HTML table row for normative rule."""
    if not isinstance(nr, NormativeRuleDef):
        fatal(f"Need NormativeRuleDef for nr but passed a {type(nr).__name__}")
    if not isinstance(tags, NormativeTags):
        fatal(f"Need NormativeTags for tags but passed a {type(tags).__name__}")
    if not isinstance(tag_fname2url, dict):
        fatal(f"Need Dict for tag_fname2url but passed a {type(tag_fname2url).__name__}")

    name_is_anchor = True  # Rule name is an anchor link in chapter tables
    omit = {}  # Don't omit anything

    html_table_row(f, nr, name_is_anchor, omit, tags, tag_fname2url)


def html_impldef_table_row(f, nr: NormativeRuleDef, tags: NormativeTags,
                           tag_fname2url: Dict[str, str]):
    """Write HTML table row for implementation-defined behavior."""
    if not isinstance(nr, NormativeRuleDef):
        fatal(f"Need NormativeRuleDef for nr but passed a {type(nr).__name__}")
    if not isinstance(tags, NormativeTags):
        fatal(f"Need NormativeTags for tags but passed a {type(tags).__name__}")
    if not isinstance(tag_fname2url, dict):
        fatal(f"Need Dict for tag_fname2url but passed a {type(tag_fname2url).__name__}")

    name_is_anchor = False
    omit = {"impldef": True}  # Redundant

    html_table_row(f, nr, name_is_anchor, omit, tags, tag_fname2url)


def html_impldef_cat_table_row(f, nr: NormativeRuleDef, tags: NormativeTags,
                               tag_fname2url: Dict[str, str]):
    """Write HTML table row for implementation-defined behavior by category."""
    if not isinstance(nr, NormativeRuleDef):
        fatal(f"Need NormativeRuleDef for nr but passed a {type(nr).__name__}")
    if not isinstance(tags, NormativeTags):
        fatal(f"Need NormativeTags for tags but passed a {type(tags).__name__}")
    if not isinstance(tag_fname2url, dict):
        fatal(f"Need Dict for tag_fname2url but passed a {type(tag_fname2url).__name__}")

    name_is_anchor = False
    omit = {
        "impldef": True,      # Redundant
        "impldef_cat": True   # Redundant
    }

    html_table_row(f, nr, name_is_anchor, omit, tags, tag_fname2url)


def html_table_row(f, nr: NormativeRuleDef, name_is_anchor: bool, omit: Dict[str, bool],
                  tags: NormativeTags, tag_fname2url: Dict[str, str]):
    """Write HTML table row."""
    if not isinstance(nr, NormativeRuleDef):
        fatal(f"Need NormativeRuleDef for nr but passed a {type(nr).__name__}")
    if not isinstance(name_is_anchor, bool):
        fatal(f"Need Boolean for name_is_anchor but passed a {type(name_is_anchor).__name__}")
    if not isinstance(omit, dict):
        fatal(f"Need Dict for omit but passed a {type(omit).__name__}")
    if not isinstance(tags, NormativeTags):
        fatal(f"Need NormativeTags for tags but passed a {type(tags).__name__}")
    if not isinstance(tag_fname2url, dict):
        fatal(f"Need Dict for tag_fname2url but passed a {type(tag_fname2url).__name__}")

    omit_impldef = omit.get("impldef", False)
    omit_impldef_cat = omit.get("impldef_cat", False)

    name_row_span = (
        (0 if nr.summary is None else 1) +
        (0 if nr.note is None else 1) +
        (0 if nr.clarification_link is None else 1) +
        (0 if nr.description is None else 1) +
        (0 if nr.kind is None else 1) +
        (0 if not nr.instances else 1) +
        (0 if omit_impldef or not nr.impldef else 1) +
        (0 if omit_impldef_cat or nr.impldef_cat is None else 1) +
        len(nr.tag_refs)
    )

    # Tracks if this is the first row for the normative rule.
    first_row = True

    # Output the normative rule name cell with rowspan.
    f.write('            <tr>\n')
    if name_is_anchor:
        f.write(f'              <td rowspan={name_row_span} id="{nr.name}">{nr.name}</td>\n')
    else:
        f.write(f'              <td rowspan={name_row_span}><a href="#{nr.name}">{nr.name}</a></td>\n')

    if nr.summary is not None:
        text = convert_def_text_to_html(nr.summary)

        if not first_row:
            f.write('            <tr>\n')
        f.write(f'              <td>{text}</td>\n')
        f.write('              <td>Rule\'s "summary" property</td>\n')
        f.write('            </tr>\n')
        first_row = False

    if nr.note is not None:
        text = convert_def_text_to_html(nr.note)

        if not first_row:
            f.write('            <tr>\n')
        f.write(f'              <td>{text}</td>\n')
        f.write('              <td>Rule\'s "note" property</td>\n')
        f.write('            </tr>\n')
        first_row = False

    if nr.description is not None:
        text = convert_def_text_to_html(nr.description)

        if not first_row:
            f.write('            <tr>\n')
        f.write(f'              <td>{text}</td>\n')
        f.write('              <td>Rule\'s "description" property</td>\n')
        f.write('            </tr>\n')
        first_row = False

    if nr.kind is not None:
        if not first_row:
            f.write('            <tr>\n')
        f.write(f'              <td>{nr.kind}</td>\n')
        f.write('              <td>Rule\'s "kind" property</td>\n')
        f.write('            </tr>\n')
        first_row = False

    if nr.instances:
        if len(nr.instances) == 1:
            instances_str = nr.instances[0]
            rule_name = "instance"
        else:
            instances_str = "[" + ', '.join(nr.instances) + "]"
            rule_name = "instances"

        if not first_row:
            f.write('            <tr>\n')
        f.write(f'              <td>{instances_str}</td>\n')
        f.write(f'              <td>Rule\'s "{rule_name}" property</td>\n')
        f.write('            </tr>\n')
        first_row = False

    if not omit_impldef and nr.impldef:
        if not first_row:
            f.write('            <tr>\n')
        f.write('              <td>Implementation-defined behavior</td>\n')
        f.write('              <td>Rule\'s property</td>\n')
        f.write('            </tr>\n')
        first_row = False

    if not omit_impldef_cat and nr.impldef_cat is not None:
        if not first_row:
            f.write('            <tr>\n')
        f.write(f'              <td>{nr.impldef_cat}</td>\n')
        f.write('              <td>Implementation-defined behavior category</td>\n')
        f.write('            </tr>\n')
        first_row = False

    for tag_ref in nr.tag_refs:
        tag = tags.get_tag(tag_ref.name)
        if tag is None:
            fatal(f"Normative rule {nr.name} defined in file {nr.def_filename} references non-existent tag {tag_ref.name}")

        target_html_fname = tag_fname2url.get(tag.tag_filename)
        if target_html_fname is None:
            fatal(f"No fname tag to HTML mapping (-tag2url cmd line arg) for tag fname {tag.tag_filename} for tag name {tag.name}")

        tag_text = convert_newlines_to_html(convert_tags_tables_to_html(Adoc2HTML.convert(tag.text)))

        # Convert adoc links to HTML links.
        tag_text = convert_adoc_links_to_html(tag_text, target_html_fname)

        if tag_text.strip() == "":
            tag_text = "(No text available)"

        if tag_ref.is_context():
            tag_text = "[CONTEXT] " + tag_text

        tag_link = tag2html_link(tag_ref.name, tag_ref.name, target_html_fname)

        if not first_row:
            f.write('            <tr>\n')
        f.write(f'              <td>{tag_text}</td>\n')
        f.write(f'              <td>{tag_link}</td>\n')
        f.write('            </tr>\n')
        first_row = False

    if nr.clarification_link is not None:
        # The clarification text can only exist if the clarification link also exists.
        if nr.clarification_text is None:
            text = "(No clarification text available)"
        else:
            text = convert_def_text_to_html(nr.clarification_text)

        link = f'<a href="{nr.clarification_link}">GitHub Issue</a>'

        if not first_row:
            f.write('            <tr>\n')
        f.write(f'              <td>[CLARIFICATION] {text}</td>\n')
        f.write(f'              <td>{link}</td>\n')
        f.write('            </tr>\n')
        first_row = False


def html_table_footer(f):
    """Write HTML table footer."""
    f.write('          </tbody>\n')
    f.write('        </table>\n')
    f.write('      </section>\n')


def tag2html_link(tag_ref: str, link_text: str, target_html_fname: Optional[str] = None) -> str:
    """Create HTML link to tag. If no target_html_fname is provided, assumes anchor is in same HTML file as link."""
    if not isinstance(tag_ref, str):
        fatal(f"Expected String for tag_ref but was passed a {type(tag_ref).__name__}")
    if not isinstance(link_text, str):
        fatal(f"Expected String for link_text but was passed a {type(link_text).__name__}")
    if target_html_fname is not None and not isinstance(target_html_fname, str):
        fatal(f"Expected String for target_html_fname but was passed a {type(target_html_fname).__name__}")

    if target_html_fname is None:
        target_html_fname = ""

    return f'<a href="{target_html_fname}#{tag_ref}">{link_text}</a>'


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


def get_impldefs_counts_str(nr_defs: List[NormativeRuleDef]) -> str:
    """Get string describing implementation-defined counts."""
    if not isinstance(nr_defs, list):
        fatal(f"Need List for nr_defs but passed a {type(nr_defs).__name__}")

    num_rules = len(nr_defs)
    counts_str = f"{num_rules} Normative Rule{'s' if num_rules != 1 else ''}"

    num_impldefs = count_impldefs(nr_defs)
    if num_impldefs > 0:
        counts_str += f": Includes {num_impldefs} Implementation-Defined Behavior{'s' if num_impldefs != 1 else ''}"

        num_impldefs_no_cat = num_impldefs  # Start with total and subtract out categorized counts

        any_impldef_cats = False
        num_impldef_cats = {}
        for cat in IMPLDEF_CATEGORIES:
            num_impldef_cats[cat] = count_impldef_cats(nr_defs, cat)
            if num_impldef_cats[cat] > 0:
                any_impldef_cats = True
                num_impldefs_no_cat -= num_impldef_cats[cat]

        if any_impldef_cats:
            counts_str += " ("

            cats_str = [f"{num_impldefs_no_cat} No Category"]
            for cat in IMPLDEF_CATEGORIES:
                if num_impldef_cats[cat] > 0:
                    cats_str.append(f"{num_impldef_cats[cat]} {cat}")

            counts_str += ", ".join(cats_str)
            counts_str += ")"

    return counts_str


def count_impldefs(nrs: List[NormativeRuleDef]) -> int:
    """Count implementation-defined behaviors."""
    if not isinstance(nrs, list):
        raise TypeError(f"Need List[NormativeRuleDef] for nrs but passed a {type(nrs).__name__}")

    count = 0
    for nr in nrs:
        if nr.impldef:
            count += 1

    return count


def count_impldef_cats(nrs: List[NormativeRuleDef], impldef_cat: str) -> int:
    """Count implementation-defined behaviors by category."""
    if not isinstance(nrs, list):
        raise TypeError(f"Need List[NormativeRuleDef] for nrs but passed a {type(nrs).__name__}")
    if not isinstance(impldef_cat, str):
        raise TypeError(f"Need String for impldef_cat but passed a {type(impldef_cat).__name__}")

    count = 0
    for nr in nrs:
        if nr.impldef_cat == impldef_cat:
            count += 1

    return count


def convert_def_text_to_html(text: str) -> str:
    """Convert all the various definition text formats to HTML."""
    if not isinstance(text, str):
        raise TypeError(f"Expected String for text but was passed a {type(text).__name__}")

    text = Adoc2HTML.convert(text)
    text = convert_tags_tables_to_html(text)
    text = convert_newlines_to_html(text)
    text= convert_adoc_links_to_html(text)

    return text


def convert_tags_tables_to_html(text: str) -> str:
    """Convert the tagged text containing entire tables. Uses format created by "tags" Asciidoctor backend."""
    if not isinstance(text, str):
        raise TypeError(f"Expected String for text but was passed a {type(text).__name__}")

    def replacer(match):
        # Found a "tags" formatted table
        heading = match.group(1).rstrip('\n')
        rows_text = match.group(2)
        rows = rows_text.split("¶")  # Split into list of rows

        ret = "<table>"  # Start html table

        # Add heading if present
        heading_cells = extract_tags_table_cells(heading)
        if heading_cells:
            ret += "<thead>"
            ret += "<tr>"
            ret += "".join(f"<th>{cell}</th>" for cell in heading_cells)
            ret += "</tr>"
            ret += "</thead>"

        # Add each row
        ret += "<tbody>"
        for index, row in enumerate(rows):
            if index < MAX_TABLE_ROWS:
                ret += "<tr>"
                row_cells = extract_tags_table_cells(row)
                ret += "".join(f"<td>{cell}</td>" for cell in row_cells)
                ret += "</tr>"
            elif index == MAX_TABLE_ROWS:
                ret += "<tr>"
                row_cells = extract_tags_table_cells(row)
                ret += "".join("<td>...</td>" for _ in row_cells)
                ret += "</tr>"

        ret += "</tbody>"
        ret += "</table>"  # End html table

        return ret

    pattern = r'(.*?)===\n(.+)\n==='
    return re.sub(pattern, replacer, text, flags=re.DOTALL)


def extract_tags_table_cells(row: str) -> List[str]:
    """Return list of table columns from one row/header of a table.

    Returns empty list if row is None or the empty string.
    """
    if not isinstance(row, str):
        raise TypeError(f"Expected String for row but was passed a {type(row).__name__}")

    if not row:
        return []

    # Split row fields with pipe symbol. The -1 passed to split ensures trailing null fields are not suppressed.
    return [cell.strip() for cell in row.split('|')]


def convert_newlines_to_html(text: str) -> str:
    """Convert newlines to <br>."""
    if not isinstance(text, str):
        raise TypeError(f"Expected String for text but was passed a {type(text).__name__}")

    return text.replace('\n', '<br>')


def convert_adoc_links_to_html(text: str, target_html_fname: Optional[str] = None) -> str:
    """Convert adoc links to HTML links.

    Supported adoc link formats:
        <<link>>
        <<link,custom text>>

    If target_html_fname is not provided, link will assume anchor is in the same HTML file as the link.
    """
    if not isinstance(text, str):
        raise TypeError(f"Passed class {type(text).__name__} for text but require String")
    if target_html_fname is not None and not isinstance(target_html_fname, str):
        raise TypeError(f"Passed class {type(target_html_fname).__name__} for target_html_fname but require String")

    def replacer(match):
        link_content = match.group(2)

        # Look to see if custom text has been provided.
        split_texts = [t.strip() for t in link_content.split(",")]

        if len(split_texts) == 0:
            raise ValueError(f"Hyperlink '{link_content}' is empty")
        elif len(split_texts) == 1:
            return tag2html_link(split_texts[0], split_texts[0], target_html_fname)
        elif len(split_texts) == 2:
            return tag2html_link(split_texts[0], split_texts[1], target_html_fname)
        else:
            raise ValueError(f"Hyperlink '{link_content}' contains too many commas")

    # Note that I'm using the non-greedy regular expression (? after +) otherwise the regular expression
    # will return multiple <<link>> in the same text as one.
    pattern = rf'(<<|{re.escape(LT_UNICODE_STR)}{re.escape(LT_UNICODE_STR)})(.+?)(>>|{re.escape(GT_UNICODE_STR)}{re.escape(GT_UNICODE_STR)})'
    return re.sub(pattern, replacer, text)


def main():
    """Main function."""
    info(f"Passed command-line: {' '.join(sys.argv[1:])}")

    def_fnames, tag_fnames, tag_fname2url, output_fname, output_format, warn_if_tags_no_rules = parse_argv()

    info(f"Normative rule definition filenames = {def_fnames}")
    info(f"Normative tag filenames = {tag_fnames}")
    for tag_fname, url in tag_fname2url.items():
        info(f"Normative tag file {tag_fname} links to URL {url}")
    info(f"Output filename = {output_fname}")
    info(f"Output format = {output_format}")

    defs = load_definitions(def_fnames)
    tags = load_tags(tag_fnames)
    validate_defs_and_tags(defs, tags, warn_if_tags_no_rules)

    info(f"Storing {len(defs.norm_rule_defs)} normative rules into file {output_fname}")
    info(f"Includes {count_impldefs(defs.norm_rule_defs)} implementation-defined behavior normative rules")
    for cat in IMPLDEF_CATEGORIES:
        count = count_impldef_cats(defs.norm_rule_defs, cat)
        info(f"Includes {count} {cat} normative rule{'s' if count != 1 else ''}")

    if output_format == "json":
        normative_rules_hash = create_normative_rules_hash(defs, tags, tag_fname2url)
        output_json(output_fname, normative_rules_hash)
    elif output_format == "html":
        output_html(output_fname, defs, tags, tag_fname2url)
    else:
        raise ValueError(f"Unknown output_format of {output_format}")

    sys.exit(0)


if __name__ == "__main__":
    main()

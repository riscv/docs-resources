#!/usr/bin/env python3
"""Script to detect changes in normative tags extracted from asciidoc files.

Compares two tag JSON files and reports additions, deletions, and modifications.
"""

import json
import sys
import argparse
import re
from pathlib import Path
from typing import Dict, Set, Any


class TagChanges:
    """Container for tag change information."""

    def __init__(self):
        self.added: Dict[str, str] = {}      # Tags present in current but not in reference
        self.deleted: Dict[str, str] = {}    # Tags present in reference but not in current
        self.modified: Dict[str, Dict[str, str]] = {}   # Tags present in both but with different text

    def any_changes(self) -> bool:
        """Check if any changes were detected."""
        return bool(self.added or self.deleted or self.modified)

    def total_changes(self) -> int:
        """Get total number of changes."""
        return len(self.added) + len(self.deleted) + len(self.modified)


class TagChangeDetector:
    """Detector for changes in tag files."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def load_tags(self, filename: str) -> Dict[str, str]:
        """Load tags from a JSON file.

        Args:
            filename: Path to the JSON file

        Returns:
            Dict of tag names to tag text
        """
        file_path = Path(filename)
        if not file_path.exists():
            sys.exit(f"Error: File not found: {filename}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            tags = data.get("tags", {})
            return tags
        except json.JSONDecodeError as e:
            sys.exit(f"Error: Failed to parse JSON from {filename}: {e}")
        except Exception as e:
            sys.exit(f"Error: Failed to read {filename}: {e}")

    def detect_changes(self, reference_tags: Dict[str, str],
                      current_tags: Dict[str, str]) -> TagChanges:
        """Compare two tag sets and identify changes.

        Args:
            reference_tags: Original tags
            current_tags: Updated tags

        Returns:
            TagChanges object containing all changes
        """
        changes = TagChanges()

        reference_keys: Set[str] = set(reference_tags.keys())
        current_keys: Set[str] = set(current_tags.keys())

        # Find added tags (in current but not in reference)
        added_keys = current_keys - reference_keys
        for tag_name in added_keys:
            changes.added[tag_name] = current_tags[tag_name]

        # Find deleted tags (in reference but not in current)
        deleted_keys = reference_keys - current_keys
        for tag_name in deleted_keys:
            changes.deleted[tag_name] = reference_tags[tag_name]

        # Find modified tags (in both but different text)
        common_keys = reference_keys & current_keys
        for tag_name in common_keys:
            reference_text = reference_tags[tag_name]
            current_text = current_tags[tag_name]

            # Compare normalized text (ignoring whitespace and AsciiDoc formatting differences)
            normalized_ref = self._normalize_text(reference_text)
            normalized_cur = self._normalize_text(current_text)

            if normalized_ref != normalized_cur:
                changes.modified[tag_name] = {
                    "reference": reference_text,
                    "current": current_text
                }

        return changes

    def display_changes(self, changes: TagChanges, reference_file: str,
                       current_file: str, verbose: bool):
        """Format and display changes.

        Args:
            changes: Changes to display
            reference_file: Name of reference file (for display)
            current_file: Name of current file (for display)
            verbose: Whether to show verbose output
        """
        if verbose:
            print("=" * 80)
            print("Tag Changes Report")
            print("=" * 80)
            print()

        print(f"Reference file: {reference_file}")
        print(f"Current file: {current_file}")

        if not changes.any_changes():
            print("No changes detected.")
            return

        # Display added tags
        if changes.added:
            count = len(changes.added)
            print(f"Added {count} tag{'s' if count > 1 else ''}:")
            for tag_name in sorted(changes.added.keys()):
                text = changes.added[tag_name]
                print(f'  * "{tag_name}": "{self._truncate_text(text)}"')
            print()

        # Display deleted tags
        if changes.deleted:
            count = len(changes.deleted)
            print(f"Deleted {count} tag{'s' if count > 1 else ''}:")
            for tag_name in sorted(changes.deleted.keys()):
                text = changes.deleted[tag_name]
                print(f'  * "{tag_name}": "{self._truncate_text(text)}"')
            print()

        # Display modified tags
        if changes.modified:
            count = len(changes.modified)
            print(f"Modified {count} tag{'s' if count > 1 else ''}:")
            for tag_name in sorted(changes.modified.keys()):
                texts = changes.modified[tag_name]
                print(f'  * "{tag_name}":')
                print(f'      Reference: "{self._truncate_text(texts["reference"])}"')
                print(f'      Current:   "{self._truncate_text(texts["current"])}"')
            print()

        # Summary
        if verbose:
            print("=" * 80)
            print(f"Summary: {changes.total_changes()} total changes")
            print(f"  Added:    {len(changes.added)}")
            print(f"  Deleted:  {len(changes.deleted)}")
            print(f"  Modified: {len(changes.modified)}")
            print("=" * 80)

    def update_tags_file(self, file_path: str, changes: TagChanges):
        """Update a tags file by adding new tags from additions.

        Args:
            file_path: Path to the file to update
            changes: Changes detected
        """
        if not changes.added:
            print(f"No additions to merge into {file_path}")
            if self.verbose:
                print("Skipping file update - no additions")
            return

        path = Path(file_path)
        if not path.exists():
            sys.exit(f"Error: Cannot update file - not found: {file_path}")

        if self.verbose:
            print(f"Updating reference file: {file_path}")

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            original_count = len(data["tags"])

            # Add new tags
            for tag_name, tag_text in changes.added.items():
                if self.verbose:
                    print(f"  Adding tag: {tag_name}")
                data["tags"][tag_name] = tag_text

            # Write back to file
            if self.verbose:
                print("Writing updated file...")

            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            new_count = len(data["tags"])
            print(f"Updated {file_path}: added {len(changes.added)} new tags ({original_count} -> {new_count} total tags)")

        except json.JSONDecodeError as e:
            sys.exit(f"Error: Failed to parse JSON from {file_path}: {e}")
        except Exception as e:
            sys.exit(f"Error: Failed to update {file_path}: {e}")

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison (whitespace and AsciiDoc formatting).

        Args:
            text: Text to normalize

        Returns:
            Normalized text
        """
        # First normalize whitespace, then strip AsciiDoc formatting
        return self._strip_asciidoc_formatting(self._normalize_whitespace(text))

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace for comparison.

        Args:
            text: Text to normalize

        Returns:
            Text with normalized whitespace
        """
        return re.sub(r'\s+', ' ', text.strip())

    def _strip_asciidoc_formatting(self, text: str) -> str:
        """Strip AsciiDoc formatting marks.

        Args:
            text: Text to strip formatting from

        Returns:
            Text without AsciiDoc formatting
        """
        result = text

        # Remove bold: **text** (unconstrained) or *text* (constrained)
        result = re.sub(r'\*\*([^\*]+?)\*\*', r'\1', result)
        result = re.sub(r'\*([^\*]+?)\*', r'\1', result)

        # Remove italic: __text__ (unconstrained) or _text_ (constrained, not in middle of words)
        result = re.sub(r'__([^_]+?)__', r'\1', result)
        result = re.sub(r'(?<!\w)_([^_]+?)_(?!\w)', r'\1', result)

        # Remove monospace: `text`
        result = re.sub(r'`([^`]+?)`', r'\1', result)

        # Remove superscript: ^text^
        result = re.sub(r'\^([^\^]+?)\^', r'\1', result)

        # Remove subscript: ~text~
        result = re.sub(r'~([^~]+?)~', r'\1', result)

        # Remove role-based formatting: [role]#text#
        result = re.sub(r'\[[^\]]+\]#([^#]+?)#', r'\1', result)

        # Remove cross-references: <<anchor,text>> or <<anchor>>
        result = re.sub(r'&lt;&lt;[^,&]+,([^&]+)&gt;&gt;', r'\1', result)
        result = re.sub(r'&lt;&lt;[^&]+&gt;&gt;', '', result)

        # Remove passthrough: +++text+++
        result = re.sub(r'\+\+\+([^\+]+?)\+\+\+', r'\1', result)

        return result.strip()

    def _truncate_text(self, text: str, max_length: int = 100) -> str:
        """Truncate text for display.

        Args:
            text: Text to truncate
            max_length: Maximum length before truncation

        Returns:
            Truncated text
        """
        if len(text) <= max_length:
            return text
        return f"{text[:max_length]}..."


def parse_options() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Namespace containing parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Detect changes in normative tags between two JSON files",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        'reference_file',
        help='Path to the reference tags JSON file'
    )

    parser.add_argument(
        'current_file',
        help='Path to the current tags JSON file'
    )

    parser.add_argument(
        '-u', '--update-reference',
        action='store_true',
        help='Update the reference tags file by adding any additions found in the current file'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show verbose output with detailed processing information'
    )

    return parser.parse_args()


def main():
    """Main execution."""
    options = parse_options()

    detector = TagChangeDetector(verbose=options.verbose)

    # Load both tag files
    reference_tags = detector.load_tags(options.reference_file)
    current_tags = detector.load_tags(options.current_file)

    # Detect changes
    changes = detector.detect_changes(reference_tags, current_tags)

    # Display changes
    detector.display_changes(changes, options.reference_file,
                            options.current_file, options.verbose)

    # Update reference file if requested
    if options.update_reference:
        detector.update_tags_file(options.reference_file, changes)

    # Exit with appropriate status code
    # Return 0 if no changes or only additions
    # Return 1 if any modifications or deletions detected
    has_modifications_or_deletions = bool(changes.modified or changes.deleted)
    sys.exit(1 if has_modifications_or_deletions else 0)


if __name__ == "__main__":
    main()

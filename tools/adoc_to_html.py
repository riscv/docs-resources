"""AsciiDoc formatting conversion helpers."""

import re

# "<" and ">" Unicode decimal values used in entity conversion.
LT_UNICODE_DECIMAL = 60
GT_UNICODE_DECIMAL = 62


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

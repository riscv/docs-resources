# How to Tag Normative Rules in RISC-V International Standards

## What is a Normative Rule?

Normative rules specify the behaviors an implementation must meet in order to be compliant with the standard. Each normative rule can be thought of as a complete individual testable behavior. In some cases, normative rules allow a plurality of acceptable implementations. These are called "parameters" and can be thought of as a special case of a normative rule.

### Examples of Normative Rules:
| ISA Manual Text |
| --------------- |
| "For RV32I, the 32 `x` registers are each 32 bits wide, i.e., `XLEN=32`." |
| "Register `x0` is hardwired with all bits equal to 0." |
| "ADDI adds the sign-extended 12-bit immediate to register _rs1_." |
| "M-mode code can access all CSRs at lower privilege levels." |

### Examples of Parameter Normative Rules:

| ISA Manual Text | Type | Allowed Values |
| --------------- | ---- | -------------- |
| "The EEI will define whether the memory system is little-endian or big-endian." | Enum | little or big |
| "The `misa` register must be readable in any implementation, but a value of zero can be returned to indicate the `misa` register has not been implemented." | Boolean | true/false |
| "If `misa` is nonzero, the MXL field indicates the effective XLEN in M-mode, a constant termed _MXLEN_." | Integer | 32 or 64 |

## Extracting Normative Rules

RISC-V International standards are written in an open-source markup language known as [AsciiDoc](https://docs.asciidoctor.org/asciidoc/latest). If normative rules are not explicitly listed in the visible content of a standard (usually in tables with a unique ID for each normative rule), the AsciiDoc anchor facility is used to "tag" normative text. This latter case is the focus of the remainder of this document.

When normative rules aren't explicitly listed by a standard, it is likely the standard was written without easy identification of normative rules in mind. This can lead to multiple normative rules being located in one tag (tag = anchored section of normative text) known as a "many:1" mapping (many normative rules mapped to one tag) or a normative rule needing to reference multiple tags known as a "1:many" mapping (one normative rule mapped to multiple tags). Here's examples of these cases:
* "many:1" (normative rules for ANDI, ORI, and XORI instructions mapped to one tag)<br>
`ANDI, ORI, XORI are logical operations that perform bitwise AND, OR, and XOR on register rs1 and the sign-extended 12-bit immediate and place the result in rd.`
* "1:many"<br>
TBD: waiting for ideal example

Quite often there is a "1:1" mapping between normative rules and tags, but not always! Because of this "not always" reality, standards provide YAML files that provide the mapping between normative rules and tags. This repository contains a simple Ruby script that uses these YAML files to create the canonical list of normative rules for its associated standard. This script can output these normative rules in formats suitable for both human-friendly and machine-readable formats.

## AsciiDoc Anchor Background

AsciiDoc provides facilities to create invisible anchors associated with an entire paragraph or portions of a paragraph. These anchors are only visible in raw AsciiDoc files and are invisible in the PDF and GitHub AsciiDoc previewer. Each "tag" added to an AsciiDoc file to indentify normative text (remember, not always 1:1 mapping from normative rules to tags) has an associated anchor name. These anchor names must be unique across all the AsciiDoc files used by a particular standard but aren't required to be unique across standards. Each RISC-V standard defines the naming convention of these anchor names but the anchor names must start with the prefix of "norm:" so they can be readily located by tools.

AsciiDoc supports several styles of anchors:
* _inline anchor_ such as:<br>
    `We must [#goal]#free the world#.`
* _paragraph anchor_ such as:

    > `[[foo]]`<br>
    > `This is an anchor for the entire paragraph.`
    >
    > `This isn't part of the anchor since it is the next paragraph.`

* You can also use the _paragraph anchor_ for table cells and list items if placed before the text such as:

    > `| [[foo]] Here is the table cell contents | next cell`

Naming restrictions:
* Start anchor names with a letter and use `:` to separate fields in the anchor name. No spaces allowed in name.
* Use underscores to separate lists of items between colons (e.g., `:insts:add_sub`) since RISC-V
uses `-` in some names (e.g., `R-type`).
* Replace `.` in items with `-` (e.g., `fence.tso` becomes `fence-tso`) so all anchors types used
work properly (see https://docs.asciidoctor.org/asciidoc/latest/attributes/id/#block-assignment for details).

If you'd like to get more detailed AsciiDoc information on anchors, please read:
* How to make cross-references: https://docs.asciidoctor.org/asciidoc/latest/macros/xref/
* How to create anchors: https://docs.asciidoctor.org/asciidoc/latest/attributes/id/

## Adding anchors into AsciiDoc files
1. Anchor to part of a paragraph

    > Syntax:      `[#<anchor-name>]# ... #`<br>
    > Example:     `Here is an example of [#foo]#anchoring part# of a paragraph
    >              and can have [#bar]#multiple anchors# if needed.`<br>
    > Tagged text: `anchoring part` and `multiple anchors`

2. Limitations:
* Can't anchor text across multiple paragraphs.
* Must have text next to the 2nd hash symbol (i.e., can't have newline after `[#<anchor-name]#`).
* Can't put inside admonitions such as [NOTE] (see #5 below for solution).
* Can't have `.` in anchor-name (replace with `-`)

3. Anchor to entire paragraph

    > Syntax:     `[[<anchor-name]]`<br>
    > Example:    `[[zort]]`<br>
    >             `Here is an example of anchoring a whole paragraph.`<br>
    > Tagged text: Entire paragraph<br>

4. Anchor to entire table cell or a list entry

    > Example:    `| Alan Turing | [[Alan_Turing_Birthday]] June 23, 1912 | London`<br>
    > Tagged text: None (just creates hyperlink to anchor in table/list so not so useful)

5. Anchor inside admonition (e.g. `[NOTE]`):
* Must use `[[<anchor-name]]` before each paragraph (with unique anchor names of course) being tagged
* Can't use `[#<anchor-name]#Here's some note text.#` since it just shows up in HTML as normal text
* Don't put `[[<<anchor-name]]` before the entire admonition (e.g., before `[NOTE]`) to apply to entire admonition
(one or more paragraphs) since it will just create a hyperlink with no associated text.

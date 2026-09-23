'use strict'

// Antora extension: xref_text_extension.js
//
// Problem:
//   A cross-reference to an anchor on ANOTHER page with no link text, e.g.
//
//     <<Zkl-notation.adoc#KLEE-Notation>>
//     xref:Zkl-notation.adoc#KLEE-Notation[]
//
//   resolves to the right page in Antora but renders its raw target
//   ("Zkl-notation.adoc#KLEE-Notation") as the link text. Antora does not
//   generate text for a fragment on another page. The same source in a
//   single-document PDF build gets automatic text ("Section 1"), so specs
//   single-sourced from docs-spec-template render correctly in the PDF and
//   badly on the site.
//
// What this does:
//   At contentClassified, for every page, it finds cross-page xrefs that have
//   a fragment and no text, parses the target page (once, cached), looks the
//   fragment up in that page's anchor catalog and writes link text into the
//   source:
//
//     - an explicit reftext, e.g. [[KLEE-IRR-long-running-no-data,IRR4]] -> IRR4
//     - otherwise the title of the section, or of the table/figure/listing
//     - the page's own title when the fragment is the page (doctitle) id
//
//   With `style: short`, a section whose title carries a number from
//   section_numbering_extension ("2.3. Foo") becomes "Section 2.3" instead,
//   matching `xrefstyle: short` in the PDF. Register this extension AFTER
//   section_numbering_extension so it sees the numbered titles.
//
//   Links that already have text, same-page links and targets that cannot be
//   resolved are left untouched (the latter are logged).
//
// Playbook:
//   - require: ./riscv-extensions/xref_text_extension.js
//     style: title        # or: short
//     # components: [zkl] # optional; default is every component

module.exports.register = function ({ config = {} }) {
  const logger = this.getLogger('xref-text-extension')
  const loader = this.require('@antora/asciidoc-loader')
  const loadAsciiDoc = loader.loadAsciiDoc || loader
  const style = config.style === 'short' ? 'short' : 'title'
  const components = config.components ? [].concat(config.components) : null

  this.on('contentClassified', ({ contentCatalog }) => {
    const docCache = new Map()
    const stats = { rewritten: 0, unresolvedPage: 0, unresolvedId: 0, noText: 0 }

    const pages = contentCatalog.findBy({ family: 'page' }).filter(
      (page) => page.src.mediaType === 'text/asciidoc' && (!components || components.includes(page.src.component))
    )

    for (const page of pages) {
      const source = page.contents.toString()
      const rewritten = rewriteXrefs(source, (target, fragment) => {
        const ctx = { component: page.src.component, version: page.src.version, module: page.src.module }
        const targetFile = contentCatalog.resolvePage(target, ctx)
        if (!targetFile) {
          stats.unresolvedPage++
          logger.warn(`${page.src.relative}: cannot resolve page ${target}`)
          return
        }
        if (targetFile === page) return // same page: Asciidoctor generates the text itself
        const doc = loadTarget(targetFile)
        const text = doc && textFor(doc, fragment, style)
        if (text === undefined) {
          stats.unresolvedId++
          logger.warn(`${page.src.relative}: no anchor #${fragment} in ${target}`)
          return
        }
        if (!text) {
          stats.noText++
          return
        }
        stats.rewritten++
        return text
      })
      if (rewritten !== source) page.contents = Buffer.from(rewritten)
    }

    logger.info(
      `Filled link text for ${stats.rewritten} cross-page xref(s); ` +
        `${stats.unresolvedPage} unresolved page(s), ${stats.unresolvedId} unknown anchor(s), ` +
        `${stats.noText} anchor(s) without a title or reftext`
    )

    // Parse a target page with its component version's AsciiDoc config, but
    // without extensions: diagram and other block extensions would do real
    // work (e.g. fetch from Kroki) for a parse that only needs the catalog.
    function loadTarget (file) {
      const key = `${file.src.version}@${file.src.component}:${file.src.module}:${file.src.relative}`
      if (!docCache.has(key)) {
        let doc
        try {
          const cv = contentCatalog.getComponentVersion(file.src.component, file.src.version)
          const asciidocConfig = Object.assign({}, cv && cv.asciidoc, { extensions: [] })
          doc = loadAsciiDoc(file, contentCatalog, asciidocConfig)
        } catch (err) {
          logger.warn(`cannot parse ${file.src.relative}: ${err.message}`)
        }
        docCache.set(key, doc)
      }
      return docCache.get(key)
    }
  })
}

// Delimited blocks whose content is not AsciiDoc text: listing, literal,
// passthrough, comment and fenced code. Xrefs inside them are left alone.
const VERBATIM = /^(-{4,}|\.{4,}|\+{4,}|\/{4,}|`{3,}.*)$/
const XREF = /xref:([^\s[\]#]+\.adoc)#([^\s[\]]+)\[\]/g
const SHORTHAND = /<<([^\s<>#,]+\.adoc)#([^\s<>,]+)>>/g

// Rewrite empty-text cross-page xrefs in AsciiDoc source. resolve(target,
// fragment) returns the link text, or undefined to leave the xref unchanged.
function rewriteXrefs (source, resolve) {
  let fence = null
  return source
    .split('\n')
    .map((line) => {
      const trimmed = line.trimEnd()
      if (fence) {
        if (trimmed === fence) fence = null
        return line
      }
      if (VERBATIM.test(trimmed)) {
        fence = trimmed
        return line
      }
      if (line.startsWith('//')) return line
      const replace = (whole, target, fragment) => {
        const text = resolve(target, fragment)
        return text === undefined ? whole : `xref:${target}#${fragment}[${escapeText(text)}]`
      }
      return line.replace(XREF, replace).replace(SHORTHAND, replace)
    })
    .join('\n')
}

// Link text for an anchor in a parsed document: undefined if the anchor does
// not exist, '' if it exists but has nothing usable.
function textFor (doc, id, style) {
  if (doc.getId && doc.getId() === id) return plain(doc.getDocumentTitle())
  const node = doc.getRefs()[id]
  if (!node) return undefined
  // Inline anchor [[id,reftext]]: the reftext is the inline node's text.
  if (node.getNodeName && node.getNodeName() === 'inline_anchor') return plain(node.getText() || '')
  const reftext = node.getReftext && node.getReftext()
  if (reftext) return plain(reftext)
  const title = node.getTitle ? plain(node.getTitle() || '') : ''
  if (style === 'short' && node.getContext() === 'section') {
    const m = title.match(/^(\d+(?:\.\d+)*)\.\s+/)
    if (m) return `${doc.getAttribute('section-refsig', 'Section')} ${m[1]}`
  }
  return title
}

// Converted titles are HTML; the text goes back into AsciiDoc source.
// Character references (&lt;, &#8594;, ...) are kept as they are: Asciidoctor
// passes them through, so they render as the original characters without
// ever being decoded here into markup that could be interpreted again.
function plain (html) {
  let text = String(html)
    .replace(/<code>([^<]*)<\/code>/g, '`$1`')
    .replace(/<em>([^<]*)<\/em>/g, '_$1_')
    .replace(/<strong>([^<]*)<\/strong>/g, '*$1*')
  // Strip the remaining tags until none are left (a single pass can leave a
  // tag behind, e.g. from "<<b>script>").
  let previous
  do {
    previous = text
    text = text.replace(/<[^<>]*>/g, '')
  } while (text !== previous)
  return text.replace(/[<>]/g, '').trim()
}

// Encode the characters that could end or escape the xref macro's text.
// Backslashes first, so the encoding of "]" is not itself escaped.
function escapeText (text) {
  return text.replace(/\\/g, '&#92;').replace(/]/g, '&#93;')
}

module.exports._test = { rewriteXrefs, textFor, plain, escapeText }

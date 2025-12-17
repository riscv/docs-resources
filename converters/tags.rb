require 'json'

# This is an Asciidoctor backend that allows extracting the content
# from tagged snippets of text.
class TagsConverter
  include Asciidoctor::Converter
  register_for("tags")

  # Hash{String => String} - map from tag ID to its text contents.
  @tag_map = {}
  # Array<String> - the stack of currently open sections in the
  # section tree. Each `Section` contains
  #
  #  * title: String            - Section title.
  #  * id: String               - Generated ID for the title which can be used for HTML links.
  #  * children: Array<Section> - Child sections.
  #  * tags: Array<String>      - List of tags in this section directly (not in children).
  #
  # This always starts with a root section with an empty title and id.
  @section_stack = []

  # Prefix on IDs that we require. We can't look at all IDs because
  # it includes a load of auto-generated ones.
  @prefix = ""

  def initialize(backend, opts = {})
    super
    # Pass `-a tags-output-suffix=.foo` to set suffix of generated output JSON file to ".foo"
    outfilesuffix(opts[:document].attributes.fetch("tags-output-suffix", ".tags.json"))
    # Pass `-a tags-match-prefix=foo` to only include tags starting with `foo`.
    @prefix = opts[:document].attributes.fetch("tags-match-prefix", "")
  end

  # node: AbstractNode
  # returns: String
  def convert(node, transform = node.node_name, opts = nil)
    if transform == "document" then
      # This is the top level node. First clear the outputs.
      @tag_map = {}
      # Root node of the section tree. For simplicity we always
      # have one root node with an empty title.
      @section_stack = [{
        "title" => "",
        "id" => "",
        "children" => [],
        "tags" => [],
      }]

      # Calling node.content will recursively call convert() on all the nodes
      # and also expand blocks, creating inline nodes. We call this to convert
      # all nodes to text, and record their content in the tag map. Then we
      # throw away the text and output the tag map as JSON instead.
      node.content

      # We must always add and remove an equal number of sections from the stack
      # and we started with one so should end with one.
      fail "Tags backend section logic error" if @section_stack.length != 1

      JSON.pretty_generate({
        "tags": @tag_map,
        "sections": @section_stack.first,
      })
    else

      # If it's a section add it to the section tree.
      if transform == "section" then
        section = {
          "title" => node.title,
          "id" => node.id,
          "children" => [],
          "tags" => [],
        }

        @section_stack.last["children"] << section
        @section_stack << section
      end

      # Recursively get the text content of this node.
      content = node_text_content(node)

      # Capture the content in the tag map and section tree if
      # this node is tagged appropriately.
      unless node.id.nil?
        if node.id.start_with?(@prefix)
          raise "Duplicate tag name '#{node.id}'" unless @tag_map[node.id].nil?
          raise "Tag '#{node.id}' content should be a String but it is #{content.class}" unless content.is_a?(String)

          @tag_map[node.id] = content.strip()
          @section_stack.last["tags"] << node.id
        end
      end

      # If it's a section, we've recursed through it (via `node.content`)
      # so pop it from the stack.
      if transform == "section" then
        @section_stack.pop()
      end

      content
    end
  end

  private

  # Return the text content of a node. Adapted from `text-converter.rb`
  # in the docs: https://docs.asciidoctor.org/asciidoctor/latest/convert/custom/
  #
  # node: AbstractNode
  # returns: String
  def node_text_content(node)
    content_or_nil = case node.node_name
    when "document"
      # Can occur when table cells use the "a|" syntax.
      node.content.strip
    when "section"
      "\n" + [node.title, node.content].join("\n").rstrip()
    when "paragraph"
      "\n" + normalize_space(node.content)
    when "ulist", "olist", "colist"
      "\n" + node.items.map do |item|
        normalize_space(item.text) + (item.blocks? ? "\n" + item.content : "")
      end.join("\n")
    when "dlist"
      "\n" + node.items.map do |terms, dd|
        terms.map(&:text).join(", ") +
          (dd&.text? ? "\n" + normalize_space(dd.text) : "") +
          (dd&.blocks? ? "\n" + dd.content : "")
      end.join("\n")
    when "table"
      # This code was wrong in the docs. This is adapted from the HTML5 converter.
      "\n" + node.rows.to_h.map do |tsec, rows|
        rows.map do |row|
          row.map do |cell|
            if tsec == :head
              cell.text
            else
              case cell.style
              when :asciidoc
                cell.content
              when :literal
                cell.text
              else
                # In this case it is an array of paragraphs.
                cell.content.join("\n")
              end
            end
            # Separate cells with "|"
          end.join("|")
          # Separate rows by Unicode pilcrow (AKA paragraph) symbol corresponding to &para;
          # Can't separate rows by newlines because AsciiDoc allows newlines inside table cells (via hard line break)
          # and this is actually used in multiple places in the ISA manual to create column-first-tables.
        end.join("¶")
        # Separate table sections by ===.
      end.join("\n===\n")
    else
      node.inline? ? node.text : ["\n", node.content].compact.join
    end

    content_or_nil.nil? ? "" : content_or_nil
  end

  # Convert newlines to spaces.
  def normalize_space text
    text.tr("\n", " ")
  end
end

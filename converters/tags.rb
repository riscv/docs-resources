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

  # `node` is an `AbstractNode`.
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
      content = if node.inline? then node.text else node.content end

      # Capture the content in the tag map and section tree if
      # this node is tagged appropriately.
      unless node.id.nil?
        if node.id.start_with?(@prefix)
          @tag_map[node.id] = content
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
end

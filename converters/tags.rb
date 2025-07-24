require 'json'

class TagsConverter
  include Asciidoctor::Converter
  register_for("tags")

  @tag_map = {}
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
      @tag_map = {}
      # Calling node.content will recursively call convert() on all the nodes
      # and also expand blocks, creating inline nodes. We call this to convert
      # all nodes to text, and record their content in the tag map. Then we
      # throw away the text and output the tag map as JSON instead.
      node.content
      JSON.pretty_generate({
        "tags": @tag_map,
      })
    else
      # Output the text content of this node.
      content = if node.inline? then node.text else node.content end
      unless node.id.nil?
        if node.id.start_with?(@prefix)
          @tag_map[node.id] = content
        end
      end
      content
    end
  end
end

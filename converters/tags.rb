require 'json'

class TagsConverter
  include Asciidoctor::Converter
  register_for("tags")

  @tag_map = {}
  @prefix = ""

  def initialize(backend, opts = {})
    super
    outfilesuffix(".tags.json")
    # Pass `-a tags-prefix=qx_` to only include tags starting with `qx_`.
    @prefix = opts[:document].attributes.fetch("tags-prefix", "")
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

# frozen_string_literal: true

require 'delegate'

module Asciidoctor
  module Sail
    @@ids = {}

    def self.seen_id?(id)
      @@ids.key?(id)
    end

    def self.get_id(id)
      return unless @@ids.key?(id)

      @@ids[id]
    end

    def self.add_id(id)
      @@ids[id] = id
    end

    def self.add_id_parent(id, parent)
      @@ids[id] = parent
    end

    # A snippet is a small chunk of Sail source with an optional file and location
    class Snippet
      attr_accessor :source, :file, :loc

      def initialize(source, file = nil, loc = nil)
        @source = source
        @file = file
        @loc = loc
      end
    end

    module SourceMacro
      include Asciidoctor::Logging

      # Should match Docinfo.docinfo_version in Sail OCaml source
      VERSION = 1
      PLUGIN_NAME = 'asciidoctor-sail'

      def get_sourcemap(doc, attrs, loc)
        from = attrs.delete('from') { 'sail-doc' }
        source_map = doc.attr(from)
        if source_map.nil?
          info = "Document attribute :#{from}: does not exist, so we don't know where to find any sources"
          logger.error %(#{logger.progname} (#{PLUGIN_NAME})) do
            message_with_context info, source_location: loc
          end
          raise "#{PLUGIN_NAME}: #{info}"
        end
        ::Asciidoctor::Sail::Sources.register(from, source_map)
        json = ::Asciidoctor::Sail::Sources.get(from)
        if json['version'] != VERSION
          logger.warn %(#{logger.progname} (#{PLUGIN_NAME})) do
            message_with_context "Version does not match version in source map #{source_map}", source_location: loc
          end
        end

        [json, from]
      end

      def cross_referencing?(doc)
        doc.attr?('sail-xref')
      end

      def get_type(attrs)
        attrs.delete('type') { 'function' }
      end

      def get_part(attrs)
        attrs.delete('part') { 'source' }
      end

      def get_split(attrs)
        attrs.delete('split') { '' }
      end

      def read_snippet(json, part)
        return ::Asciidoctor::Sail::Snippet.new(json) if json.is_a? String

        json = json.fetch(part, json)

        return ::Asciidoctor::Sail::Snippet.new(json) if json.is_a? String

        source = ''
        file = json['file']
        loc = json['loc']

        if json['contents'].nil?
          raise "#{PLUGIN_NAME}: File #{file} does not exist" unless File.exist?(file)

          contents = File.read(file)

          # Get the source code, adjusting for the indentation of the first line of the span
          indent = loc[2] - loc[1]

          source = contents.byteslice(loc[2], loc[5] - loc[2])
          source = (' ' * indent) + source
        else
          source = json['contents']
        end

        ::Asciidoctor::Sail::Snippet.new(source, file, loc)
      end

      def get_sail_object(json, target, attrs)
        type = get_type(attrs)
        json = json["#{type}s"]
        raise "#{PLUGIN_NAME}: No Sail objects of type #{type}" if json.nil?

        json = json[target]
        raise "#{PLUGIN_NAME}: No Sail #{type} #{target} could be found" if json.nil?

        links = json['links']

        json = json[type]

        if attrs.key? 'clause'
          clause = attrs.delete('clause')
          json.each do |child|
            if match_clause(clause, child['pattern'])
              json = child
              break
            end
          end
        elsif attrs.key? 'left-clause'
          clause = attrs.delete('left-clause')
          json.each do |child|
            if match_clause(clause, child['left'])
              json = child
              break
            end
          end
        elsif attrs.key? 'right-clause'
          clause = attrs.delete('right-clause')
          json.each do |child|
            if match_clause(clause, child['right'])
              json = child
              break
            end
          end
        elsif attrs.key? 'grep'
          grep = attrs.delete('grep')
          json.each do |child|
            source = read_snippet(child, 'body').source
            json = child if source =~ Regexp.new(grep)
          end
        end

        [json, type, links]
      end

      # Compute the minimum indentation for any line in a source block
      def minindent(tabwidth, source)
        indent = -1
        source.each_line do |line|
          line_indent = 0
          line.chars.each do |c|
            case c
            when ' '
              line_indent += 1
            when "\t"
              line_indent += tabwidth
            else
              break
            end
          end
          indent = line_indent if indent == -1 || line_indent < indent
        end
        indent
      end

      def insert_links(snippet, links, from, type)
        return snippet.source if snippet.loc.nil? || snippet.file.nil? || links.nil?

        cursor = snippet.loc[2]
        link_end = nil
        final = ''

        snippet.source.each_byte do |b|
          if !link_end.nil? && cursor == link_end
            final += ']'
            link_end = nil
          else
            links.each do |link|
              if link['loc'][0] == cursor && link['file'] == snippet.file && link_end.nil?
                final += "sailref:#{from}##{type}["
                link_end = link['loc'][1]
              end
            end
          end

          final += b.chr
          cursor += 1
        end

        final
      end

      def get_source(doc, target, attrs, loc)
        json, from = get_sourcemap doc, attrs, loc
        json, type, links = get_sail_object json, target, attrs
        dedent = attrs.any? { |k, v| (k.is_a? Integer) && %w[dedent unindent].include?(v) }
        strip = attrs.any? { |k, v| (k.is_a? Integer) && %w[trim strip].include?(v) }

        part = get_part attrs
        split = get_split attrs
        snippet = if split == ''
                    read_snippet(json, part)
                  else
                    ::Asciidoctor::Sail::Snippet.new(json['splits'][split])
                  end

        source = if cross_referencing? doc
                   insert_links(snippet, links, from, type)
                 else
                   snippet.source
                 end

        source.strip! if strip

        if dedent
          lines = ''
          min = minindent 4, source

          source.each_line do |line|
            lines += line[min..]
          end
          source = lines
        end

        [source, type, from]
      end

      def match_clause(desc, json)
        if desc =~ /^([a-zA-Z_?][a-zA-Z0-9_?#]*)(\(.*\))$/
          return false unless json['type'] == 'app' && json['id'] == ::Regexp.last_match(1)

          patterns = json['patterns']
          patterns = patterns[0] if patterns.length == 1

          match_clause ::Regexp.last_match(2), patterns
        elsif desc.length.positive? && desc[0] == '('
          tuples = nil
          tuples = if json.is_a? Array
                     json
                   elsif json['type'] == 'tuple'
                     json['patterns']
                   else
                     [json]
                   end

          results = []
          desc[1...-1].split(',').each_with_index do |desc, i|
            results.push(match_clause(desc.strip, tuples[i]))
          end
          results.all?
        elsif desc == '_'
          true
        elsif desc =~ /^([a-zA-Z_?][a-zA-Z0-9_?#]*)$/
          json['type'] == 'id' && json['id'] == ::Regexp.last_match(1)
        elsif desc =~ /^(0[bx][a-fA-F0-9]*)$/
          json['type'] == 'literal' && json['value'] == ::Regexp.last_match(1)
        else
          false
        end
      end
    end

    class SourceBlockMacro < ::Asciidoctor::Extensions::BlockMacroProcessor
      include SourceMacro

      use_dsl

      named :sail

      def process(parent, target, attrs)
        logger.info "Including Sail source #{target} #{attrs}"
        loc = parent.document.reader.cursor_at_mark

        source, type, from = get_source parent.document, target, attrs, loc

        id = if type == 'function'
               "#{from}-#{target}"
             else
               "#{from}-#{type}-#{target}"
             end

        if ::Asciidoctor::Sail.seen_id?(id)
          block = create_listing_block parent, source, { 'style' => 'source', 'language' => 'sail' }
        else
          ::Asciidoctor::Sail.add_id(id)
          block = create_listing_block parent, source, { 'id' => id, 'style' => 'source', 'language' => 'sail' }
        end

        block
      end
    end

    class SourceIncludeProcessor < ::Asciidoctor::Extensions::IncludeProcessor
      include SourceMacro

      def handles?(target)
        target.start_with? 'sail:'
      end

      def process(doc, reader, target, attrs)
        logger.info "Including Sail source #{target} #{attrs}"
        loc = reader.cursor_at_mark

        target.delete_prefix! 'sail:'

        source, type, from = get_source doc, target, attrs, loc

        hyper_ref = attrs.delete('ref')

        id = if type == 'function'
               "#{from}-#{target}"
             else
               "#{from}-#{type}-#{target}"
             end

        ::Asciidoctor::Sail.add_id_parent(id, hyper_ref) unless ::Asciidoctor::Sail.seen_id?(id)

        reader.push_include source, target, target, 1, {}
        reader
      end
    end

    class WavedromIncludeProcessor < ::Asciidoctor::Extensions::IncludeProcessor
      include SourceMacro

      def handles?(target)
        target.start_with? 'sailwavedrom:'
      end

      def process(doc, reader, target, attrs)
        target.delete_prefix! 'sailwavedrom:'
        json, = get_sourcemap doc, attrs, reader.cursor_at_mark
        json, = get_sail_object json, target, attrs

        key = 'wavedrom'
        if attrs.any? { |k, v| (k.is_a? Integer) && v == 'right' }
          key = 'right_wavedrom'
        elsif attrs.any? { |k, v| (k.is_a? Integer) && v == 'left' }
          key = 'left_wavedrom'
        end

        diagram = if attrs.any? { |k, v| (k.is_a? Integer) && v == 'raw' }
                    json[key]
                  else
                    "[wavedrom, ,]\n....\n#{json[key]}\n...."
                  end

        reader.push_include diagram, target, target, 1, {}
        reader
      end
    end

    class DocCommentIncludeProcessor < ::Asciidoctor::Extensions::IncludeProcessor
      include SourceMacro

      def handles?(target)
        target.start_with? 'sailcomment:'
      end

      def process(doc, reader, target, attrs)
        target.delete_prefix! 'sailcomment:'
        json, = get_sourcemap doc, attrs, reader.cursor_at_mark
        json, = get_sail_object json, target, attrs

        if json.nil? || json.is_a?(Array)
          raise "#{PLUGIN_NAME}: Could not find Sail object for #{target} when processing include::sailcomment. You may need to specify a clause."
        end

        comment = json['comment']
        raise "#{PLUGIN_NAME}: No documentation comment for Sail object #{target}" if comment.nil?

        reader.push_include comment.strip, nil, nil, 1, {}
        reader
      end
    end

    # We want to swap out the source of a listing block to include
    # cross-referenced source, but asciidoctor won't let us write to
    # content directly.
    class ListingDecorator < SimpleDelegator
      attr_accessor :source

      def content
        source
      end
    end

    # This class overrides the default asciidoctor html5 converter by
    # post-processing the listing blocks that contain Sail code to
    # insert cross referencing information.
    class ListingLinkInserter < (Asciidoctor::Converter.for 'html5')
      include SourceMacro

      register_for 'html5'

      SAILREF_REGEX = /sailref:(?<from>[^#]*)#(?<type>[^\[]*)\[(?<sail_id>[^\]]*)\]/

      def match_id(match, override_type = nil)
        type = override_type.nil? ? match[:type] : override_type
        if type == 'function'
          "#{match[:from]}-#{match[:sail_id]}"
        else
          "#{match[:from]}-#{type}-#{match[:sail_id]}"
        end
      end

      def instantiate_template(match, ext)
        return match[:sail_id] unless /^[a-zA-Z0-9_#?]*$/ =~ match[:sail_id]

        json = ::Asciidoctor::Sail::Sources.get(match[:from])
        commit = json['git']['commit']
        json, = get_sail_object json, match[:sail_id], { 'type' => match[:type] }
        json = json.fetch('source', json)
        file = json['file']
        line = json['loc'][0]
        ext = ext.gsub('%commit%', commit)
        ext = ext.gsub('%file%', file)
        ext = ext.gsub('%filehtml%', file.gsub('.sail', '.html'))
        ext = ext.gsub('%line%', line.to_s)
        "<a href=\"#{ext}\">#{match[:sail_id]}</a>"
      rescue Exception
        match[:sail_id]
      end

      def source_with_link(match, ref, ext)
        if ref.nil? && ext.nil?
          "#{match.pre_match}#{match[:sail_id]}#{match.post_match}"
        elsif ref.nil?
          "#{match.pre_match}#{instantiate_template(match, ext)}#{match.post_match}"
        else
          "#{match.pre_match}<a href=\"##{ref}\">#{match[:sail_id]}</a>#{match.post_match}"
        end
      end

      def external_template(document)
        document.attr('sail-xref-external')
      end

      def convert_listing(node)
        return super unless node.style == 'source' && (node.attr 'language') == 'sail'

        source = node.content
        ext = external_template node.document

        loop do
          match = source.match(SAILREF_REGEX)
          break if match.nil?

          ref = ::Asciidoctor::Sail.get_id(match_id(match))
          ref = ::Asciidoctor::Sail.get_id(match_id(match, 'val')) if ref.nil? && match[:type] == 'function'
          source = source_with_link(match, ref, ext)
        end

        decorated_node = ListingDecorator.new(node)
        decorated_node.source = source

        super(decorated_node)
      end
    end
  end
end

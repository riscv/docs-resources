# frozen_string_literal: true

require "json"
require "yaml"

PN = "create_normative_rules.rb"

# Global constants
LT_UNICODE_DECIMAL = 60     # "<" Unicode decimal value
GT_UNICODE_DECIMAL = 62     # ">"" Unicode decimal value

LT_UNICODE_STR = "&##{LT_UNICODE_DECIMAL};"   # "<" Unicode string
GT_UNICODE_STR = "&##{GT_UNICODE_DECIMAL};"   # ">" Unicode string

NORM_PREFIX = "norm:"

MAX_TABLE_ROWS = 12         # Max rows of a table displayed in a cell.

# Names/prefixes for tables in HTML output.
NORM_RULES_CH_TABLE_NAME_PREFIX = "table-norm-rules-ch-"
IMPLDEFS_A_Z_TABLE_NAME = "table-impldefs-a-z"
IMPLDEFS_CH_TABLE_NAME_PREFIX = "table-impldefs-ch-"
FIELD_TYPE_TABLE_NAME_PREFIX = "table-field-type-"

# Enums
KINDS = ["extension", "extension_dependency", "instruction", "csr", "csr_field"]
FIELD_TYPES = ["WARL", "WLRL"]

# Norm rule name checking
NORM_RULE_NAME_PATTERN = "^[a-zA-Z][a-zA-Z0-9_-]+$"
IMPLDEF_NAME_PATTERN = "^[A-Z][A-Z0-9_]+$"

###################################
# Classes for Normative Rule Tags #
###################################

# Holds all the normative rule tags for a RISC-V standard.
class NormativeTags
  def initialize
    # Contains tag entries as a flat hash for the entire standard (across multiple tag files).
    # The hash key is the tag name and the hash value is a NormativeTag object
    # The tag names must be unique across the standard.
    @tag_map = {}
  end

  # Add tags for specified standards document.
  #
  # param tag_filename [String] Name of the tag file
  # param tags [Hash<String,String>] Hash key is tag name (AKA anchor name) and value is tag text.
  def add_tags(tag_filename, tags)
    fatal("Need String for tag_filename but was passed a #{tag_filename.class}") unless tag_filename.is_a?(String)
    fatal("Need Hash for tags but was passed a #{tags.class}") unless tags.is_a?(Hash)

    tags.each do |name, text|
      unless name.is_a?(String)
        fatal("Tag name #{name} in file #{tag_filename} is a #{name.class} instead of a String")
      end

      unless text.is_a?(String)
        fatal("Tag name #{name} in file #{tag_filename} is a #{text.class} instead of a String
#{PN}:   If the AsciiDoc anchor for #{name} is before an AsciiDoc 'Description List' term, move to after term on its own line.")
      end

      unless @tag_map[name].nil?
        fatal("Tag name #{name} in file #{tag_filename} already defined in file #{@tag_map[name].tag_filename}")
      end

      @tag_map[name] = NormativeTag.new(name, tag_filename, text)
    end
  end

  # @param [String] Normative rule tag name
  # @return [NormativeTag] Normative rule tag object corresponding to tag name. Returns nil if not found.
  def get_tag(name) = @tag_map[name]

  # @return [Array<NormativeTag>] All normative tags for the standard.
  def get_tags() = @tag_map.values
end

# Holds all information for one tag.
class NormativeTag
  # @return [String] Name of normative rule tag in standards document
  attr_reader :name

  # @return [String] Name of tag file
  attr_reader :tag_filename

  # @return [String] Text associated with normative rule tag from standards document. Can have newlines.
  attr_reader :text

  # @param name [String]
  # @param tag_filename [String]
  # @param text [String]
  def initialize(name, tag_filename, text)
    fatal("Need String for name but passed a #{name.class}") unless name.is_a?(String)
    fatal("Need String for tag_filename but passed a #{tag_filename.class}") unless tag_filename.is_a?(String)
    fatal("Need String for text but passed a #{text.class}") unless text.is_a?(String)

    @name = name
    @tag_filename = tag_filename
    @text = text
  end
end

##########################################
# Classes for Normative Rule Definitions #
##########################################

# Holds all the information for all normative rule definition files.
class NormativeRuleDefs
  attr_reader :norm_rule_defs  # Array<NormativeRuleDef> Contains all normative rule definitions across all input files

  def initialize
    @norm_rule_defs = []
    @defs_by_name = {}     # Hash<String name, NormativeRuleDef> Same objects as in array and just internal to class
  end

  def add_file_contents(def_filename, chapter_name, array_data)
    fatal("Need String for def_filename but passed a #{def_filename.class}") unless def_filename.is_a?(String)
    fatal("Need String for chapter_name but passed a #{chapter_name.class}") unless chapter_name.is_a?(String)
    fatal("Need Array for array_data but passed a #{array_data.class}") unless array_data.is_a?(Array)

    array_data.each do |data|
      fatal("File #{def_filename} entry isn't a hash: #{data}") unless data.is_a?(Hash)

      if !data["name"].nil?
        # Add one definition object
        add_def(data["name"], def_filename, chapter_name, data)
      elsif !data["names"].nil?
        # Add one definition object for each name in array
        names = data["names"]
        names.each do |name|
          add_def(name, def_filename, chapter_name, data)
        end
      else
        fatal("File #{def_filename} missing name/names in normative rule definition entry: #{data}")
      end
    end
  end

  def add_def(name, def_filename, chapter_name, data)
    fatal("Need String for name but passed a #{name.class}") unless name.is_a?(String)
    fatal("Need String for def_filename but passed a #{def_filename.class}") unless def_filename.is_a?(String)
    fatal("Need String for chapter_name but passed a #{chapter_name.class}") unless chapter_name.is_a?(String)
    fatal("Need Hash for data but passed a #{data.class}") unless data.is_a?(Hash)

    unless @defs_by_name[name].nil?
      fatal("Normative rule definition #{name} in file #{def_filename} already defined in file #{@defs_by_name[name].def_filename}")
    end

    # Create definition object and store reference to it in array (to maintain order) and defs_by_name (for convenient lookup by name).
    norm_rule_def = NormativeRuleDef.new(name, def_filename, chapter_name, data)
    @norm_rule_defs.append(norm_rule_def)
    @defs_by_name[name] = norm_rule_def
  end
end # class NormativeRuleDefs

# Holds reference to one tag in a normative rule definition.
class TagRef
  attr_reader :name      # Tag name, String (mandatory)

  def initialize(name, context = false)
    fatal("Need String for name but was passed a #{name.class}") unless name.is_a?(String)
    fatal("Need Boolean for context but was passed a #{context.class}") unless context == true || context == false

    @name = name
    @context = context
  end

  def context? = @context
end

# Holds one normative rule definition.
class NormativeRuleDef
  attr_reader :name                   # Normative rule name, String (mandatory)
  attr_reader :def_filename           # String (mandatory)
  attr_reader :chapter_name           # String (mandatory)
  attr_reader :summary                # String (optional - a few words)
  attr_reader :note                   # String (optional - as long as needed)
  attr_reader :clarification_text     # String (optional - as long as needed)
  attr_reader :clarification_link     # String (optional - as long as needed)
  attr_reader :description            # String (optional - sentence, paragraph, or more)
  attr_reader :kind                   # String (optional, can be nil)
  attr_reader :impldef                # Boolean (optional, true or false, never nil)
  attr_reader :instances              # Array<String> (optional - can be empty)
  attr_reader :field_type             # String (optional, can be nil)
  attr_reader :tag_refs               # Array<TagRef> (optional - can be empty)

  def initialize(name, def_filename, chapter_name, data)
    fatal("Need String for name but was passed a #{name.class}") unless name.is_a?(String)
    fatal("Need String for def_filename but was passed a #{def_filename.class}") unless def_filename.is_a?(String)
    fatal("Need String for chapter_name but was passed a #{chapter_name.class}") unless chapter_name.is_a?(String)
    fatal("Need Hash for data but was passed a #{data.class}") unless data.is_a?(Hash)

    @name = name
    @def_filename = def_filename
    @chapter_name = chapter_name

    @summary = data["summary"]
    unless @summary.nil?
      fatal("Provided #{@summary.class} class for summary in normative rule #{name} but need a String") unless @summary.is_a?(String)
    end

    @note = data["note"]
    unless @note.nil?
      fatal("Provided #{@note.class} class for note in normative rule #{name} but need a String") unless @note.is_a?(String)
    end

    @clarification_link = data["clarification-link"]
    unless @clarification_link.nil?
      fatal("Provided #{@clarification_link.class} class for clarification_link in normative rule #{name} but need a String") unless @clarification_link.is_a?(String)
    end

    @clarification_text = data["clarification-text"]
    unless @clarification_text.nil?
      fatal("Provided #{@clarification_text.class} class for clarification_text in normative rule #{name} but need a String") unless @clarification_text.is_a?(String)
    end

    @description = data["description"]
    unless @description.nil?
      fatal("Provided #{@description.class} class for description in normative rule #{name} but need a String") unless @description.is_a?(String)
    end

    @kind = data["kind"]
    unless @kind.nil?
      fatal("Provided #{@kind.class} class for kind in normative rule #{name} but need a String") unless @kind.is_a?(String)
      check_kind(@kind, @name, nil)
    end

    if data["impl-def-behavior"].nil?
      @impldef = false
    else
      @impldef = data["impl-def-behavior"]
    end

    @field_type = data["field-type"]
    unless @field_type.nil?
      fatal("Provided #{@field_type.class} class for field_type in normative rule #{name} but need a String") unless @field_type.is_a?(String)
      check_field_type(@field_type, @name, nil)
    end

    @instances = []
    @instances.append(data["instance"]) unless data["instance"].nil?
    data["instances"]&.each do |instance_name|
      @instances.append(instance_name)
    end

    if @kind.nil?
      # Not allowed to have instances without a kind.
      fatal("Normative rule #{name} defines instances but no kind") unless @instances.empty?
    else
      fatal("Provided #{@instances.class} class for instances in normative rule #{nr_name} but need an Array") unless @instances.is_a?(Array)
    end

    @tag_refs = []
    @tag_refs.append(TagRef.new(data["tag"])) unless data["tag"].nil?
    data["tags"]&.each do |tag_data|
      if tag_data.is_a?(String)
        @tag_refs.append(TagRef.new(tag_data))
      elsif tag_data.is_a?(Hash)
        tag_name = tag_data["name"]
        fatal("Normative rule #{name} tag reference #{tag_data} missing name") if tag_name.nil?

        context = tag_data["context"].nil? ? false : tag_data["context"]

        @tag_refs.append(TagRef.new(tag_name, context))
      else
        fatal("Normative rule #{name} has tag reference that's a #{tag_data.class} instead of a String or Hash: #{tag_data}")
      end
    end

    # Validate name (function of impldef).
    pattern = @impldef ? IMPLDEF_NAME_PATTERN : NORM_RULE_NAME_PATTERN
    unless @name.match?(Regexp.new(pattern))
      fatal("Normative rule '#{name}' doesn't match regex pattern '#{pattern}")
    end
  end
end # class NormativeRuleDef

# Create fatal if kind not recognized. The name is nil if this is called in the normative rule definition.
def check_kind(kind, nr_name, name)
  unless KINDS.include?(kind)
    tag_str = name.nil? ? "" : "tag #{name} in "
    allowed_str = KINDS.join(",")
    fatal("Don't recognize kind '#{kind}' for #{tag_str}normative rule #{nr_name}\n#{PN}: Allowed kinds are: #{allowed_str}")
  end
end

# Create fatal if field_type not recognized. The name is nil if this is called in the normative rule definition.
def check_field_type(field_type, nr_name, name)
  unless FIELD_TYPES.include?(field_type)
    tag_str = name.nil? ? "" : "tag #{name} in "
    allowed_str = FIELD_TYPES.join(",")
    fatal("Don't recognize field-type '#{field_type}' for #{tag_str}normative rule #{nr_name}\n#{PN}: Allowed field-types are: #{allowed_str}")
  end
end

def fatal(msg)
  error(msg)
  exit(1)
end

def error(msg)
  puts "#{PN}: ERROR: #{msg}"
end

def info(msg)
  puts "#{PN}: #{msg}"
end

def usage(exit_status = 1)
  puts "Usage: #{PN} [OPTION]... <output-filename>"
  puts "  --help                  Display this usage message"
  puts "  -j                      Set output format to JSON (default)"
  puts "  -h                      Set output format to HTML"
  puts "  -w                      Warning instead of error if tags found without rules (Only use for debugging!)"
  puts "  -d fname                Normative rule definition filename (YAML format)"
  puts "  -t fname                Normative tag filename (JSON format)"
  puts "  -tag2url tag-fname url  Maps from tag fname to corresponding URL to stds doc"
  puts
  puts "Creates list of normative rules and stores them in <output-filename> (JSON format)."
  exit exit_status
end

# Returns array of command line information.
# Uses Ruby ARGV variable to access command line args.
# Exits program on error.
def parse_argv
  usage(0) if ARGV.count == 1 && (ARGV[0] == "--help")

  usage if ARGV.count == 0

  # Return values
  def_fnames=[]
  tag_fnames=[]
  tag_fname2url={}
  output_fname=nil
  output_format="json"
  warn_if_tags_no_rules = false

  i = 0
  while i < ARGV.count
    arg = ARGV[i]
    case arg
    when "--help"
      usage 0
    when "-j"
      output_format = "json"
    when "-h"
      output_format = "html"
    when "-w"
      warn_if_tags_no_rules = true
    when "-d"
      if (ARGV.count-i) < 1
        info("Missing argument for -d option")
        usage
      end
      def_fnames.append(ARGV[i+1])
      i=i+1
    when "-t"
      if (ARGV.count-i) < 1
        info("Missing argument for -t option")
        usage
      end
      tag_fnames.append(ARGV[i+1])
      i=i+1
    when "-tag2url"
      if (ARGV.count-i) < 2
        info("Missing one or more arguments for -tag2url option")
        usage
      end
      tag_fname = ARGV[i+1]
      url = ARGV[i+2]
      tag_fname2url[tag_fname] = url
      i=i+2
    when /^-/
      info("Unknown command-line option #{arg}")
    else
      if (ARGV.count-i) == 1
        # Last command-line argument
        output_fname = arg
      else
        info("Unknown option '#{arg}' i=#{i} ARGVcount=#{ARGV.count}")
        usage
      end
    end

    i=i+1
  end

  if def_fnames.empty?
    info("Missing normative rule definition filename(s)")
    usage
  end

  if tag_fnames.empty?
    info("Missing normative tag filename(s)")
    usage
  end

  if output_fname.nil?
    info("Missing output filename")
    usage
  end

  if (output_format == "json" || output_format == "html") && tag_fname2url.empty?
    info("Missing -tag2url command line options")
    usage
  end

  return [def_fnames, tag_fnames, tag_fname2url, output_fname, output_format, warn_if_tags_no_rules]
end

# Load the contents of all normative rule tag files in JSON format.
# Returns a NormativeTag class with all the contents.
def load_tags(tag_fnames)
  fatal("Need Array<String> for tag_fnames but passed a #{tag_fnames.class}") unless tag_fnames.is_a?(Array)

  tags = NormativeTags.new()

  tag_fnames.each do |tag_fname|
    info("Loading tag file #{tag_fname}")

    # Read in file to a String
    begin
      file_contents = File.read(tag_fname, encoding: "UTF-8")
    rescue Errno::ENOENT => e
      fatal("#{e.message}")
    end

    # Convert String in JSON format to a Ruby hash.
    begin
      file_data = JSON.parse(file_contents)
    rescue JSON::ParserError => e
      fatal("File #{tag_fname} JSON parsing error: #{e.message}")
    rescue JSON::NestingError => e
      fatal("File #{tag_fname} JSON nesting error: #{e.message}")
    end

    tags_data = file_data["tags"] || fatal("Missing 'tags' key in #{tag_fname}")

    # Add tags from JSON file to Ruby class.
    tags.add_tags(tag_fname, tags_data)
  end

  return tags
end

# Load the contents of all normative rule definition files in YAML format.
# Returns a NormativeRuleDef class with all the contents.
def load_definitions(def_fnames)
  fatal("Need Array<String> for def_fnames but passed a #{def_fnames.class}") unless def_fnames.is_a?(Array)

  defs = NormativeRuleDefs.new()

  def_fnames.each do |def_fname|
    info("Loading definition file #{def_fname}")

    # Read in file to a String
    begin
      file_contents = File.read(def_fname, encoding: "UTF-8")
    rescue Errno::ENOENT => e
      fatal("#{e.message}")
    end

    # Convert String in YAML format to a Ruby hash.
    # Note that YAML is an alias for Pysch in Ruby.
    begin
      yaml_hash = YAML.load(file_contents)
    rescue Psych::SyntaxError => e
      fatal("File #{def_fname} YAML syntax error - #{e.message}")
    end

    chapter_name = yaml_hash["chapter_name"] || fatal("Missing 'chapter_name' key in #{def_fname}")

    array_data = yaml_hash["normative_rule_definitions"] || fatal("Missing 'normative_rule_definitions' key in #{def_fname}")
    fatal("'normative_rule_definitions' isn't an array in #{def_fname}") unless array_data.is_a?(Array)

    defs.add_file_contents(def_fname, chapter_name, array_data)
  end

  return defs
end

# Returns a Hash with just one entry called "normative_rules" that contains an Array of Hashes of all normative rules.
# Hash is suitable for JSON/YAML serialization.
def create_normative_rules_hash(defs, tags, tag_fname2url)
  fatal("Need NormativeRuleDefs for defs but was passed a #{defs.class}") unless defs.is_a?(NormativeRuleDefs)
  fatal("Need NormativeTags for tags but was passed a #{tags.class}") unless tags.is_a?(NormativeTags)
  fatal("Need Hash for tag_fname2url but passed a #{tag_fname2url.class}") unless tag_fname2url.is_a?(Hash)

  info("Creating normative rules from definition files")

  ret = {
    "normative_rules" => []
  }

  defs.norm_rule_defs.each do |d|
    # Create hash with mandatory definition file arguments.
    hash = {
      "name" => d.name,
      "def_filename" => d.def_filename,
      "chapter_name" => d.chapter_name
    }

    # Now add optional arguments.
    hash["kind"] = d.kind unless d.kind.nil?
    hash["impl-def-behavior"] = d.impldef unless d.impldef.nil?
    hash["instances"] = d.instances unless d.instances.empty?
    hash["field-type"] = d.field_type unless d.field_type.nil?
    hash["summary"] = d.summary unless d.summary.nil?
    hash["note"] = d.note unless d.note.nil?
    hash["clarification-text"] = d.clarification_text unless d.clarification_text.nil?
    hash["clarification-link"] = d.clarification_link unless d.clarification_link.nil?
    hash["description"] = d.description unless d.description.nil?

    unless d.tag_refs.nil?
      hash["tags"] = []
    end

    # Add tag entries
    unless d.tag_refs.nil?
      d.tag_refs.each do |tag_ref|
        # Lookup tag
        tag = tags.get_tag(tag_ref.name)
        fatal("Normative rule #{d.name} defined in file #{d.def_filename} references non-existent tag #{tag_ref.name}") if tag.nil?

        url = tag_fname2url[tag.tag_filename]
        fatal("No fname tag to URL mapping (-tag2url cmd line arg) for tag fname #{tag.tag_filename} for tag name #{tag.name}") if url.nil?

        resolved_tag = {
          "name" => tag.name,
          "context" => tag_ref.context?,
          "text" => tag.text,
          "tag_filename" => tag.tag_filename,
          "stds_doc_url" => url
        }

        hash["tags"].append(resolved_tag)
      end
    end

    ret["normative_rules"].append(hash)
  end

  return ret
end

# Fatal error if any normative rule references a non-existant tag.
# Fatal error or warning (controlled by cmd line switch) if there are tags that no rule references.
def validate_defs_and_tags(defs, tags, warn_if_tags_no_rules)
  fatal("Need NormativeRuleDefs for defs but passed a #{defs.class}") unless defs.is_a?(NormativeRuleDefs)
  fatal("Need NormativeTags for tags but was passed a #{tags.class}") unless tags.is_a?(NormativeTags)

  missing_tag_cnt = 0
  bad_norm_rule_name_cnt = 0
  unref_cnt = 0
  referenced_tags = {}    # Key is tag name and value is any non-nil value
  rule_name_lengths = []
  tag_name_lengths = []

  # Go through each normative rule definition. Look for:
  #   - References to non-existant tags
  #   - Normative rule names starting with NORM_PREFIX (should only be for tags)
  defs.norm_rule_defs.each do |d|
    unless d.tag_refs.nil?
      d.tag_refs.each do |tag_ref|
        # Lookup tag by its name
        tag = tags.get_tag(tag_ref.name)

        if tag.nil?
          missing_tag_cnt += 1
          error("Normative rule #{d.name} references non-existent tag #{tag_ref.name} in file #{d.def_filename}")
        else
          referenced_tags[tag.name] = 1 # Any non-nil value
        end
      end

      if d.name.start_with?(NORM_PREFIX)
        bad_norm_rule_name_cnt += 1
        error("Normative rule #{d.name} starts with \"#{NORM_PREFIX}\" prefix. This prefix is only for tag names, not rule names.")
      end

      unless d.clarification_text.nil?
        if d.clarification_link.nil?
          error("Normative rule #{d.name} has clarification-text but no clarification-link")
        end
      end

      unless d.clarification_link.nil?
        unless d.clarification_link =~ %r{^https://(www.)?github\.com/riscv/.+/issues/[0-9]+$}
          error("Normative rule #{d.name} clarification-link of '#{d.clarification_link}' doesn't look like a RISC-V GitHub issue link")
        end
      end
    end

    # Increment length (ensure it isn't nil first with ||=)
    rule_name_lengths[d.name.length] ||= 0
    rule_name_lengths[d.name.length] += 1
  end

  # Look for any unreferenced tags.
  tags.get_tags.each do |tag|
    if referenced_tags[tag.name].nil?
      msg = "Tag #{tag.name} not referenced by any normative rule. Did you forget to define a normative rule?"
      if warn_if_tags_no_rules
        info(msg)
      else
        error(msg)
      end
      unref_cnt = unref_cnt + 1
    end

    # Increment length (ensure it isn't nil first with ||=)
    tag_name_lengths[tag.name.length] ||= 0
    tag_name_lengths[tag.name.length] += 1
  end

  if missing_tag_cnt > 0
    error("#{missing_tag_cnt} reference#{missing_tag_cnt == 1 ? "" : "s"} to non-existing tags")
  end

  if bad_norm_rule_name_cnt > 0
    error("#{bad_norm_rule_name_cnt} illegal normative rule name#{bad_norm_rule_name_cnt == 1 ? "" : "s"}")
  end

  if unref_cnt > 0
    msg = "#{unref_cnt} tag#{unref_cnt == 1 ? "" : "s"} have no normative rules referencing them"
    if warn_if_tags_no_rules
      info(msg)
    else
      error(msg)
    end
  end

  if (missing_tag_cnt > 0) || (bad_norm_rule_name_cnt > 0) || ((unref_cnt > 0) && !warn_if_tags_no_rules)
    fatal("Exiting due to errors")
  end
end

module Adoc2HTML
  extend self

  # Apply constrained formatting pair transformation
  # Single delimiter, bounded by whitespace/punctuation
  # Example: "That is *strong* stuff!" or "This is *strong*!"
  #
  # @param text [String] The text to transform
  # @param delimiter [String] The formatting delimiter (e.g., '*', '_', '`')
  # @param recursive [Boolean] Whether to recursively process nested formatting
  # @yield [content] Block that transforms the captured content
  # @yieldparam content [String] The text between the delimiters
  # @yieldreturn [String] The transformed content
  # @return [String] The text with formatting applied
  def constrained_format_pattern(text, delimiter, recursive: false, &block)
    escaped_delimiter = Regexp.escape(delimiter)
    # (?:^|\s) - start of line or space before
    # \K - keep assertion (excludes preceding pattern from match)
    # #{escaped_delimiter} - single opening mark
    # (\S(?:(?!\s).*?(?<!\s))?) - text that doesn't start/end with space
    # #{escaped_delimiter} - single closing mark
    # (?=[,;".?!\s]|$) - followed by punctuation, space, or end of line
    pattern = /(?:^|\s)\K#{escaped_delimiter}(\S(?:(?!\s).*?(?<!\s))?)#{escaped_delimiter}(?=[,;".?!\s]|$)/
    text.gsub(pattern) do
      content = $1
      # Recursively process nested formatting if enabled
      content = convert_nested(content) if recursive
      block.call(content)
    end
  end

  # Apply unconstrained formatting pair transformation
  # Double delimiter, can be used anywhere
  # Example: "Sara**h**" or "**man**ual"
  #
  # @param text [String] The text to transform
  # @param delimiter [String] The formatting delimiter (e.g., '*', '_', '`')
  # @param recursive [Boolean] Whether to recursively process nested formatting
  # @yield [content] Block that transforms the captured content
  # @yieldparam content [String] The text between the delimiters
  # @yieldreturn [String] The transformed content
  # @return [String] The text with formatting applied
  def unconstrained_format_pattern(text, delimiter, recursive: false, &block)
    escaped_delimiter = Regexp.escape(delimiter)
    # #{escaped_delimiter}{2} - double opening mark
    # (.+?) - any text (non-greedy)
    # #{escaped_delimiter}{2} - double closing mark
    pattern = /#{escaped_delimiter}{2}(.+?)#{escaped_delimiter}{2}/
    text.gsub(pattern) do
      content = $1
      # Recursively process nested formatting if enabled
      content = convert_nested(content) if recursive
      block.call(content)
    end
  end

  # Apply superscript/subscript formatting transformation
  # Single delimiter, can be used anywhere, but text must be continuous (no spaces)
  # Example: "2^32^" or "X~i~"
  #
  # @param text [String] The text to transform
  # @param delimiter [String] The formatting delimiter ('^' or '~')
  # @yield [content] Block that transforms the captured content
  # @yieldparam content [String] The text between the delimiters
  # @yieldreturn [String] The transformed content
  # @return [String] The text with formatting applied
  def continuous_format_pattern(text, delimiter, &block)
    escaped_delimiter = Regexp.escape(delimiter)
    # #{escaped_delimiter} - single opening mark
    # (\S+?) - continuous non-space text (no spaces allowed)
    # #{escaped_delimiter} - single closing mark
    # Note: Superscript/subscript don't support nesting in AsciiDoc
    pattern = /#{escaped_delimiter}(\S+?)#{escaped_delimiter}/
    text.gsub(pattern) { block.call($1) }
  end

  # Convert formatting within already-captured content.
  # This processes unconstrained (double delimiters) first, then constrained (single delimiters),
  # which is an order based on delimiter type, not on innermost-to-outermost nesting.
  def convert_nested(text)
    result = text.dup
    # Process unconstrained first (double delimiters)
    result = unconstrained_format_pattern(result, "*", recursive: true) { |content| "<b>#{content}</b>" }
    result = unconstrained_format_pattern(result, "_", recursive: true) { |content| "<i>#{content}</i>" }
    result = unconstrained_format_pattern(result, "`", recursive: true) { |content| "<code>#{content}</code>" }
    # Then process constrained (single delimiters)
    result = constrained_format_pattern(result, "*", recursive: true) { |content| "<b>#{content}</b>" }
    result = constrained_format_pattern(result, "_", recursive: true) { |content| "<i>#{content}</i>" }
    result = constrained_format_pattern(result, "`", recursive: true) { |content| "<code>#{content}</code>" }
    result
  end

  # Convert unconstrained bold, italics, and monospace notation.
  # For example, **foo**bar -> <b>foo</b>bar
  # Supports nesting when recursive: true
  def convert_unconstrained(text)
    text = unconstrained_format_pattern(text, "*", recursive: true) { |content| "<b>#{content}</b>" }
    text = unconstrained_format_pattern(text, "_", recursive: true) { |content| "<i>#{content}</i>" }
    unconstrained_format_pattern(text, "`", recursive: true) { |content| "<code>#{content}</code>" }
  end

  # Convert constrained bold, italics, and monospace notation.
  # For example, *foo* -> <b>foo</b>
  # Supports nesting when recursive: true
  def convert_constrained(text)
    text = constrained_format_pattern(text, "*", recursive: true) { |content| "<b>#{content}</b>" }
    text = constrained_format_pattern(text, "_", recursive: true) { |content| "<i>#{content}</i>" }
    constrained_format_pattern(text, "`", recursive: true) { |content| "<code>#{content}</code>" }
  end

  # Convert superscript notation: 2^32^ -> 2<sup>32</sup>
  #                               ^32^  -> <sup>32</sup>
  # Superscript uses continuous formatting (no spaces allowed in content)
  def convert_superscript(text)
    text = continuous_format_pattern(text, "^") { |content| "<sup>#{content}</sup>" }
  end

  # Convert subscript notation: X~i~ -> X<sub>i</sub>
  #                             ~i~  -> <sub>i</sub>
  # Subscript uses continuous formatting (no spaces allowed in content)
  def convert_subscript(text)
    text = continuous_format_pattern(text, "~") { |content| "<sub>#{content}</sub>" }
  end

  # Convert underline notation: [.underline]#text# -> <span class="underline">text</span>
  def convert_underline(text)
    text.gsub(/\[\.underline\]#([^#]+)#/, '<span class="underline">\1</span>')
  end

  def convert_extra_amp(text)
    # Sometimes the tags backend converts "&foo;" to "&amp;foo;". Convert it to "&foo;".
    # Note that the \w is equivalent to [a-zA-Z0-9_].
    text = text.gsub(/&amp;(\w+);/) do
      "&" + $1 + ";"
    end

    # Sometimes the tags backend converts "&#8800;" to "&amp;#8800;". Convert it to "&#8800;".
    text = text.gsub(/&amp;#([0-9]+);/) do
      "&#" + $1 + ";"
    end

    # And now handle the hexadecimal variant.
    text.gsub(/&amp;#x([0-9a-fA-F]+);/) do
      "&#x" + $1 + ";"
    end
  end

  # Convert unicode character entity names to numeric codes
  def convert_unicode_names(text)
    # Common HTML entity names to numeric codes
    entities = {
      'ge' => 8805,    # ≥ greater than or equal
      'le' => 8804,    # ≤ less than or equal
      'ne' => 8800,    # ≠ not equal
      'equiv' => 8801, # ≡ equivalent
      'lt' => LT_UNICODE_DECIMAL,      # < less than
      'gt' => GT_UNICODE_DECIMAL,      # > greater than
      'amp' => 38,     # & ampersand
      'quot' => 34,    # " quote
      'apos' => 39,    # ' apostrophe
      'nbsp' => 160,   # non-breaking space
      'times' => 215,  # × multiplication
      'divide' => 247, # ÷ division
      'plusmn' => 177, # ± plus-minus
      'deg' => 176,    # ° degree
      'micro' => 181,  # µ micro
      'para' => 182,   # ¶ paragraph
      'middot' => 183, # · middle dot
      'raquo' => 187,  # » right angle quote
      'laquo' => 171,  # « left angle quote
      'frac12' => 189, # ½ one half
      'frac14' => 188, # ¼ one quarter
      'frac34' => 190, # ¾ three quarters
    }

    # Convert known entities to their Unicode value.
    # The \w is equivalent to [a-zA-Z0-9_].
    text.gsub(/&(\w+);/) do
      entity_name = $1
      if entities.key?(entity_name)
        # Convert to numeric entity
        "&##{entities[entity_name]};"
      else
        # Leave unknown entities as-is
        "&#{entity_name};"
      end
    end
  end

  # Apply all format conversions (keeping numeric entities).
  def convert(text)
    result = text.dup
    result = convert_unconstrained(result)
    result = convert_constrained(result)
    result = convert_superscript(result)
    result = convert_subscript(result)
    result = convert_underline(result)
    result = convert_extra_amp(result)
    result = convert_unicode_names(result)
    result
  end
end

# Store normative rules in JSON output file
def output_json(filename, normative_rules_hash)
  fatal("Need String for filename but passed a #{filename.class}") unless filename.is_a?(String)
  fatal("Need Hash<String, Array> for normative_rules_hash but passed a #{normative_rules_hash.class}") unless normative_rules_hash.is_a?(Hash)

  # Serialize normative_rules_hash to JSON format String.
  # Shouldn't throw exceptions since we created the data being serialized.
  serialized_string = JSON.pretty_generate(normative_rules_hash)

  # Write serialized string to desired output file.
  begin
    File.write(filename, serialized_string)
  rescue Errno::ENOENT => e
    fatal("#{e.message}")
  rescue Errno::EACCES => e
    fatal("#{e.message}")
  rescue IOError => e
    fatal("#{e.message}")
  rescue ArgumentError => e
    fatal("#{e.message}")
  end
end

# Store normative rules in HTML output file.
def output_html(filename, defs, tags, tag_fname2url)
  fatal("Need String for filename but passed a #{filename.class}") unless filename.is_a?(String)
  fatal("Need NormativeRuleDefs for defs but passed a #{defs.class}") unless defs.is_a?(NormativeRuleDefs)
  fatal("Need NormativeTags for tags but passed a #{tags.class}") unless tags.is_a?(NormativeTags)
  fatal("Need Hash for tag_fname2url but passed a #{tag_fname2url.class}") unless tag_fname2url.is_a?(Hash)

  # Array of all chapter names
  chapter_names = []

  # Organize rules. Each hash key is chapter name. Each hash entry is an Array<NormativeRuleDef>.
  norm_rules_by_chapter_name = {}
  impldefs_by_chapter_name = {}

  # Create array of all impldef normative rules that will be sorted. Each array entry is a NormativeRuleDef.
  all_impldefs_a_z = []

  # Organize rules by field type. Each hash key is field type. Each hash entry is an Array<NormativeRuleDef>.
  defs_by_field_type = {}
  FIELD_TYPES.each do |ft|
    defs_by_field_type[ft] = []
  end

  # Go through all normative rule definitions and put into appropriate data structures.
  defs.norm_rule_defs.each do |d|
    chapter_names.append(d.chapter_name) if !chapter_names.include?(d.chapter_name)

    if norm_rules_by_chapter_name[d.chapter_name].nil?
      norm_rules_by_chapter_name[d.chapter_name] = []
    end
    norm_rules_by_chapter_name[d.chapter_name].append(d)

    if d.impldef
      all_impldefs_a_z.append(d)

      if impldefs_by_chapter_name[d.chapter_name].nil?
        impldefs_by_chapter_name[d.chapter_name] = []
      end
      impldefs_by_chapter_name[d.chapter_name].append(d)
    end

    defs_by_field_type[d.field_type].append(d) unless d.field_type.nil?
  end

  # Sort alphabetically for consistent output.
  chapter_names.sort!
  all_impldefs_a_z.sort_by! { |p| p.name }

  # Create list of all table names in order.
  table_names = []
  table_num=1
  chapter_names.each do |chapter_name|
    table_names.append("#{NORM_RULES_CH_TABLE_NAME_PREFIX}#{table_num}")
    table_num = table_num+1
  end
  table_names.append(IMPLDEFS_A_Z_TABLE_NAME) if all_impldefs_a_z.length > 0
  table_num=1
  chapter_names.each do |chapter_name|
    table_names.append("#{IMPLDEFS_CH_TABLE_NAME_PREFIX}#{table_num}") unless impldefs_by_chapter_name[chapter_name].nil?
    table_num = table_num+1
  end
  FIELD_TYPES.each do |ft|
    table_names.append("#{FIELD_TYPE_TABLE_NAME_PREFIX}#{ft}") if defs_by_field_type[ft].length > 0
  end

  File.open(filename, "w") do |f|
    html_head(f, table_names)
    f.puts(%Q{<body>})
    f.puts(%Q{  <div class="app">})

    html_sidebar(f, chapter_names, defs.norm_rule_defs, all_impldefs_a_z, impldefs_by_chapter_name, defs_by_field_type)
    f.puts(%Q{    <main>})
    f.puts(%Q{      <style>.grand-total-heading { font-size: 24px; font-weight: bold; }</style>})
    f.puts(%Q{      <h1 class="grand-total-heading">Grand total of #{defs.norm_rule_defs.length} normative rules including #{all_impldefs_a_z.length} implementation-defined behaviors</h1>})

    table_num=1
    chapter_names.each do |chapter_name|
      nr_defs = norm_rules_by_chapter_name[chapter_name]
      html_norm_rule_table(f, "#{NORM_RULES_CH_TABLE_NAME_PREFIX}#{table_num}", chapter_name, nr_defs, tags, tag_fname2url)
      table_num=table_num+1
    end

    if all_impldefs_a_z.length > 0
      html_impldef_table(f, IMPLDEFS_A_Z_TABLE_NAME, " (A-Z)", all_impldefs_a_z, tags, tag_fname2url)

      table_num=1
      chapter_names.each do |chapter_name|
        nr_defs = impldefs_by_chapter_name[chapter_name]
        unless nr_defs.nil?
          # XXX - Might need to change chapter name
          html_impldef_table(f, "#{IMPLDEFS_CH_TABLE_NAME_PREFIX}#{table_num}", " for Chapter #{chapter_name}", nr_defs, tags, tag_fname2url)
        end
        table_num=table_num+1
      end
    end

    FIELD_TYPES.each do |ft|
      nr_defs = defs_by_field_type[ft]
      if nr_defs.length > 0
        html_field_type_table(f, "#{FIELD_TYPE_TABLE_NAME_PREFIX}#{ft}", ft, nr_defs, tags, tag_fname2url)
      end
    end

    f.puts(%Q{    </main>})
    f.puts(%Q{  </div>})

    html_script(f)

    f.puts(%Q{</body>})
    f.puts(%Q{</html>})
  end
end

def html_head(f, table_names)
  fatal("Need File for f but passed a #{f.class}") unless f.is_a?(File)
  fatal("Need Array for table_names but passed a #{table_names.class}") unless table_names.is_a?(Array)

  f.puts(<<~HTML
    <!doctype html>
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
        .sidebar h2{margin:0 0 12px;font-size:18px}
        .nav{display:flex;flex-direction:column;gap:2px}
        .nav a{
          display:block;
          font-size: 14px;
          padding:6px 10px;
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
HTML
  )

  table_names.each do |table_name|
    f.puts("    ##{table_name} > table { table-layout: fixed; width: 100% }")
  end

  f.puts(<<~HTML

        /* Responsive */
        @media (max-width:820px){
          .app{grid-template-columns:1fr}
          .sidebar{position:relative;height:auto;display:flex;gap:8px;overflow:auto;border-right:none;border-bottom:1px solid rgba(15,23,42,0.04)}
          main{padding:18px}
        }
      </style>
    </head>
HTML
  )
end

def html_sidebar(f, chapter_names, nrs, all_impldefs_a_z, impldefs_by_chapter_name, defs_by_field_type)
  fatal("Need File for f but passed a #{f.class}") unless f.is_a?(File)
  fatal("Need Array for chapter_names but passed a #{chapter_names.class}") unless chapter_names.is_a?(Array)
  fatal("Need Array<NormativeRuleDef> for nrs but passed a #{nrs.class}") unless nrs.is_a?(Array)
  fatal("Need Array<NormativeRuleDef> for all_impldefs_a_z but passed a #{all_impldefs_a_z.class}") unless all_impldefs_a_z.is_a?(Array)
  fatal("Need Hash for impldefs_by_chapter_name but passed a #{impldefs_by_chapter_name.class}") unless impldefs_by_chapter_name.is_a?(Hash)
  fatal("Need Hash for defs_by_field_type but passed a #{defs_by_field_type.class}") unless defs_by_field_type.is_a?(Hash)

  # Use Ruby $Q{...} instead of double quotes to allow freely mixing embedded double quotes and Ruby's #{} operator.
  f.puts("")
  f.puts(%Q{  <aside class="sidebar">})
  f.puts(%Q{    <h2>All Normative Rules</h2>})
  f.puts(%Q{    <nav class="nav" id="nav-chapters">})

  table_num=1
  chapter_names.each do |chapter_name|
    f.puts(%Q{      <a href="##{NORM_RULES_CH_TABLE_NAME_PREFIX}#{table_num}" data-target="#{NORM_RULES_CH_TABLE_NAME_PREFIX}#{table_num}">#{chapter_name}</a>})
    table_num = table_num+1
  end

  if all_impldefs_a_z.length > 0
    f.puts(%Q{    </nav>})
    f.puts(%Q{    <h2>Implementation-Defined Behaviors</h2>})
    f.puts(%Q{    <nav class="nav" id="nav-impldefs-a-z">})
    f.puts(%Q{      <a href="##{IMPLDEFS_A_Z_TABLE_NAME}" data-target="#{IMPLDEFS_A_Z_TABLE_NAME}">A-Z</a>})

    table_num=1
    chapter_names.each do |chapter_name|
      unless impldefs_by_chapter_name[chapter_name].nil?
        f.puts(%Q{      <a href="##{IMPLDEFS_CH_TABLE_NAME_PREFIX}#{table_num}" data-target="#{IMPLDEFS_CH_TABLE_NAME_PREFIX}#{table_num}">#{chapter_name}</a>})
      end
      table_num = table_num+1
    end

    f.puts(%Q{    </nav>})
  end

  total_for_all_field_types = 0
  FIELD_TYPES.each do |ft|
    total_for_all_field_types += defs_by_field_type[ft].length unless defs_by_field_type[ft].nil?
  end

  if total_for_all_field_types > 0
    f.puts(%Q{    <h2>WARL & WLRL</h2>})

    FIELD_TYPES.each do |ft|
      count = defs_by_field_type[ft].length unless defs_by_field_type[ft].nil?
      unless count == 0
        f.puts(%Q{    <nav class="nav" id="nav-field-type-#{ft}">})
        f.puts(%Q{      <a href="##{FIELD_TYPE_TABLE_NAME_PREFIX}#{ft}" data-target="#{FIELD_TYPE_TABLE_NAME_PREFIX}#{ft}">#{ft} field#{count == 1 ? "" : "s"} A-Z</a>})
        f.puts(%Q{    </nav>})
      end
    end
  end

  f.puts('  </aside>')
end

def html_norm_rule_table(f, table_name, chapter_name, nr_defs, tags, tag_fname2url)
  fatal("Need File for f but passed a #{f.class}") unless f.is_a?(File)
  fatal("Need String for table_name but passed a #{table_name.class}") unless table_name.is_a?(String)
  fatal("Need String for chapter_name but passed a #{chapter_name.class}") unless chapter_name.is_a?(String)
  fatal("Need Array for nr_defs but passed a #{nr_defs.class}") unless nr_defs.is_a?(Array)
  fatal("Need NormativeTags for tags but passed a #{tags.class}") unless tags.is_a?(NormativeTags)
  fatal("Need Hash for tag_fname2url but passed a #{tag_fname2url.class}") unless tag_fname2url.is_a?(Hash)

  num_rules = nr_defs.length
  num_params = count_impldefs(nr_defs)

  num_rules_str = "#{num_rules} normative rule#{num_rules == 1 ? "" : "s"}"

  includes_str = "#{num_params} implementation-defined behavior#{num_params == 1 ? "" : "s"}"

  num_field_types = {}
  FIELD_TYPES.each do |ft|
    num_field_types[ft] = count_field_types(nr_defs, ft)
  end

  FIELD_TYPES.each do |ft|
    includes_str << ", #{num_field_types[ft]} #{ft} field#{num_field_types[ft] == 1 ? "" : "s"}" if num_field_types[ft] > 0
  end

  html_table_header(f, table_name, "Chapter #{chapter_name} (#{num_rules_str} including #{includes_str})")
  nr_defs.each do |nr|
    html_norm_rule_table_row(f, nr, tags, tag_fname2url)
  end
  html_table_footer(f)
end

def html_impldef_table(f, table_name, caption_suffix, nr_defs, tags, tag_fname2url)
  fatal("Need File for f but passed a #{f.class}") unless f.is_a?(File)
  fatal("Need String for table_name but passed a #{table_name.class}") unless table_name.is_a?(String)
  fatal("Need String for caption_suffix but passed a #{caption_suffix.class}") unless caption_suffix.is_a?(String)
  fatal("Need Array for nr_defs but passed a #{nr_defs.class}") unless nr_defs.is_a?(Array)
  fatal("Need NormativeTags for tags but passed a #{tags.class}") unless tags.is_a?(NormativeTags)
  fatal("Need Hash for tag_fname2url but passed a #{tag_fname2url.class}") unless tag_fname2url.is_a?(Hash)

  html_table_header(f, table_name, "All #{nr_defs.length} Implementation-Defined Behaviors#{caption_suffix}")
  nr_defs.each do |nr|
    html_impldef_table_row(f, nr, tags, tag_fname2url)
  end
  html_table_footer(f)
end

def html_field_type_table(f, table_name, ft, nr_defs, tags, tag_fname2url)
  fatal("Need File for f but passed a #{f.class}") unless f.is_a?(File)
  fatal("Need String for table_name but passed a #{table_name.class}") unless table_name.is_a?(String)
  fatal("Need String for ft but passed a #{ft.class}") unless ft.is_a?(String)
  fatal("Need Array for nr_defs but passed a #{nr_defs.class}") unless nr_defs.is_a?(Array)
  fatal("Need NormativeTags for tags but passed a #{tags.class}") unless tags.is_a?(NormativeTags)
  fatal("Need Hash for tag_fname2url but passed a #{tag_fname2url.class}") unless tag_fname2url.is_a?(Hash)

  html_table_header(f, table_name, "#{nr_defs.length} #{ft} field#{nr_defs.length == 1 ? "" : "s"}")
  nr_defs.each do |nr|
    html_field_type_table_row(f, nr, tags, tag_fname2url)
  end
  html_table_footer(f)
end

def html_table_header(f, table_name, table_caption)
  fatal("Need File for f but passed a #{f.class}") unless f.is_a?(File)
  fatal("Need String for table_name but passed a #{table_name.class}") unless table_name.is_a?(String)
  fatal("Need String for table_caption but passed a #{table_caption.class}") unless table_caption.is_a?(String)

  f.puts("")
  f.puts(%Q{      <section id="#{table_name}" class="section">})
  f.puts(%Q{        <table>})
  f.puts(%Q{          <caption class="sticky-caption">#{table_caption}</caption>})
  f.puts(%Q{          <colgroup>})
  f.puts(%Q{            <col class="col-name">})
  f.puts(%Q{            <col class="col-description">})
  f.puts(%Q{            <col class="col-location">})
  f.puts(%Q{          </colgroup>})
  f.puts(%Q{          <thead>})
  f.puts(%Q{            <tr><th>Rule Name</th><th>Rule Description</th><th>Origin of Description</th></tr>})
  f.puts(%Q{          </thead>})
  f.puts(%Q{          <tbody>})
end

def html_norm_rule_table_row(f, nr, tags, tag_fname2url)
  fatal("Need File for f but passed a #{f.class}") unless f.is_a?(File)
  fatal("Need NormativeRuleDef for nr but passed a #{nr.class}") unless nr.is_a?(NormativeRuleDef)
  fatal("Need NormativeTags for tags but passed a #{tags.class}") unless tags.is_a?(NormativeTags)
  fatal("Need Hash for tag_fname2url but passed a #{tag_fname2url.class}") unless tag_fname2url.is_a?(Hash)

  html_table_row(f, nr, true, false, false,tags, tag_fname2url)
end

def html_impldef_table_row(f, nr, tags, tag_fname2url)
  fatal("Need File for f but passed a #{f.class}") unless f.is_a?(File)
  fatal("Need NormativeRuleDef for nr but passed a #{nr.class}") unless nr.is_a?(NormativeRuleDef)
  fatal("Need NormativeTags for tags but passed a #{tags.class}") unless tags.is_a?(NormativeTags)
  fatal("Need Hash for tag_fname2url but passed a #{tag_fname2url.class}") unless tag_fname2url.is_a?(Hash)

  html_table_row(f, nr, false, true, false, tags, tag_fname2url)
end

def html_field_type_table_row(f, nr, tags, tag_fname2url)
  fatal("Need File for f but passed a #{f.class}") unless f.is_a?(File)
  fatal("Need NormativeRuleDef for nr but passed a #{nr.class}") unless nr.is_a?(NormativeRuleDef)
  fatal("Need NormativeTags for tags but passed a #{tags.class}") unless tags.is_a?(NormativeTags)
  fatal("Need Hash for tag_fname2url but passed a #{tag_fname2url.class}") unless tag_fname2url.is_a?(Hash)

  html_table_row(f, nr, false, false, true, tags, tag_fname2url)
end

def html_table_row(f, nr, name_is_anchor, omit_kind, omit_field_type, tags, tag_fname2url)
  fatal("Need File for f but passed a #{f.class}") unless f.is_a?(File)
  fatal("Need NormativeRuleDef for nr but passed a #{nr.class}") unless nr.is_a?(NormativeRuleDef)
  fatal("Need Boolean for name_is_anchor but passed a #{name_is_anchor.class}") unless name_is_anchor == true || name_is_anchor == false
  fatal("Need Boolean for omit_kind but passed a #{omit_kind.class}") unless omit_kind == true || omit_kind == false
  fatal("Need Boolean for omit_field_type but passed a #{omit_field_type.class}") unless omit_field_type == true || omit_field_type == false
  fatal("Need NormativeTags for tags but passed a #{tags.class}") unless tags.is_a?(NormativeTags)
  fatal("Need Hash for tag_fname2url but passed a #{tag_fname2url.class}") unless tag_fname2url.is_a?(Hash)

  name_row_span =
    (nr.summary.nil? ? 0 : 1) +
    (nr.note.nil? ? 0 : 1) +
    (nr.clarification_link.nil? ? 0 : 1) +
    (nr.description.nil? ? 0 : 1) +
    (omit_kind || nr.kind.nil? ? 0 : 1) +
    (nr.instances.empty? ? 0 : 1) +
    (omit_field_type || nr.field_type.nil? ? 0 : 1) +
    nr.tag_refs.length

  # Tracks if this is the first row for the normative rule.
  # Required because normative rule name spans multiple rows so it is only provided on the first row.
  # Each subsequent row sets first_row to false after omitting the opening <tr> tag (which is only needed for rows after the first).
  first_row = true

  # Output the normative rule name cell with rowspan.
  f.puts(%Q{            <tr>})
  if name_is_anchor
    f.puts(%Q{              <td rowspan=#{name_row_span} id="#{nr.name}">#{nr.name}</td>})
  else
    f.puts(%Q{              <td rowspan=#{name_row_span}><a href="##{nr.name}">#{nr.name}</a></td>})
  end

  unless nr.summary.nil?
    text = convert_def_text_to_html(nr.summary)

    f.puts(%Q{            <tr>}) unless first_row
    f.puts(%Q{              <td>#{text}</td>})
    f.puts(%Q{              <td>Rule's "summary" property</td>})
    f.puts(%Q{            </tr>})
    first_row = false
  end

  unless nr.note.nil?
    text = convert_def_text_to_html(nr.note)

    f.puts(%Q{            <tr>}) unless first_row
    f.puts(%Q{              <td>#{text}</td>})
    f.puts(%Q{              <td>Rule's "note" property</td>})
    f.puts(%Q{            </tr>})
    first_row = false
  end

  unless nr.description.nil?
    text = convert_def_text_to_html(nr.description)

    f.puts(%Q{            <tr>}) unless first_row
    f.puts(%Q{              <td>#{text}</td>})
    f.puts(%Q{              <td>Rule's "description" property</td>})
    f.puts(%Q{            </tr>})
    first_row = false
  end

  unless omit_kind || nr.kind.nil?
    f.puts(%Q{            <tr>}) unless first_row
    f.puts(%Q{              <td>#{nr.kind}</td>})
    f.puts(%Q{              <td>Rule's "kind" property</td>})
    f.puts(%Q{            </tr>})
    first_row = false
  end

  unless nr.instances.empty?
    if nr.instances.size == 1
      instances_str = nr.instances[0]
      rule_name = "instance"
    else
      instances_str = "[" + nr.instances.join(', ') + "]"
      rule_name = "instances"
    end
    f.puts(%Q{            <tr>}) unless first_row
    f.puts(%Q{              <td>#{instances_str}</td>})
    f.puts(%Q{              <td>Rule's "#{rule_name}" property</td>})
    f.puts(%Q{            </tr>})
    first_row = false
  end

  unless omit_field_type || nr.field_type.nil?
    f.puts(%Q{              <td>#{nr.field_type}</td>})

    f.puts(%Q{              <td>Rule's "field_type" property</td>})
    f.puts(%Q{            </tr>})
    first_row = false
  end

  nr.tag_refs.each do |tag_ref|
    tag = tags.get_tag(tag_ref.name)
    fatal("Normative rule #{nr.name} defined in file #{nr.def_filename} references non-existent tag #{tag_ref.name}") if tag.nil?

    target_html_fname = tag_fname2url[tag.tag_filename]
    fatal("No fname tag to HTML mapping (-tag2url cmd line arg) for tag fname #{tag.tag_filename} for tag name #{tag.name}") if target_html_fname.nil?

    tag_text = convert_newlines_to_html(convert_tags_tables_to_html(Adoc2HTML::convert(tag.text)))

    # Convert adoc links to HTML links.
    # Can assume that the link is to the same HTML standards document as the
    # tag text that it is found in because these kind of adoc links only link within their document.
    tag_text = convert_adoc_links_to_html(tag_text, target_html_fname)

    if tag_text.strip.empty?
      tag_text = "(No text available)"
    end

    tag_text = ("[CONTEXT] " + tag_text) if tag_ref.context?

    tag_link = tag2html_link(tag_ref.name, tag_ref.name, target_html_fname)

    f.puts(%Q{            <tr>}) unless first_row
    f.puts(%Q{              <td>#{tag_text}</td>})
    f.puts(%Q{              <td>#{tag_link}</td>})
    f.puts(%Q{            </tr>})
    first_row = false
  end

  unless nr.clarification_link.nil?
    # The clarification text can only exist if the clarification link also exists.
    if nr.clarification_text.nil?
      text = "(No clarification text available)"
    else
      text = convert_def_text_to_html(nr.clarification_text)
    end

    link = %Q{<a href="#{nr.clarification_link}">GitHub Issue</a>}

    f.puts(%Q{            <tr>}) unless first_row
    f.puts(%Q{              <td>[CLARIFICATION] #{text}</td>})
    f.puts(%Q{              <td>#{link}</td>})
    f.puts(%Q{            </tr>})
    first_row = false
  end
end
def html_table_footer(f)
  fatal("Need File for f but passed a #{f.class}") unless f.is_a?(File)

  f.puts(%Q{          </tbody>})
  f.puts(%Q{        </table>})
  f.puts(%Q{      </section>})
end

# If no target_html_fname is provided, assumes anchor is in same HTML file as link (i.e., an HTML "fragment" link).
def tag2html_link(tag_ref, link_text, target_html_fname = nil)
  fatal("Expected String for tag_ref but was passed a #{tag_ref.class}") unless tag_ref.is_a?(String)
  fatal("Expected String for link_text but was passed a #{link_text.class}") unless link_text.is_a?(String)
  unless target_html_fname.nil?
    fatal("Expected String for target_html_fname but was passed a #{target_html_fname.class}") unless target_html_fname.is_a?(String)
  end

  target_html_fname = "" if target_html_fname.nil?

  return %Q{<a href="#{target_html_fname}##{tag_ref}">#{link_text}</a>}
end

def html_script(f)
  fatal("Need File for f but passed a #{f.class}") unless f.is_a?(File)

  f.puts(<<~HTML
    <script>
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
HTML
  )
end

# Cleanup the tag text to be suitably displayed.
def limit_table_rows(text)
  raise ArgumentError, "Expected String for text but was passed a #{text.class}" unless text.is_a?(String)

  # This is the detection pattern for an entire table being tagged from the "tags.rb" AsciiDoctor backend.
  if text.end_with?("\n===")
    # Limit table size displayed.
    truncate_after_newlines(text, MAX_TABLE_ROWS)
  else
    text
  end
end

def truncate_after_newlines(text, max_newlines)
  # Split the string into lines
  lines = text.split("\n")

  # Take only up to the allowed number of lines
  truncated_lines = lines.first(max_newlines + 1)

  # Join them back together with newline characters
  truncated_text = truncated_lines.join("\n")

  # If there were more lines than allowed, indicate truncation.
  truncated_text += "\n..." if lines.size > max_newlines + 1

  truncated_text
end

def count_impldefs(nrs)
  raise ArgumentError, "Need Array<NormativeRuleDef> for nrs but passed a #{nrs.class}" unless nrs.is_a?(Array)

  count = 0

  nrs.each do |nr|
    count += 1 if nr.impldef
  end

  return count
end

def count_field_types(nrs, field_type)
  raise ArgumentError, "Need Array<NormativeRuleDef> for nrs but passed a #{nrs.class}" unless nrs.is_a?(Array)
  raise ArgumentError, "Need String for field_type but passed a #{field_type.class}" unless field_type.is_a?(String)

  count = 0

  nrs.each do |nr|
    count += 1 if nr.field_type == field_type
  end

  return count
end

# Convert all the various definition text formats to HTML.
def convert_def_text_to_html(text)
  raise ArgumentError, "Expected String for text but was passed a #{text.class}" unless text.is_a?(String)

  text = Adoc2HTML::convert(text)
  text = convert_tags_tables_to_html(text)
  text = convert_newlines_to_html(text)
  text = convert_adoc_links_to_html(text)

  return text
end

# Convert the tagged text containing entire tables. Uses format created by "tags" Asciidoctor backend.
#
# Possible formats:
#
#   Without heading:
#
#     ===
#     ABC | DEF¶
#     GHI |JKL
#     ===
#
#     Actual string from tags: "===\nABC | DEF¶GHI |JKL\n==="
#
#   With heading:
#
#     H1 | H2
#     ===
#     GHI | JKL
#     ===
#
#     Actual string from tags: "H1 | H2\n===\nGHI | JKL\n==="
#
#   Newlines in table cells:
#   (Creates table with just one row. Newlines after each cell give the appearance of multiple table rows.)
#
#     ColA|ColB
#     ===
#     0
#     1|Off
#     On
#     ===
#
#     Actual string from tags: "ColA|ColB\n===\n0\n1|Off\nOn\n==="

def convert_tags_tables_to_html(text)
  raise ArgumentError, "Expected String for text but was passed a #{text.class}" unless text.is_a?(String)

  text.gsub(/(.*?)===\n(.+)\n===/m) do
    # Found a "tags" formatted table
    heading = $1.chomp          # Remove potential trailing newline
    rows = $2.split("¶")        # Split into array of rows. Using "paragraph" symbol since adoc can have newlines in table cells.

    ret = "<table>".dup    # Start html table

    # Add heading if present
    heading_cells = extract_tags_table_cells(heading)
    unless heading_cells.empty?
      ret << "<thead>"
      ret << "<tr>"
      ret << heading_cells.map { |cell| "<th>#{cell}</th>" }.join("")
      ret << "</tr>"
      ret << "</thead>"
    end

    # Add each row
    ret << "<tbody>"
    rows.each_with_index do |row,index|
      if index < MAX_TABLE_ROWS
        ret << "<tr>"
        row_cells = extract_tags_table_cells(row)
        ret << row_cells.map { |cell| "<td>#{cell}</td>" }.join("")
        ret << "</tr>"
      elsif index == MAX_TABLE_ROWS
        ret << "<tr>"
        row_cells = extract_tags_table_cells(row)
        ret << row_cells.map { |cell| "<td>...</td>" }.join("")
        ret << "</tr>"
      end
    end

    ret << "</tbody>"
    ret << "</table>"    # End html table
  end
end

# Return array of table columns from one row/header of a table.
# Returns empty array if row is nil or the empty string.
def extract_tags_table_cells(row)
  raise ArgumentError, "Expected String for row but was passed a #{row.class}" unless row.is_a?(String)

  return [] if row.nil? || row.empty?

  # Split row fields with pipe symbol. The -1 passed to split ensures trailing null fields are not suppressed.
  #
  # Examples:
  #   "H1 | H2" => ["H1", "H2"]
  #   "|" => ["", ""]
  #   "|A|B" => ["", "A", "B"]
  #   "||C" => ["", "", "C"]
  row.split('|', -1).map(&:strip)
end

# Convert newlines to <br>.
def convert_newlines_to_html(text)
  raise ArgumentError, "Expected String for text but was passed a #{text.class}" unless text.is_a?(String)

  text.gsub(/\n/, '<br>')
end

# Convert adoc links to HTML links.
#
# Supported adoc link formats:
#   <<link>>
#   <<link,custom text>>
#
# If target_html_fname is not provided, link will assume anchor is in the same HTML file as the link.
def convert_adoc_links_to_html(text, target_html_fname = nil)
  raise ArgumentError, "Passed class #{text.class} for text but require String" unless text.is_a?(String)
  unless target_html_fname.nil?
    raise ArgumentError, "Passed class #{target_html_fname.class} for target_html_fname but require String" unless target_html_fname.is_a?(String)
  end

  # Note that I'm using the non-greedy regular expression (? after +) otherwise the regular expression
  # will return multiple <<link>> in the same text as one.
  text.gsub(/(<<|#{LT_UNICODE_STR}#{LT_UNICODE_STR})(.+?)(>>|#{GT_UNICODE_STR}#{GT_UNICODE_STR})/) do
    # Look to see if custom text has been provided.
    split_texts = $2.split(",").map(&:strip)

    if split_texts.length == 0
      fail("Hyperlink '#{$2}' is empty")
    elsif split_texts.length == 1
      tag2html_link(split_texts[0], split_texts[0], target_html_fname)
    elsif split_texts.length == 2
      tag2html_link(split_texts[0], split_texts[1], target_html_fname)
    else
      fail("Hyperlink '#{$2}' contains too many commas")
    end
  end
end

#main()

info("Passed command-line: #{ARGV.join(' ')}")

def_fnames, tag_fnames, tag_fname2url, output_fname, output_format, warn_if_tags_no_rules = parse_argv()

info("Normative rule definition filenames = #{def_fnames}")
info("Normative tag filenames = #{tag_fnames}")
tag_fname2url.each do |tag_fname, url|
  info("Normative tag file #{tag_fname} links to URL #{url}")
end
info("Output filename = #{output_fname}")
info("Output format = #{output_format}")

defs = load_definitions(def_fnames)
tags = load_tags(tag_fnames)
validate_defs_and_tags(defs, tags, warn_if_tags_no_rules)

info("Storing #{defs.norm_rule_defs.count} normative rules into file #{output_fname}")
info("Includes #{count_impldefs(defs.norm_rule_defs)} implementation-defined behavior normative rules")
FIELD_TYPES.each do |ft|
  count = count_field_types(defs.norm_rule_defs, ft)
  info("Includes #{count} #{ft} normative rule#{count == 1 ? "" : "s"  }")
end

case output_format
when "json"
  normative_rules_hash = create_normative_rules_hash(defs, tags, tag_fname2url)
  output_json(output_fname, normative_rules_hash)
when "html"
  output_html(output_fname, defs, tags, tag_fname2url)
else
  raise "Unknown output_format of #{output_format}"
end

exit 0

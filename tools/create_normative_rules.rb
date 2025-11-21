# frozen_string_literal: true

require "json"
require "yaml"
require "write_xlsx"

PN = "create_normative_rules.rb"

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

class NormativeRuleDef
  attr_reader :name                   # Normative rule name, String (mandatory)
  attr_reader :def_filename           # String (mandatory)
  attr_reader :chapter_name           # String (mandatory)
  attr_reader :summary                # String (optional - a few words)
  attr_reader :description            # String (optional - sentence, paragraph, or more)
  attr_reader :kind                   # String (optional, can be nil)
  attr_reader :instances              # Array<String> (optional - can be empty)
  attr_reader :tag_refs               # Array<String> (optional - can be empty)

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

    @description = data["description"]
    unless @description.nil?
      fatal("Provided #{@description.class} class for description in normative rule #{name} but need a String") unless @description.is_a?(String)
    end

    @kind = data["kind"]
    unless @kind.nil?
      fatal("Provided #{@kind.class} class for kind in normative rule #{name} but need a String") unless @kind.is_a?(String)
      check_allowed_types(@kind, @name, nil)
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
    @tag_refs.append(data["tag"]) unless data["tag"].nil?
    data["tags"]&.each do |tag_name|
      @tag_refs.append(tag_name)
    end
  end
end # class NormativeRuleDef

# Create fatal if kind not recognized. The name is nil if this is called in the normative rule definition.
def check_allowed_types(kind, nr_name, name)
  allowed_types = ["extension", "instruction", "csr", "csr_field", "parameter"]

  unless allowed_types.include?(kind)
    tag_str = name.nil? ? "" : "tag #{name} in "
    allowed_str = allowed_types.join(",")
    fatal("Don't recognize kind '#{kind}' for #{tag_str}normative rule #{nr_name}\n#{PN}: Allowed types are: #{allowed_str}")
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
  puts "  -x                      Set output format to XLSX"
  puts "  -a                      Set output format to AsciiDoc"
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
  warn_if_tags_no_rules = 0

  i = 0
  while i < ARGV.count
    arg = ARGV[i]
    case arg
    when "--help"
      usage 0
    when "-j"
      output_format = "json"
    when "-x"
      output_format = "xlsx"
    when "-a"
      output_format = "adoc"
    when "-h"
      output_format = "html"
    when "-w"
      warn_if_tags_no_rules = 1
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

  if (output_format == "json" || output_format == "adoc" || output_format == "html") && tag_fname2url.empty?
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
    hash["instances"] = d.instances unless d.instances.empty?
    hash["summary"] = d.summary unless d.summary.nil?
    hash["description"] = d.description unless d.description.nil?

    unless d.tag_refs.nil?
      hash["tags"] = []
    end

    # Add tag entries
    unless d.tag_refs.nil?
      d.tag_refs.each do |tag_ref|
        # Lookup tag
        tag = tags.get_tag(tag_ref)

        fatal("Normative rule #{d.name} defined in file #{d.def_filename} references non-existent tag #{tag_ref}") if tag.nil?

        url = tag_fname2url[tag.tag_filename]
        fatal("No fname tag to URL mapping (-tag2url cmd line arg) for tag fname #{tag.tag_filename} for tag name #{tag.name}") if url.nil?

        resolved_tag = {
          "name" => tag.name,
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
  unref_cnt = 0
  referenced_tags = {}    # Key is tag name and value is any non-nil value
  rule_name_lengths = []
  tag_name_lengths = []

  # Detect missing tags and unreferenced tags.
  defs.norm_rule_defs.each do |d|
    unless d.tag_refs.nil?
      d.tag_refs.each do |tag_ref|
        # Lookup tag by its name
        tag = tags.get_tag(tag_ref)

        if tag.nil?
          missing_tag_cnt = missing_tag_cnt + 1
          error("Normative rule #{d.name} defined in file #{d.def_filename} references non-existent tag #{tag_ref}")
        else
          referenced_tags[tag.name] = 1 # Any non-nil value
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
      if warn_if_tags_no_rules == 1
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

  if unref_cnt > 0
    msg = "#{unref_cnt} tag#{unref_cnt == 1 ? "" : "s"} have no normative rules referencing them"
    if warn_if_tags_no_rules == 1
      info(msg)
    else
      error(msg)
    end
  end

  fatal("Exiting due to errors") if ((missing_tag_cnt > 0) || ((unref_cnt > 0) && (warn_if_tags_no_rules == 0)))

  # Display counts of name lengths.
  #info("")
  #info("Normative rule name lengths:")
  #rule_name_lengths.each_with_index do |count, index|
  #  info("  rule_name_length[#{index}] => #{count}")
  #end

  # Display counts of name lengths.
  #info("")
  #info("Tag name lengths:")
  #tag_name_lengths.each_with_index do |count, index|
  #  info("  tag_name_length[#{index}] => #{count}")
  #end
end

module Adoc2HTML
  extend self

  # Convert superscript notation: 2^32^ -> 2<sup>32</sup>
  # Uses non-greedy matching and allows various content types
  def convert_superscript(text)
    # Match word followed by ^content^, where content doesn't contain ^
    text.gsub(/(\w+)\^([^\^]+?)\^/) do
      "#{$1}<sup>#{$2}</sup>"
    end
  end

  # Convert subscript notation: X~i~ -> X<sub>i</sub>
  # Uses non-greedy matching and allows various content types
  def convert_subscript(text)
    # Match word followed by ~content~, where content doesn't contain ~
    text.gsub(/(\w+)~([^~]+?)~/) do
      "#{$1}<sub>#{$2}</sub>"
    end
  end

  # Convert underline notation: [.underline]#text# -> <span class="underline">text</span>
  def convert_underline(text)
    text.gsub(/\[\.underline\]#([^#]+)#/, '<span class="underline">\1</span>')
  end

  # Convert unicode character entity names to numeric codes
  # Handles tags backend converting "&" in the adoc to "&amp;".
  def convert_unicode_names(text)
    # Common HTML entity names to numeric codes
    entities = {
      'ge' => 8805,    # ≥ greater than or equal
      'le' => 8804,    # ≤ less than or equal
      'ne' => 8800,    # ≠ not equal
      'equiv' => 8801, # ≡ equivalent
      'lt' => 60,      # < less than
      'gt' => 62,      # > greater than
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

    text.gsub(/&amp;(\w+);/) do
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

  # Convert numeric unicode entities to proper unicode numbers. Handle both hex and decimal formats.
  # Handles tags backend converting "&" in the adoc to "&amp;". That's all this really does.
  def convert_unicode_numbers(text)
    text.gsub(/&amp;#x(\h+);/) do
      # Hexadecimal case
      "&#x#{$1};"
    end.gsub(/&amp;#(\d+);/) do
      # Decimal case
      "&##{$1};"
    end
  end

  # Apply all inline format conversions (keeping numeric entities)
  def convert_all(text)
    result = text.dup
    result = convert_superscript(result)
    result = convert_subscript(result)
    result = convert_underline(result)
    result = convert_unicode_names(result)
    result = convert_unicode_numbers(result)
    result
  end
end

# Store normative rules in JSON output file
def output_json(filename, normative_rules_hash)
  fatal("Need String for filename but passed a #{filename.class}") unless filename.is_a?(String)
  fatal("Need Hash<String, Array> for normative_rules_hash but passed a #{normative_rules_hash.class}") unless normative_rules_hash.is_a?(Hash)

  nr_array = normative_rules_hash["normative_rules"]
  raise "Expecting an array for key normative_rules but got an #{nr_array.class}" unless nr_array.is_a?(Array)

  info("Storing #{nr_array.count} normative rules into file #{filename}")

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

# Store normative rule defs in XLSX output file
def output_xlsx(filename, defs, tags)
  fatal("Need String for filename but passed a #{filename.class}") unless filename.is_a?(String)
  fatal("Need NormativeRuleDefs for defs but passed a #{defs.class}") unless defs.is_a?(NormativeRuleDefs)
  fatal("Need NormativeTags for tags but passed a #{tags.class}") unless tags.is_a?(NormativeTags)

  info("Storing #{defs.norm_rule_defs.count} normative rules into file #{filename}")

  # Create a new Excel workbook
  info("Creating Excel workbook #{filename}")
  workbook = WriteXLSX.new(filename)

  # Add a worksheet
  worksheet = workbook.add_worksheet("Normative Rules")

  # Define format for cells that want wrapping on.
  wrap_format = workbook.add_format()
  wrap_format.set_text_wrap()

  # Define table column names
  table_props = {
    columns: [
      { header: "Chapter Name" },
      { header: "Rule Name" },
      { header: "Rule Description" },
      { header: "Origin of Description" },
      { header: "Kind" },
      { header: "Instances" }
    ]
  }

  # Add normative rules in rows. One row for each tag if multiple tags.
  row_num = 1
  defs.norm_rule_defs.each do |d|
    worksheet.write_string(row_num, 0, d.chapter_name)
    worksheet.write_string(row_num, 1, d.name, wrap_format)

    rule_defs = []
    rule_def_sources = []

    unless d.summary.nil?
      rule_defs.append(d.summary.chomp)
      rule_def_sources.append("Rule Summary")
    end

    unless d.description.nil?
      rule_defs.append(d.description.chomp)
      rule_def_sources.append("Rule Description")
    end

    tag_sources = []
    d.tag_refs.each do |tag_ref|
      tag = tags.get_tag(tag_ref)
      fatal("Normative rule #{d.name} defined in file #{d.def_filename} references non-existent tag #{tag_ref}") if tag.nil?
      rule_defs.append(handle_tables(tag.text).chomp)
      tag_sources.append('"' + tag.name + '"')
    end
    rule_def_sources.append('[' + tag_sources.join(', ') + ']') unless tag_sources.empty?

    worksheet.write_string(row_num, 2, rule_defs.join("\n"), wrap_format) unless rule_defs.empty?
    worksheet.write_string(row_num, 3, rule_def_sources.join(", "), wrap_format) unless rule_def_sources.empty?
    worksheet.write_string(row_num, 4, d.kind) unless d.kind.nil?
    worksheet.write_string(row_num, 5, d.instances.join(', ')) unless d.instances.empty?

    row_num += 1
  end

  num_rows = row_num - 1

  # Make into a table. Assume columns A to F.
  worksheet.add_table("A1:F#{num_rows}", table_props)

  # Set column widths to hold data width.
  worksheet.autofit

  # Override autofit for really wide columns
  worksheet.set_column(1, 1, 20) # name column
  worksheet.set_column(2, 2, 80) # definition column
  worksheet.set_column(3, 3, 40) # definition sources column

  workbook.close
end

# Store normative rules in AsciiDoc output file.
def output_adoc(filename, defs, tags, tag_fname2url)
  fatal("Need String for filename but passed a #{filename.class}") unless filename.is_a?(String)
  fatal("Need NormativeRuleDefs for defs but passed a #{defs.class}") unless defs.is_a?(NormativeRuleDefs)
  fatal("Need NormativeTags for tags but passed a #{tags.class}") unless tags.is_a?(NormativeTags)
  fatal("Need Hash for tag_fname2url but passed a #{tag_fname2url.class}") unless tag_fname2url.is_a?(Hash)

  info("Storing #{defs.norm_rule_defs.count} normative rules into file #{filename}")

  # Organize rules by chapter name. Each hash key is chapter name. Each hash entry is an Array<NormativeRuleDef>
  defs_by_chapter_name = {}
  defs.norm_rule_defs.each do |d|
    defs_by_chapter_name[d.chapter_name] = [] if defs_by_chapter_name[d.chapter_name].nil?
    defs_by_chapter_name[d.chapter_name].append(d)
  end

  File.open(filename, "w") do |f|
    f.puts("= Normative Rules by Chapter")

    defs_by_chapter_name.each do |chapter_name, nr_defs|
      f.puts("")
      f.puts("== #{chapter_name}")
      f.puts("")
      f.puts("[cols=\"20%,60%,20%\"]")
      f.puts("|===")
      f.puts("| Rule Name | Rule Description | Origin of Description")

      nr_defs.each do |nr|
        info_rows = (nr.summary.nil? ? 0 : 1) + (nr.description.nil? ? 0 : 1) +
          (nr.kind.nil? ? 0 : 1) + (nr.instances.empty? ? 0 : 1) + nr.tag_refs.length
        row_span = (info_rows > 0) ? ".#{info_rows}+" : ""

        f.puts("")
        f.puts("#{row_span}| #{nr.name}")
        f.puts("| #{nr.summary} | Rule's 'summary' property") unless nr.summary.nil?
        f.puts("| #{nr.description} | Rule's 'description' property") unless nr.description.nil?
        f.puts("| #{nr.kind} | Rule's 'kind' property") unless nr.kind.nil?
        f.puts('| [' + nr.instances.join(', ') + '] | Rule Instances') unless nr.instances.empty?
        nr.tag_refs.each do |tag_ref|
          tag = tags.get_tag(tag_ref)
          fatal("Normative rule #{nr.name} defined in file #{nr.def_filename} references non-existent tag #{tag_ref}") if tag.nil?

          url = tag_fname2url[tag.tag_filename]
          fatal("No fname tag to URL mapping (-tag2url cmd line arg) for tag fname #{tag.tag_filename} for tag name #{tag.name}") if url.nil?

          f.puts("| #{handle_tables(tag.text)} a| link:#{url}" + "#" + tag_ref + "[#{tag_ref}]")
        end
      end

      f.puts("|===")
    end
  end
end

# Store normative rules in HTML output file.
def output_html(filename, defs, tags, tag_fname2url)
  fatal("Need String for filename but passed a #{filename.class}") unless filename.is_a?(String)
  fatal("Need NormativeRuleDefs for defs but passed a #{defs.class}") unless defs.is_a?(NormativeRuleDefs)
  fatal("Need NormativeTags for tags but passed a #{tags.class}") unless tags.is_a?(NormativeTags)
  fatal("Need Hash for tag_fname2url but passed a #{tag_fname2url.class}") unless tag_fname2url.is_a?(Hash)

  info("Storing #{defs.norm_rule_defs.count} normative rules into file #{filename}")

  # Organize rules by chapter name. Each hash key is chapter name. Each hash entry is an Array<NormativeRuleDef>
  defs_by_chapter_name = {}
  chapter_names=[]
  defs.norm_rule_defs.each do |d|
    if defs_by_chapter_name[d.chapter_name].nil?
      # Haven't seen this chapter name yet.
      defs_by_chapter_name[d.chapter_name] = []
      chapter_names.append(d.chapter_name)
    end
    defs_by_chapter_name[d.chapter_name].append(d)
  end

  chapter_names.sort!

  File.open(filename, "w") do |f|
    #f.puts("= Normative Rules by Chapter")
    html_head(f)
    f.puts(%Q{<body>})
    f.puts(%Q{  <div class="app">})

    html_sidebar(f, chapter_names)
    f.puts("    <main>")

    table_num=1

    chapter_names.each do |chapter_name|
      nr_defs = defs_by_chapter_name[chapter_name]
      html_chapter_table(f, table_num, chapter_name, nr_defs, tags, tag_fname2url)
      table_num=table_num+1
    end

    f.puts("    </main>")
    f.puts("  </div>")

    html_script(f)

    f.puts("</body>")
    f.puts("</html>")
  end
end

def html_head(f)
  fatal("Need File for f but passed a #{f.class}") unless f.is_a?(File)

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

        table{width:100%;border-collapse:collapse;margin-top:12px;table-layout: fixed}
        th,td{padding:10px 12px;border:1px solid #e6edf3;text-align:left;overflow-wrap: break-word;white-space: normal}
        th{background:#f3f7fb;font-weight:700}

        .col-name { width: 20%; }
        .col-description { width: 60%; }
        .col-location { width: 20%; }

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

def html_sidebar(f, chapter_names)
  fatal("Need File for f but passed a #{f.class}") unless f.is_a?(File)
  fatal("Need Array for chapter_names but passed a #{chapter_names.class}") unless chapter_names.is_a?(Array)

  # Use Ruby $Q{...} instead of double quotes to allow freely mixing embedded double quotes and Ruby's #{} operator.
  f.puts("")
  f.puts(%Q{  <aside class="sidebar">})
  f.puts(%Q{    <h2>Chapters</h2>})
  f.puts(%Q{    <nav class="nav" id="nav">})

  table_num=1

  chapter_names.each do |chapter_name|
    f.puts(%Q{      <a href="#table-#{table_num}" data-target="table-#{table_num}">#{chapter_name}</a>})
    table_num = table_num+1
  end

  f.puts('    </nav>')
  f.puts('  </aside>')
end

def html_chapter_table(f, table_num, chapter_name, nr_defs, tags, tag_fname2url)
  fatal("Need File for f but passed a #{f.class}") unless f.is_a?(File)
  fatal("Need Integer for table_num but passed a #{table_num.class}") unless table_num.is_a?(Integer)
  fatal("Need String for chapter_name but passed a #{chapter_name.class}") unless chapter_name.is_a?(String)
  fatal("Need Array for nr_defs but passed a #{nr_defs.class}") unless nr_defs.is_a?(Array)
  fatal("Need NormativeTags for tags but passed a #{tags.class}") unless tags.is_a?(NormativeTags)
  fatal("Need Hash for tag_fname2url but passed a #{tag_fname2url.class}") unless tag_fname2url.is_a?(Hash)

  f.puts("")
  f.puts(%Q{      <section id="table-#{table_num}" class="section">})
  f.puts(%Q{        <h3>#{chapter_name}</h3>})
  f.puts(%Q{        <table>})
  f.puts(%Q{          <colgroup>})
  f.puts(%Q{            <col class="col-name">})
  f.puts(%Q{            <col class="col-description">})
  f.puts(%Q{            <col class="col-location">})
  f.puts(%Q{          </colgroup>})
  f.puts(%Q{          <thead>})
  f.puts(%Q{            <tr><th>Rule Name</th><th>Rule Description</th><th>Origin of Description</th></tr>})
  f.puts(%Q{          </thead>})
  f.puts(%Q{          <tbody>})

  nr_defs.each do |nr|
    name_row_span = (nr.summary.nil? ? 0 : 1) + (nr.description.nil? ? 0 : 1) +
      (nr.kind.nil? ? 0 : 1) + (nr.instances.empty? ? 0 : 1) + nr.tag_refs.length

    row_started = true
    f.puts(%Q{            <tr>})
    f.puts(%Q{              <td rowspan=#{name_row_span} id="#{nr.name}">#{nr.name}</td>})

    unless nr.summary.nil?
      f.puts(%Q{            <tr>}) unless row_started
      f.puts(%Q{              <td>#{nr.summary}</td>})
      f.puts(%Q{              <td>Rule's "summary" property</td>})
      f.puts(%Q{            </tr>})
      row_started = false
    end

    unless nr.description.nil?
      f.puts(%Q{            <tr>}) unless row_started
      f.puts(%Q{              <td>#{html_handle_newlines(nr.description)}</td>})
      f.puts(%Q{              <td>Rule's "description" property</td>})
      f.puts(%Q{            </tr>})
      row_started = false
    end

    unless nr.kind.nil?
      f.puts(%Q{            <tr>}) unless row_started
      f.puts(%Q{              <td>#{nr.kind}</td>})
      f.puts(%Q{              <td>Rule's "kind" property</td>})
      f.puts(%Q{            </tr>})
      row_started = false
    end

    unless nr.instances.empty?
      instances_str = "[" + nr.instances.join(', ') + "]"
      f.puts(%Q{            <tr>}) unless row_started
      f.puts(%Q{              <td>#{instances_str}</td>})
      f.puts(%Q{              <td>Rule's "instance/instances" property</td>})
      f.puts(%Q{            </tr>})
      row_started = false
    end

    nr.tag_refs.each do |tag_ref|
      tag = tags.get_tag(tag_ref)
      fatal("Normative rule #{nr.name} defined in file #{nr.def_filename} references non-existent tag #{tag_ref}") if tag.nil?

      html_fname = tag_fname2url[tag.tag_filename]
      fatal("No fname tag to HTML mapping (-tag2url cmd line arg) for tag fname #{tag.tag_filename} for tag name #{tag.name}") if html_fname.nil?

      f.puts(%Q{            <tr>}) unless row_started
      f.puts(%Q{              <td>#{html_handle_newlines(handle_tables(Adoc2HTML::convert_all(tag.text)))}</td>})
      f.puts(%Q{              <td><a href="#{html_fname}##{tag_ref}">#{tag_ref}</a></td>})
      f.puts(%Q{            </tr>})
      row_started = false
    end
  end

  f.puts(%Q{          </tbody>})
  f.puts(%Q{        </table>})
  f.puts(%Q{      </section>})
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
def handle_tables(text)
  raise ArgumentError, "Expected String for text but was passed a #{text}.class" unless text.is_a?(String)

  # This is the detection pattern for an entire table being tagged from the "tags.rb" AsciiDoctor backend.
  if text.end_with?("\n===")
    # Limit table size displayed.
    truncate_after_newlines(text, 12)
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

# Convert newlines to <br>.
def html_handle_newlines(text)
  raise ArgumentError, "Expected String for text but was passed a #{text}.class" unless text.is_a?(String)

  text.gsub(/\n/, '<br>')
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

case output_format
when "json"
  normative_rules_hash = create_normative_rules_hash(defs, tags, tag_fname2url)
  output_json(output_fname, normative_rules_hash)
when "xlsx"
  output_xlsx(output_fname, defs, tags)
when "adoc"
  output_adoc(output_fname, defs, tags, tag_fname2url)
when "html"
  output_html(output_fname, defs, tags, tag_fname2url)
else
  raise "Unknown output_format of #{output_format}"
end

exit 0

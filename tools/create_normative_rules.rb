# frozen_string_literal: true

require "json"
require "yaml"

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
    fatal_error("Need String for tag_filename but was passed a #{tag_filename.class}") unless tag_filename.is_a?(String)
    fatal_error("Need Hash for tags but was passed a #{tags.class}") unless tags.is_a?(Hash)

    tags.each do |name, text|
      unless name.is_a?(String)
        fatal_error("Tag name #{name} in file #{tag_filename} is a #{name.class} instead of a String")
      end

      unless text.is_a?(String)
        fatal_error("Tag name #{name} in file #{tag_filename} is a #{text.class} instead of a String
#{PN}:   If the AsciiDoc anchor for #{name} is before an AsciiDoc 'Description List' term, move to after term on its own line.")
      end

      unless @tag_map[name].nil?
        fatal_error("Tag name #{name} in file #{tag_filename} already defined in file #{@tag_map[name].tag_filename}")
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
  # @return [String] Name of normative rule tag into standards document
  attr_reader :name

  # @return [String] Name of tag file
  attr_reader :tag_filename

  # @return [String] Text associated with normative rule tag from standards document. Can have newlines.
  attr_reader :text

  # @param name [String]
  # @param tag_filename [String]
  # @param text [String]
  def initialize(name, tag_filename, text)
    fatal_error("Need String for name but passed a #{name.class}") unless name.is_a?(String)
    fatal_error("Need String for tag_filename but passed a #{tag_filename.class}") unless tag_filename.is_a?(String)
    fatal_error("Need String for text but passed a #{text.class}") unless text.is_a?(String)

    @name = name
    @tag_filename = tag_filename
    @text = text

    # Used to find tags without any references to them.
    @ref_to_me = false
  end

  def normative_rule_references_me
    @ref_to_me = true
  end

  # No normative rule has referencing me.
  def unreferenced? = !@ref_to_me
end

##########################################
# Classes for Normative Rule Definitions #
##########################################

# Holds all the information for all normative rule definition files.
class NormativeRuleDefs
  attr_reader :norm_rule_defs  # Array<NormativeRuleDef> Contains all normative rule definitions across all input files

  def initialize
    @norm_rule_defs = []
    @hash = {}     # Hash<String name, NormativeRuleDef> Same objects as in array and just internal to class
  end

  def add_file_contents(def_filename, array_data)
    fatal_error("Need String for def_filename but passed a #{def_filename.class}") unless def_filename.is_a?(String)
    fatal_error("Need Array for array_data but passed a #{array_data.class}") unless array_data.is_a?(Array)

    array_data.each do |data|
      fatal_error("File #{def_filename} entry isn't a hash: #{data}") unless data.is_a?(Hash)

      if !data["name"].nil?
        # Add one definition object
        add_def(data["name"], def_filename, data)
      elsif !data["names"].nil?
        # Add one definition object for each name in array
        names = data["names"]
        names.each do |name|
          add_def(name, def_filename, data)
        end
      else
        fatal_error("File #{def_filename} missing name/names in normative rule definition entry: #{data}")
      end
    end
  end

  def add_def(name, def_filename, data)
    fatal_error("Need String for name but passed a #{name.class}") unless name.is_a?(String)
    fatal_error("Need String for def_filename but passed a #{def_filename.class}") unless def_filename.is_a?(String)
    fatal_error("Need Hash for data but passed a #{data.class}") unless data.is_a?(Hash)

    unless @hash[name].nil?
      fatal_error("Normative rule definition #{name} in file #{def_filename} already defined in file #{@hash[name].def_filename}")
    end

    # Create definition object and store reference to it in array (to maintain order) and hash (for convenient lookup by name).
    norm_rule_defs = NormativeRuleDef.new(def_filename, name, data)
    @norm_rule_defs.append(norm_rule_defs)
    @hash[name] = norm_rule_defs
  end
end # class NormativeRuleDefs

class NormativeRuleDef
  attr_reader :def_filename           # String (mandatory)
  attr_reader :name                   # String (mandatory)
  attr_reader :summary                # String (optional - a few words)
  attr_reader :description            # String (optional - sentence, paragraph, or more)
  attr_reader :kind                   # String (optional, can be nil, extension, instruction, csr, csr_field)
  attr_reader :instances              # Array<String> (optional only if kind defined, nil if kind nil, otherwise an array)
  attr_reader :tag_refs               # Array<NormativeTagRef> (optional - can be empty)
  attr_reader :tag_refs_without_text  # Array<NormativeTagRef> (optional - can be empty - like tag_refs but no tag text)

  def initialize(def_filename, name, data)
    fatal_error("Need String for def_filename but was passed a #{def_filename.class}") unless def_filename.is_a?(String)
    fatal_error("Need String for name but was passed a #{name.class}") unless name.is_a?(String)
    fatal_error("Need Hash for data but was passed a #{data.class}") unless data.is_a?(Hash)

    @def_filename = def_filename
    @name = name

    @summary = data["summary"]
    unless @summary.nil?
      fatal_error("Provided #{@summary.class} class for summary in normative rule #{name} but need a String") unless @summary.is_a?(String)
    end

    @description = data["description"]
    unless @description.nil?
      fatal_error("Provided #{@description.class} class for description in normative rule #{name} but need a String") unless @description.is_a?(String)
    end

    @kind = data["kind"]
    unless @kind.nil?
      fatal_error("Provided #{@kind.class} class for kind in normative rule #{name} but need a String") unless @kind.is_a?(String)
      check_allowed_types(@kind, @name, nil)
    end

    @instances = data["instances"]
    if @kind.nil?
      # Not allowed to have instances without a kind.
      fatal_error("Normative rule #{name} defines instances but no kind") unless @instances.nil?
    else
      fatal_error("Provided #{@kind.class} class for kind in normative rule #{name} but need a String") unless @kind.is_a?(String)

      if @instances.nil?
        @instances = []
      else
        fatal_error("Provided #{@instances.class} class for instances in normative rule #{nr_name} but need an Array") unless @instances.is_a?(Array)
      end
    end

    @tag_refs = []
    data["tags"]&.each do |tag_data|
      @tag_refs.append(NormativeTagRef.new(@name, tag_data))
    end

    @tag_refs_without_text = []
    data["tags_without_text"]&.each do |tag_data|
      @tag_refs_without_text.append(NormativeTagRef.new(@name, tag_data))
    end
  end
end # class NormativeRuleDef

# Holds one reference to a tag by a rule definition.
class NormativeTagRef
  attr_reader :name               # String (mandatory)
  attr_reader :kind               # String (optional, can be nil, extension, instruction, csr, csr_field)
  attr_reader :instances          # Array<String> (optional only if kind defined, nil if kind nil, otherwise an array)

  # The nr_name is the name of the normative rule
  # The data can either be a String (so just the tag name provided) or a hash if more info passed.
  def initialize(nr_name, data)
    fatal_error("Need String for nr_name but was passed a #{nr_name.class}") unless nr_name.is_a?(String)

    if data.is_a?(String)
      @name = data
      @instances = nil
    elsif data.is_a?(Hash)
      @name = data["name"]
      fatal_error("Missing tag name referenced by normative rule #{nr_name}") if @name.nil?
      fatal_error("Provided #{@name.class} class for tag name #{@name} in normative rule #{nr_name} but need a String") unless @name.is_a?(String)

      # Handle optional values
      @kind = data["kind"]
      unless @kind.nil?
        fatal_error("Provided #{@kind.class} class for kind in tag #{@name} in normative rule #{name} but need a String") unless @kind.is_a?(String)
        check_allowed_types(@kind, nr_name, @name)
      end

      @instances = data["instances"]

      if @kind.nil?
        # Not allowed to have instances without a kind.
        fatal_error("Tag #{@name} referenced in normative rule #{nr_name} defines instances but no kind") unless @instances.nil?
      else
        fatal_error("Provided #{@kind.class} class for kind in tag #{name} in normative rule #{nr_name} but need a String") unless @kind.is_a?(String)

        if @instances.nil?
          @instances = []
        else
          fatal_error("Provided #{@instances.class} class for instances in tag #{name} in normative rule #{nr_name} but need an Array") unless @instances.is_a?(Array)
        end
      end
    else
      fatal_error("Need String or Hash for data for normative rule #{nr_name} but passed a #{data.class}")
    end
  end
end # class NormativeTagRef

# Create fatal_error if kind not recognized. The name is nil if this is called in the normative rule definition.
def check_allowed_types(kind, nr_name, name)
  allowed_types = ["extension", "instruction", "csr", "csr_field"]

  unless allowed_types.include?(kind)
    tag_str = name.nil? ? "" : "tag #{name} in "
    allowed_str = allowed_types.join(",")
    fatal_error("Don't recognize kind '#{kind}' for #{tag_str}normative rule #{nr_name}\n#{PN}: Allowed types are: #{allowed_str}")
  end
end

def fatal_error(msg)
  puts "#{PN}: ERROR: #{msg}"
  exit(1)
end

def info(msg)
  puts "#{PN}: #{msg}"
end

def usage(exit_status = 1)
  puts "Usage: #{PN} [OPTION]... <output-filename>"
  puts "  -d filename    normative rule definition filename (YAML format)"
  puts "  -t filename    normative tag filename (JSON format)"
  puts
  puts "Creates list of normative rules and stores them in <output-filename> (JSON format)."
  exit exit_status
end

# Returns array of command line information
# Uses Ruby ARGV variable to access command line args.
# Exits program on error.
def parse_argv
  usage(0) if ARGV.count == 1 && (ARGV[0] == "-h" || ARGV[0] == "--help")

  usage if ARGV.count == 0

  # Return values
  def_fnames=[]
  tag_fnames=[]
  output_fname=nil

  i = 0
  while i < ARGV.count
    arg = ARGV[i]
    case arg
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

  return [def_fnames, tag_fnames, output_fname]
end

# Load the contents of all normative rule tag files in JSON format.
# Returns a NormativeTag class with all the contents.
def load_tags(tag_fnames)
  fatal_error("Need Array<String> for tag_fnames but passed a #{tag_fnames.class}") unless tag_fnames.is_a?(Array)

  tags = NormativeTags.new()

  tag_fnames.each do |tag_fname|
    info("Loading tag file #{tag_fname}")

    # Read in file to a String
    begin
      file_contents = File.read(tag_fname, encoding: "UTF-8")
    rescue Errno::ENOENT => e
      fatal_error("#{e.message}")
    end

    # Convert String in JSON format to a Ruby hash.
    begin
      file_data = JSON.parse(file_contents)
    rescue JSON::ParserError => e
      fatal_error("File #{tag_fname} JSON parsing error: #{e.message}")
    rescue JSON::NestingError => e
      fatal_error("File #{tag_fname} JSON nesting error: #{e.message}")
    end

    tags_data = file_data["tags"] || fatal_error("Missing 'tags' key in #{tag_fname}")

    # Add tags from JSON file to Ruby class.
    tags.add_tags(tag_fname, tags_data)
  end

  return tags
end

# Load the contents of all normative rule definition files in YAML format.
# Returns a NormativeRuleDef class with all the contents.
def load_definitions(def_fnames)
  fatal_error("Need Array<String> for def_fnames but passed a #{def_fnames.class}") unless def_fnames.is_a?(Array)

  defs = NormativeRuleDefs.new()

  def_fnames.each do |def_fname|
    info("Loading definition file #{def_fname}")

    # Read in file to a String
    begin
      file_contents = File.read(def_fname, encoding: "UTF-8")
    rescue Errno::ENOENT => e
      fatal_error("#{e.message}")
    end

    # Convert String in YAML format to a Ruby hash.
    # Note that YAML is an alias for Pysch in Ruby.
    begin
      yaml_hash = YAML.load(file_contents)
    rescue Psych::SyntaxError => e
      fatal_error("File #{def_fname} YAML syntax error - #{e.message}")
    end

    array_data = yaml_hash["normative_rule_definitions"] || fatal_error("Missing 'normative_rule_definitions' key in #{def_fname}")
    fatal_error("'normative_rule_definitions' isn't an array in #{def_fname}") unless array_data.is_a?(Array)

    defs.add_file_contents(def_fname, array_data)
  end

  return defs
end

# Returns a Hash with just one entry called "normative_rules" that contains an Array of Hashes of all normative rules.
def create_normative_rules(tags, defs)
    fatal_error("Need NormativeTags for tags but was passed a #{tags.class}") unless tags.is_a?(NormativeTags)
    fatal_error("Need NormativeRuleDefs for defs but was passed a #{defs.class}") unless defs.is_a?(NormativeRuleDefs)

    info("Creating normative rules from definition files")

    ret = {
      "normative_rules" => []
    }

    missing_tag_cnt = 0

    defs.norm_rule_defs.each do |d|
      # Create hash with mandatory definition arguments.
      hash = {
        "name" => d.name,
        "def_filename" => d.def_filename
      }

      # Now add optional arguments.
      hash["kind"] = d.kind unless d.kind.nil?
      hash["instances"] = d.instances unless d.instances.nil?
      hash["summary"] = d.summary unless d.summary.nil?
      hash["description"] = d.description unless d.description.nil?

      unless d.tag_refs.nil? && d.tag_refs_without_text.nil?
        hash["tags"] = []
      end

      # Add tag entries for those that should have tag text.
      unless d.tag_refs.nil?
        d.tag_refs.each do |tag_ref|
          tag_ref_name = tag_ref.name

          # Lookup tag
          tag = tags.get_tag(tag_ref_name)

          if tag.nil?
            missing_tag_cnt = missing_tag_cnt + 1
            info("Normative rule #{d.name} defined in file #{d.def_filename} references non-existent tag #{tag_ref_name}")
          else
            resolved_tag = {
              "name" => tag.name,
              "text" => tag.text,
              "tag_filename" => tag.tag_filename
            }

            # Add optional info from tag reference.
            resolved_tag["kind"] = tag_ref.kind unless tag_ref.kind.nil?
            resolved_tag["instances"] = tag_ref.instances unless tag_ref.instances.nil?

            hash["tags"].append(resolved_tag)

            # Used to track which tags don't have any normative rules referencing them.
            tag.normative_rule_references_me()
          end
        end
      end

      # Add tag entries for those that shouldn't have tag text.
      unless d.tag_refs_without_text.nil?
        d.tag_refs_without_text.each do |tag_ref|
          tag_ref_name = tag_ref.name

          # Lookup tag. Should be nil.
          tag = tags.get_tag(tag_ref_name)

          if tag.nil?
            resolved_tag = {
              "name" => tag_ref_name,
            }

            # Add optional info from tag reference.
            resolved_tag["kind"] = tag_ref.kind unless tag_ref.kind.nil?
            resolved_tag["instances"] = tag_ref.instances unless tag_ref.instances.nil?

            hash["tags"].append(resolved_tag)
          else
            fatal_error("Normative rule #{d.name} defined in file #{d.def_filename} has
#{PN}: tag #{tag_ref_name} tag text but shouldn't")
          end
        end
      end

      ret["normative_rules"].append(hash)
    end

    fatal_error("#{missing_tag_cnt} reference#{missing_tag_cnt == 1 ? "" : "s"} to non-existing tags") if missing_tag_cnt > 0

    return ret
end

# Report any tags not referenced by any normative rule.
# Must be called after normative_rules are created so pass them in
# to this method but don't use them.
def detect_unreferenced_tags(tags, normative_rules)
  fatal_error("Need NormativeTags for tags but was passed a #{tags.class}") unless tags.is_a?(NormativeTags)
  fatal_error("Need Hash<String, Array> for normative_rules but passed a #{normative_rules.class}") unless normative_rules.is_a?(Hash)

  unref_cnt = 0

  tags.get_tags.each do |tag|
    if tag.unreferenced?
      info("Tag #{tag.name} not referenced by any normative rule. Did you forget to define a normative rule?")
      unref_cnt = unref_cnt + 1
    end
  end

  # TODO: Make this a fatal_error() instead of an info().
  info("#{unref_cnt} tag#{unref_cnt == 1 ? "" : "s"} have no normative rules referencing them") if unref_cnt > 0
end

# Store normative rules in JSON output file
def store_normative_rules(filename, normative_rules)
  fatal_error("Need String for filename but passed a #{filename.class}") unless filename.is_a?(String)
  fatal_error("Need Hash<String, Array> for normative_rules but passed a #{normative_rules.class}") unless normative_rules.is_a?(Hash)

  nr_array = normative_rules["normative_rules"]
  raise "Expecting an array for key normative_rules but got an #{nr_array.class}" unless nr_array.is_a?(Array)

  info("Storing #{nr_array.count} normative rules into file #{filename}")

  # Serialize normative_rules hash to JSON format String.
  # Shouldn't throw exceptions since we created the data being serialized.
  serialized_string = JSON.pretty_generate(normative_rules)

  # Write serialized string to desired output file.
  begin
    File.write(filename, serialized_string)
  rescue Errno::ENOENT => e
    fatal_error("#{e.message}")
  rescue Errno::EACCES => e
    fatal_error("#{e.message}")
  rescue IOError => e
    fatal_error("#{e.message}")
  rescue ArgumentError => e
    fatal_error("#{e.message}")
  end
end

#main()

info("Passed #{ARGV.join(' ')}")

def_fnames, tag_fnames, output_fname = parse_argv()

info("Normative rule definition filenames = #{def_fnames}")
info("Normative tag filenames = #{tag_fnames}")
info("Output filename = #{output_fname}")

tags = load_tags(tag_fnames)
defs = load_definitions(def_fnames)
normative_rules = create_normative_rules(tags, defs)
detect_unreferenced_tags(tags, normative_rules)
store_normative_rules(output_fname, normative_rules)

exit 0

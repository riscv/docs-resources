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
  # param filename [String] Name of the tag file
  # param tags [Hash<String,String>] Hash key is tag name (AKA anchor name) and value is tag text.
  def add_tags(filename, tags)
    fatal_error("Need String for filename but was passed a #{filename.class}") unless filename.is_a?(String)
    fatal_error("Need Hash for tags but was passed a #{tags.class}") unless tags.is_a?(Hash)

    tags.each do |tag_name, tag_text|
      unless tag_name.is_a?(String)
        fatal_error("NormativeTag name #{tag_name} in file #{filename} is a #{tag_name.class} instead of a String")
      end

      unless tag_text.is_a?(String)
        fatal_error("NormativeTag name #{tag_name} in file #{filename} is a #{tag_text.class} instead of a String
#{PN}:   If the AsciiDoc anchor for #{tag_name} is before an AsciiDoc 'Description List' term, move to after term on its own line.")
      end

      unless @tag_map[tag_name].nil?
        fatal_error("NormativeTag name #{tag_name} in file #{filename} already defined in file #{@tag_map[tag_name].filename}")
      end

      @tag_map[tag_name] = NormativeTag.new(tag_name, filename, tag_text)
    end
  end

  # @param [String] Normative rule tag name
  # @return [NormativeTag] Normative rule tag object corresponding to tag name. Returns nil if not found.
  def get_tag(tag_name) = @tag_map[tag_name]

  # @return [Array<NormativeTag>] All normative tags for the standard.
  def get_tags() = @tag_map.values
end

# Holds all information for one tag.
class NormativeTag
  # @return [String] Name of normative rule tag into standards document
  attr_reader :tag_name

  # @return [String] Name of standards document tag is located in.
  attr_reader :filename

  # @return [String] Text associated with normative rule tag from standards document. Can have newlines.
  attr_reader :tag_text

  # @param tag_name [String]
  # @param filename [String]
  # @param tag_text [String]
  def initialize(tag_name, filename, tag_text)
    fatal_error("Need String for tag_name but passed a #{tag_name.class}") unless tag_name.is_a?(String)
    fatal_error("Need String for filename but passed a #{filename.class}") unless filename.is_a?(String)
    fatal_error("Need String for tag_text but passed a #{tag_text.class}") unless tag_text.is_a?(String)

    @tag_name = tag_name
    @filename = filename
    @tag_text = tag_text

    # Used to find tags without any references to them.
    @ref_to_me = false
  end

  def normative_rule_references_me
    @ref_to_me = true
  end

  # No normative rule has referencing me.
  def unreferenced? = !@ref_to_me
end

########################################
# Classes for Normative Rule Creations #
########################################

# Holds all the information for all the normative rule creation files.
class NormativeRuleCreations
  attr_reader :norm_rule_creations  # Array<NormativeRuleCreation> Contains all normative rules across all input files

  def initialize
    @norm_rule_creations = []
    @hash = {}     # Hash<String name, NormativeRuleCreation> Same objects as in array and just internal to class
  end

  def add_file_contents(filename, array_data)
    fatal_error("Need String for filename but passed a #{filename.class}") unless filename.is_a?(String)
    fatal_error("Need Array for array_data but passed a #{array_data.class}") unless array_data.is_a?(Array)

    array_data.each do |data|
      fatal_error("File #{filename} entry isn't a hash: #{data}") unless data.is_a?(Hash)

      if !data["name"].nil?
        # Add one creation object
        add_creation(data["name"], filename, data)
      elsif !data["names"].nil?
        # Add one creation object for each name in array
        names = data["names"]
        names.each do |name|
          add_creation(name, filename, data)
        end
      else
        fatal_error("File #{filename} missing name/names in normative rule creation entry: #{data}")
      end
    end
  end

  def add_creation(name, filename, data)
    fatal_error("Need String for name but passed a #{name.class}") unless name.is_a?(String)
    fatal_error("Need String for filename but passed a #{filename.class}") unless filename.is_a?(String)
    fatal_error("Need Hash for data but passed a #{data.class}") unless data.is_a?(Hash)

    unless @hash[name].nil?
      fatal_error("Normative rule creation #{name} in file #{filename} already defined in file #{@hash[name].filename}")
    end

    # Create creation object and store reference to it in array (to maintain order) and hash (for convenient lookup by name).
    norm_rule_creations = NormativeRuleCreation.new(filename, name, data)
    @norm_rule_creations.append(norm_rule_creations)
    @hash[name] = norm_rule_creations
  end
end # class NormativeRuleCreations

class NormativeRuleCreation
  attr_reader :filename               # String (mandatory)
  attr_reader :name                   # String (mandatory)
  attr_reader :type                   # String (optional)
  attr_reader :summary                # String (optional - a few words)
  attr_reader :description            # String (optional - sentence, paragraph, or more)
  attr_reader :tag_refs               # Array<NormativeTagRef> (optional - can be empty)
  attr_reader :tag_refs_without_text  # Array<NormativeTagRef> (optional - can be empty - like tag_refs but no tag text)

  def initialize(filename, name, data)
    @filename = filename
    @name = name
    @type = data["type"]
    @summary = data["summary"]
    @description = data["description"]

    @tag_refs = []
    data["tags"]&.each do |tag_data|
      @tag_refs.append(NormativeTagRef.new(tag_data))
    end

    @tag_refs_without_text = []
    data["tags_without_text"]&.each do |tag_data|
      @tag_refs_without_text.append(NormativeTagRef.new(tag_data))
    end
  end
end # class NormativeRuleCreation

# Holds one reference to a tag by a creation.
class NormativeTagRef
  attr_reader :name

  # Currently NormativeTag is just a String but could potentially be passed a Hash if metadata gets added to a tag.
  def initialize(tag_data)
    fatal_error("Need String for tag_data but passed a #{tag_data.class}") unless tag_data.is_a?(String)

    @name = tag_data
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
  puts "  -c filename    normative rule creation filename (YAML)"
  puts "  -t filename    normative tag filename (JSON)"
  puts
  puts "Creates list of normative rules and stores them in <output-filename> (in JSON format)."
  exit exit_status
end

# Returns array of command line information
# Uses Ruby ARGV variable to access command line args.
# Exits program on error.
def parse_argv
  usage(0) if ARGV.count == 1 && (ARGV[0] == "-h" || ARGV[0] == "--help")

  usage if ARGV.count == 0

  # Return values
  creation_fnames=[]
  tag_fnames=[]
  output_fname=

  i = 0
  while i < ARGV.count
    arg = ARGV[i]
    case arg
    when "-c"
      if (ARGV.count-i) < 1
        info("Missing argument for -c option")
        usage
      end
      creation_fnames.append(ARGV[i+1])
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

  if creation_fnames.empty?
    info("Missing normative rule creation filename(s)")
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

  return [creation_fnames, tag_fnames, output_fname]
end

# Load the contents of all normative rule tag files in JSON format.
# Returns a NormativeTag class with all the contents.
def load_tags(tag_fnames)
  fatal_error("Need Array<String> for tag_fnames but passed a #{tag_fnames.class}") unless tag_fnames.is_a?(Array)

  tags = NormativeTags.new()

  tag_fnames.each do |filename|
    info("Loading tag file #{filename}")

    # Read in file to a String
    begin
      file_contents = File.read(filename, encoding: "UTF-8")
    rescue Errno::ENOENT => e
      fatal_error("#{e.message}")
    end

    # Convert String in JSON format to a Ruby hash.
    begin
      file_data = JSON.parse(file_contents)
    rescue JSON::ParserError => e
      fatal_error("File #{filename} JSON parsing error: #{e.message}")
    rescue JSON::NestingError => e
      fatal_error("File #{filename} JSON nesting error: #{e.message}")
    end

    tags_data = file_data["tags"] || fatal_error("Missing 'tags' key in #{filename}")

    # Add tags from JSON file to Ruby class.
    tags.add_tags(filename, tags_data)
  end

  return tags
end

# Load the contents of all normative rule creation files in YAML format.
# Returns a NormativeRuleCreation class with all the contents.
def load_creations(creation_fnames)
  fatal_error("Need Array<String> for creation_fnames but passed a #{creation_fnames.class}") unless creation_fnames.is_a?(Array)

  creations = NormativeRuleCreations.new()

  creation_fnames.each do |filename|
    info("Loading creation file #{filename}")

    # Read in file to a String
    begin
      file_contents = File.read(filename, encoding: "UTF-8")
    rescue Errno::ENOENT => e
      fatal_error("#{e.message}")
    end

    # Convert String in YAML format to a Ruby hash.
    # Note that YAML is an alias for Pysch in Ruby.
    begin
      yaml_hash = YAML.load(file_contents)
    rescue Psych::SyntaxError => e
      fatal_error("File #{filename} YAML syntax error - #{e.message}")
    end

    array_data = yaml_hash["normative_rule_creations"] || fatal_error("Missing 'normative_rule_creations' key in #{filename}")
    fatal_error("'normative_rule_creations' isn't an array in #{filename}") unless array_data.is_a?(Array)

    creations.add_file_contents(filename, array_data)
  end

  return creations
end

# Returns a Hash with just one entry called "normative_rules" that contains an Array of Hashes of all normative rules.
def create_normative_rules(tags, creations)
    fatal_error("Need NormativeTags for tags but was passed a #{tags.class}") unless tags.is_a?(NormativeTags)
    fatal_error("Need NormativeRuleCreations for creations but was passed a #{creations.class}") unless creations.is_a?(NormativeRuleCreations)

    info("Creating created normative rules")

    ret = {
      "normative_rules" => []
    }

    missing_tag_cnt = 0

    creations.norm_rule_creations.each do |creation|
      # Create hash with mandatory creation arguments.
      hash = {
        "name" => creation.name,
        "filename" => creation.filename
      }

      # Now add optional arguments.
      hash["type"] = creation.type unless creation.type.nil?
      hash["summary"] = creation.summary unless creation.summary.nil?
      hash["description"] = creation.description unless creation.description.nil?

      unless creation.tag_refs.nil? && creation.tag_refs_without_text.nil?
        hash["tags"] = []
      end

      # Add tag entries for those that should have tag text.
      unless creation.tag_refs.nil?
        creation.tag_refs.each do |tag_ref|
          tag_ref_name = tag_ref.name

          # Lookup tag
          tag = tags.get_tag(tag_ref_name)

          if tag.nil?
            missing_tag_cnt = missing_tag_cnt + 1
            info("Normative rule #{creation.name} in file #{creation.filename} references non-existant tag #{tag_ref_name}")
          else
            resolved_tag = {
              "tag_name" => tag.tag_name,
              "tag_text" => tag.tag_text,
              "filename" => tag.filename
            }

            hash["tags"].append(resolved_tag)

            # Used to track which tags don't have any normative rules referencing them.
            tag.normative_rule_references_me()
          end
        end
      end

      # Add tag entries for those that shouldn't have tag text.
      unless creation.tag_refs_without_text.nil?
        creation.tag_refs_without_text.each do |tag_ref|
          tag_ref_name = tag_ref.name

          # Lookup tag. Should be nil.
          tag = tags.get_tag(tag_ref_name)

          if tag.nil?
            resolved_tag = {
              "tag_name" => tag_ref_name,
            }

            hash["tags"].append(resolved_tag)
          else
            fatal_error("Normative rule #{creation.name} in file #{creation.filename} has
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
      info("Tag #{tag.tag_name} not referenced by any normative rule. Did you forget to create a normative rule?")
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

  info("Storing #{nr_array.count} created normative rules into file #{filename}")

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

creation_fnames, tag_fnames, output_fname = parse_argv()

info("Normative rule creation filenames = #{creation_fnames}")
info("Normative tag filenames = #{tag_fnames}")
info("Output filename = #{output_fname}")

tags = load_tags(tag_fnames)
creations = load_creations(creation_fnames)
normative_rules = create_normative_rules(tags, creations)
detect_unreferenced_tags(tags, normative_rules)
store_normative_rules(output_fname, normative_rules)

exit 0

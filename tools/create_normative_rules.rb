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
    raise ArgumentError, "Need String for filename but was passed a #{filename.class}" unless filename.is_a?(String)
    raise ArgumentError, "Need Hash for tags but was passed a #{tags.class}" unless tags.is_a?(Hash)

    tags.each do |tag_name, tag_text|
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
# Classes for Normative Rule Curations #
########################################

# Holds all the information for all the normative rule curation files.
class NormativeCurations
  attr_reader :normative_curations  # Array<NormativeCuration> Contains all normative rules across all input files

  def initialize
    @normative_curations = []
    @hash = {}     # Hash<String name, NormativeCuration> Same objects as in array and just internal to class
  end

  def add_file_contents(filename, array_data)
    raise ArgumentError, "Need String for filename but passed a #{filename.class}" unless filename.is_a?(String)
    raise ArgumentError, "Need Array for array_data but passed a #{array_data.class}" unless array_data.is_a?(Array)

    array_data.each do |data|
      fatal_error("File #{filename} entry isn't a hash: #{data}") unless data.is_a?(Hash)

      if !data["name"].nil?
        # Add one curation object
        add_curation(data["name"], filename, data)
      elsif !data["names"].nil?
        # Add one curation object for each name in array
        names = data["names"]
        names.each do |name|
          add_curation(name, filename, data)
        end
      else
        fatal_error("File #{filename} missing name/names in normative rule curation entry: #{data}")
      end
    end
  end

  def add_curation(name, filename, data)
    raise ArgumentError, "Need String for name but passed a #{name.class}" unless name.is_a?(String)
    raise ArgumentError, "Need String for filename but passed a #{filename.class}" unless filename.is_a?(String)
    raise ArgumentError, "Need Hash for data but passed a #{data.class}" unless data.is_a?(Hash)

    unless @hash[name].nil?
      fatal_error("Normative rule curation #{name} in file #{filename} already defined in file #{@hash[name].filename}")
    end

    # Create curation object and store reference to it in array (to maintain order) and hash (for convenient lookup by name).
    normative_curation = NormativeCuration.new(filename, name, data)
    @normative_curations.append(normative_curation)
    @hash[name] = normative_curation
  end
end # class NormativeCurations

class NormativeCuration
  attr_reader :filename     # String        (mandatory)
  attr_reader :name         # String        (mandatory)
  attr_reader :type         # String        (optional)
  attr_reader :summary      # String        (optional - a few words)
  attr_reader :description  # String        (optional - sentence, paragraph, or more)
  attr_reader :tag_refs     # Array<NormativeTagRef> (optional - can be empty)

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
  end
end # class NormativeCuration

# Holds one reference to a tag by a curation.
class NormativeTagRef
  attr_reader :name

  # Currently NormativeTag is just a String but could potentially be passed a Hash if metadata gets added to a tag.
  def initialize(tag_data)
    raise ArgumentError, "Need String for tag_data but passed a #{tag_data.class}" unless tag_data.is_a?(String)

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
  puts "  -c filename    normative rule curation filename (YAML)"
  puts "  -t filename    normative tag filename (JSON)"
  puts
  puts "Creates curated list of normative rules and stores them <output-filename> (in JSON format)."
  exit exit_status
end

# Returns array of command line information
# Uses Ruby ARGV variable to access command line args.
# Exits program on error.
def parse_argv
  usage(0) if ARGV.count == 1 && (ARGV[0] == "-h" || ARGV[0] == "--help")

  usage if ARGV.count == 0

  # Return values
  curation_fnames=[]
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
      curation_fnames.append(ARGV[i+1])
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

  if curation_fnames.empty?
    info("Missing normative rule curation filename(s)")
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

  return [curation_fnames, tag_fnames, output_fname]
end

# Load the contents of all normative rule tag files in JSON format.
# Returns a NormativeTag class with all the contents.
def load_tags(tag_fnames)
  raise ArgumentError, "Need Array<String> for tag_fnames but passed a #{tag_fnames.class}" unless tag_fnames.is_a?(Array)

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

# Load the contents of all normative rule curation files in YAML format.
# Returns a NormativeCuration class with all the contents.
def load_curations(curation_fnames)
  raise ArgumentError, "Need Array<String> for curation_fnames but passed a #{curation_fnames.class}" unless curation_fnames.is_a?(Array)

  curations = NormativeCurations.new()

  curation_fnames.each do |filename|
    info("Loading curation file #{filename}")

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

    array_data = yaml_hash["normative_curations"] || fatal_error("Missing 'normative_curations' key in #{filename}")
    fatal_error("'normative_curations' isn't an array in #{filename}") unless array_data.is_a?(Array)

    curations.add_file_contents(filename, array_data)
  end

  return curations
end

# Returns an Array of Hashes containing the curated normative rules ready to be serialized into a YAML file.
def create_curated_rules(tags, curations)
    raise ArgumentError, "Need NormativeTags for tags but was passed a #{tags.class}" unless tags.is_a?(NormativeTags)
    raise ArgumentError, "Need NormativeCurations for curations but was passed a #{curations.class}" unless curations.is_a?(NormativeCurations)

    info("Creating curated normative rules")

    ret = []
    missing_tag_cnt = 0

    curations.normative_curations.each do |curation|
      # Create hash with mandatory curation arguments.
      hash = {
        "name" => curation.name,
        "source" => curation.filename
      }

      # Now add optional arguments.
      hash["type"] = curation.type unless curation.type.nil?
      hash["summary"] = curation.summary unless curation.summary.nil?
      hash["description"] = curation.description unless curation.description.nil?

      # Now go through tag reference array if it has any entries and look those up.
      unless curation.tag_refs.nil?
        hash["tags"] = []

        curation.tag_refs.each do |tag_ref|
          tag_ref_name = tag_ref.name

          # Lookup tag
          tag = tags.get_tag(tag_ref_name)

          if tag.nil?
            missing_tag_cnt = missing_tag_cnt + 1
            info("Normative rule #{curation.name} references non-existant tag #{tag_ref_name}")
          else
            resolved_tag = {
              "tag_name" => tag.tag_name,
              "tag_text" => tag.tag_text,
              "source" => tag.filename
            }

            hash["tags"].append(resolved_tag)

            # Used to track which tags don't have any normative rules referencing them.
            tag.normative_rule_references_me()
          end
        end
      end

      ret.append(hash)
    end

    fatal_error("#{missing_tag_cnt} reference#{missing_tag_cnt == 1 ? "" : "s"} to non-existing tags") if missing_tag_cnt > 0

    return ret
end

# Report any tags not referenced by any normative rule.
# Must be called after curated_rules are created so pass them in
# to this method but don't use them.
def detect_unreferenced_tags(tags, curated_rules)
  raise ArgumentError, "Need NormativeTags for tags but was passed a #{tags.class}" unless tags.is_a?(NormativeTags)
  raise ArgumentError, "Need Array<Hash> for curated_rules but passed a #{curated_rules.class}" unless curated_rules.is_a?(Array)

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

# Store curated rules in JSON output file
def store_curated_rules(filename, curated_rules)
  raise ArgumentError, "Need String for filename but passed a #{filename.class}" unless filename.is_a?(String)
  raise ArgumentError, "Need Array<Hash> for curated_rules but passed a #{curated_rules.class}" unless curated_rules.is_a?(Array)

  info("Storing #{curated_rules.count} curated normative rules into file #{filename}")

  # Serialize curated_rules Array to JSON format String.
  # Shouldn't throw exceptions since we created the data being serialized.
  serialized_string = JSON.pretty_generate(curated_rules)

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

curation_fnames, tag_fnames, output_fname = parse_argv()

info("Normative rule curation filenames = #{curation_fnames}")
info("Normative tag filenames = #{tag_fnames}")
info("Output filename = #{output_fname}")

tags = load_tags(tag_fnames)
curations = load_curations(curation_fnames)
curated_rules = create_curated_rules(tags, curations)
detect_unreferenced_tags(tags, curated_rules)
store_curated_rules(output_fname, curated_rules)

exit 0

#!/usr/bin/env ruby
# frozen_string_literal: true

require "json"
require "optparse"
require "set"

# Script to detect changes in normative tags extracted from asciidoc files
# Compares two tag JSON files and reports additions, deletions, and modifications

class TagChanges
  attr_reader :added, :deleted, :modified

  def initialize
    @added = {}      # Tags present in current but not in reference
    @deleted = {}    # Tags present in reference but not in current
    @modified = {}   # Tags present in both but with different text
  end

  def any_changes?
    !@added.empty? || !@deleted.empty? || !@modified.empty?
  end

  def total_changes
    @added.size + @deleted.size + @modified.size
  end
end

class TagChangeDetector
  def initialize(options = {})
    @verbose = options[:verbose] || false
  end

  # Load tags from a JSON file
  # @param filename [String] Path to the JSON file
  # @return [Hash<String, String>] Hash of tag names to tag text
  def load_tags(filename)
    unless File.exist?(filename)
      abort("Error: File not found: #{filename}")
    end

    begin
      data = JSON.parse(File.read(filename))
      tags = data["tags"] || {}
      tags
    rescue JSON::ParserError => e
      abort("Error: Failed to parse JSON from #{filename}: #{e.message}")
    end
  end

  # Compare two tag sets and identify changes
  # @param reference_tags [Hash<String, String>] Original tags
  # @param current_tags [Hash<String, String>] Updated tags
  # @return [TagChanges] Object containing all changes
  def detect_changes(reference_tags, current_tags)
    changes = TagChanges.new

    reference_keys = reference_tags.keys.to_set
    current_keys = current_tags.keys.to_set

    # Find added tags (in current but not in reference)
    added_keys = current_keys - reference_keys
    added_keys.each do |tag_name|
      changes.added[tag_name] = current_tags[tag_name]
    end

    # Find deleted tags (in reference but not in current)
    deleted_keys = reference_keys - current_keys
    deleted_keys.each do |tag_name|
      changes.deleted[tag_name] = reference_tags[tag_name]
    end

    # Find modified tags (in both but different text)
    common_keys = reference_keys & current_keys
    common_keys.each do |tag_name|
      reference_text = reference_tags[tag_name]
      current_text = current_tags[tag_name]

      # Compare normalized text (ignoring whitespace and AsciiDoc formatting differences)
      normalized_ref = normalize_text(reference_text)
      normalized_cur = normalize_text(current_text)

      if normalized_ref != normalized_cur
        changes.modified[tag_name] = {
          "reference" => reference_text,
          "current" => current_text
        }
      end
    end

    changes
  end

  # Format and display changes
  # @param changes [TagChanges] Changes to display
  # @param reference_file [String] Name of reference file (for display)
  # @param current_file [String] Name of current file (for display)
  # @param verbose [Boolean] Whether to show verbose output
  def display_changes(changes, reference_file, current_file, verbose)
    if verbose
      puts "=" * 80
      puts "Tag Changes Report"
      puts "=" * 80
      puts
    end

    puts "Reference file: #{reference_file}"
    puts "Current file: #{current_file}"

    unless changes.any_changes?
      puts "No changes detected."
      return
    end

    # Display added tags
    unless changes.added.empty?
      count = changes.added.size
      puts "Added #{count} tag#{count > 1 ? 's' : ''}:"
      changes.added.sort.each do |tag_name, text|
        puts %Q[  * "#{tag_name}": "#{truncate_text(text)}"]
      end
      puts
    end

    # Display deleted tags
    unless changes.deleted.empty?
      count = changes.deleted.size
      puts "Deleted #{count} tag#{count > 1 ? 's' : ''}:"
      changes.deleted.sort.each do |tag_name, text|
        puts %Q[  * "#{tag_name}": "#{truncate_text(text)}"]
      end
      puts
    end

    # Display modified tags
    unless changes.modified.empty?
      count = changes.modified.size
      puts "Modified #{count} tag#{count > 1 ? 's' : ''}:"
      changes.modified.sort.each do |tag_name, texts|
        puts %Q[  * "#{tag_name}":]
        puts %Q[      Reference: "#{truncate_text(texts['reference'])}"]
        puts %Q[      Current:   "#{truncate_text(texts['current'])}"]
      end
      puts
    end

    # Summary
    if verbose
      puts "=" * 80
      puts "Summary: #{changes.total_changes} total changes"
      puts "  Added:    #{changes.added.size}"
      puts "  Deleted:  #{changes.deleted.size}"
      puts "  Modified: #{changes.modified.size}"
      puts "=" * 80
    end
  end


  # Update a tags file by adding new tags from additions
  # @param file_path [String] Path to the file to update
  # @param changes [TagChanges] Changes detected
  def update_tags_file(file_path, changes)
    if changes.added.empty?
      puts "No additions to merge into #{file_path}"
      puts "Skipping file update - no additions" if @verbose
      return
    end

    unless File.exist?(file_path)
      abort("Error: Cannot update file - not found: #{file_path}")
    end

    puts "Updating reference file: #{file_path}" if @verbose

    begin
      data = JSON.parse(File.read(file_path))
      original_count = data["tags"].size

      # Add new tags
      changes.added.each do |tag_name, tag_text|
        puts "  Adding tag: #{tag_name}" if @verbose
        data["tags"][tag_name] = tag_text
      end

      # Write back to file
      puts "Writing updated file..." if @verbose
      File.write(file_path, JSON.pretty_generate(data))
      new_count = data["tags"].size
      puts "Updated #{file_path}: added #{changes.added.size} new tags (#{original_count} -> #{new_count} total tags)"
    rescue JSON::ParserError => e
      abort("Error: Failed to parse JSON from #{file_path}: #{e.message}")
    end
  end

  private

  # Normalize text for comparison (whitespace and AsciiDoc formatting)
  # @param text [String] Text to normalize
  # @return [String] Normalized text
  def normalize_text(text)
    # First normalize whitespace, then strip AsciiDoc formatting
    strip_asciidoc_formatting(normalize_whitespace(text))
  end

  # Normalize whitespace for comparison
  # @param text [String] Text to normalize
  # @return [String] Text with normalized whitespace
  def normalize_whitespace(text)
    text.strip.gsub(/\s+/, ' ')
  end

  # Strip AsciiDoc formatting marks
  # @param text [String] Text to strip formatting from
  # @return [String] Text without AsciiDoc formatting
  def strip_asciidoc_formatting(text)
    result = text.dup

    # Remove bold: **text** (unconstrained) or *text* (constrained)
    result.gsub!(/\*\*([^\*]+?)\*\*/, '\1')
    result.gsub!(/\*([^\*]+?)\*/, '\1')

    # Remove italic: __text__ (unconstrained) or _text_ (constrained, not in middle of words)
    result.gsub!(/__([^_]+?)__/, '\1')
    result.gsub!(/(?<!\w)_([^_]+?)_(?!\w)/, '\1')

    # Remove monospace: `text`
    result.gsub!(/`([^`]+?)`/, '\1')

    # Remove superscript: ^text^
    result.gsub!(/\^([^\^]+?)\^/, '\1')

    # Remove subscript: ~text~
    result.gsub!(/~([^~]+?)~/, '\1')

    # Remove role-based formatting: [role]#text#
    result.gsub!(/\[[^\]]+\]#([^#]+?)#/, '\1')

    # Remove cross-references: <<anchor,text>> or <<anchor>>
    result.gsub!(/&lt;&lt;[^,&]+,([^&]+)&gt;&gt;/, '\1')
    result.gsub!(/&lt;&lt;[^&]+&gt;&gt;/, '')

    # Remove passthrough: +++text+++
    result.gsub!(/\+\+\+([^\+]+?)\+\+\+/, '\1')

    result.strip
  end

  # Truncate text for display
  # @param text [String] Text to truncate
  # @param max_length [Integer] Maximum length before truncation
  # @return [String] Truncated text
  def truncate_text(text, max_length = 100)
    return text if text.length <= max_length
    "#{text[0...max_length]}..."
  end
end

# Parse command-line arguments
def parse_options
  options = {
    update_reference: false,
    verbose: false
  }

  parser = OptionParser.new do |opts|
    opts.banner = "Usage: #{File.basename($0)} [options] REFERENCE_TAGS.json CURRENT_TAGS.json"
    opts.separator ""
    opts.separator "Detect changes in normative tags between two JSON files"
    opts.separator ""
    opts.separator "Options:"

    opts.on("-u", "--update-reference", "Update the reference tags file by adding any additions found in the current file") do
      options[:update_reference] = true
    end

    opts.on("-v", "--verbose", "Show verbose output with detailed processing information") do
      options[:verbose] = true
    end

    opts.on("-h", "--help", "Show this help message") do
      puts opts
      exit
    end
  end

  parser.parse!

  if ARGV.length != 2
    puts parser
    exit 1
  end

  options[:reference_file] = ARGV[0]
  options[:current_file] = ARGV[1]

  options
end

# Main execution
if __FILE__ == $0
  options = parse_options

  detector = TagChangeDetector.new(
    verbose: options[:verbose]
  )

  # Load both tag files
  reference_tags = detector.load_tags(options[:reference_file])
  current_tags = detector.load_tags(options[:current_file])

  # Detect changes
  changes = detector.detect_changes(reference_tags, current_tags)

  # Display changes
  detector.display_changes(changes, options[:reference_file], options[:current_file], options[:verbose])

  # Update reference file if requested
  if options[:update_reference]
    detector.update_tags_file(options[:reference_file], changes)
  end

  # Exit with appropriate status code
  # Return 0 if no changes or only additions
  # Return 1 if any modifications or deletions detected
  has_modifications_or_deletions = !changes.modified.empty? || !changes.deleted.empty?
  exit(has_modifications_or_deletions ? 1 : 0)
end

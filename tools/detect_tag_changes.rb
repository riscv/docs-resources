#!/usr/bin/env ruby
# frozen_string_literal: true

require "json"
require "optparse"

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
    @show_text = options[:show_text] || false
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

      # Apply prefix filter if specified
      if @prefix_filter
        tags = tags.select { |tag_name, _| tag_name.start_with?(@prefix_filter) }
      end

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
    (current_keys - reference_keys).each do |tag_name|
      changes.added[tag_name] = current_tags[tag_name]
    end

    # Find deleted tags (in reference but not in current)
    (reference_keys - current_keys).each do |tag_name|
      changes.deleted[tag_name] = reference_tags[tag_name]
    end

    # Find modified tags (in both but different text)
    (reference_keys & current_keys).each do |tag_name|
      reference_text = reference_tags[tag_name]
      current_text = current_tags[tag_name]

      if reference_text != current_text
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
  def display_changes(changes, reference_file, current_file)
    puts "=" * 80
    puts "Tag Changes Report"
    puts "=" * 80
    puts "Reference file: #{reference_file}"
    puts "Current file: #{current_file}"
    puts "=" * 80
    puts

    unless changes.any_changes?
      puts "No changes detected."
      return
    end

    # Display added tags
    unless changes.added.empty?
      puts "Added Tags (#{changes.added.size}):"
      puts "-" * 80
      changes.added.sort.each do |tag_name, text|
        puts "  + #{tag_name}"
        if @show_text
          puts "      Text: #{truncate_text(text)}"
          puts
        end
      end
      puts
    end

    # Display deleted tags
    unless changes.deleted.empty?
      puts "Deleted Tags (#{changes.deleted.size}):"
      puts "-" * 80
      changes.deleted.sort.each do |tag_name, text|
        puts "  - #{tag_name}"
        if @show_text
          puts "      Text: #{truncate_text(text)}"
          puts
        end
      end
      puts
    end

    # Display modified tags
    unless changes.modified.empty?
      puts "Modified Tags (#{changes.modified.size}):"
      puts "-" * 80
      changes.modified.sort.each do |tag_name, texts|
        puts "  ~ #{tag_name}"
        if @show_text
          puts "      Reference: #{truncate_text(texts['reference'])}"
          puts "      Current: #{truncate_text(texts['current'])}"
          puts
        end
      end
      puts
    end

    # Summary
    puts "=" * 80
    puts "Summary: #{changes.total_changes} total changes"
    puts "  Added:    #{changes.added.size}"
    puts "  Deleted:  #{changes.deleted.size}"
    puts "  Modified: #{changes.modified.size}"
    puts "=" * 80
  end

  # Update a tags file by adding new tags from additions
  # @param file_path [String] Path to the file to update
  # @param changes [TagChanges] Changes detected
  def update_tags_file(file_path, changes)
    if changes.added.empty?
      puts "No additions to merge into #{file_path}"
      return
    end

    unless File.exist?(file_path)
      abort("Error: Cannot update file - not found: #{file_path}")
    end

    begin
      data = JSON.parse(File.read(file_path))
      original_count = data["tags"].size

      # Add new tags
      changes.added.each do |tag_name, tag_text|
        data["tags"][tag_name] = tag_text
      end

      # Write back to file
      File.write(file_path, JSON.pretty_generate(data))
      new_count = data["tags"].size
      puts "Updated #{file_path}: added #{changes.added.size} new tags (#{original_count} -> #{new_count} total tags)"
    rescue JSON::ParserError => e
      abort("Error: Failed to parse JSON from #{file_path}: #{e.message}")
    end
  end

  private

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
    show_text: false,
    update_reference: false
  }

  parser = OptionParser.new do |opts|
    opts.banner = "Usage: #{File.basename($0)} [options] REFERENCE_TAGS.json CURRENT_TAGS.json"
    opts.separator ""
    opts.separator "Detect changes in normative tags between two JSON files"
    opts.separator ""
    opts.separator "Options:"

    opts.on("-t", "--show-text", "Show tag text in the output") do
      options[:show_text] = true
    end

    opts.on("-u", "--update-reference", "Update the reference tags file by adding any additions found in the current file") do
      options[:update_reference] = true
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
    show_text: options[:show_text]
  )

  # Load both tag files
  reference_tags = detector.load_tags(options[:reference_file])
  current_tags = detector.load_tags(options[:current_file])

  # Detect changes
  changes = detector.detect_changes(reference_tags, current_tags)

  # Display changes
  detector.display_changes(changes, options[:reference_file], options[:current_file])

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

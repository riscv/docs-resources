#!/usr/bin/env ruby
# frozen_string_literal: true

require "json"
require "optparse"

# Script to detect changes in normative tags extracted from asciidoc files
# Compares two tag JSON files and reports additions, deletions, and modifications

class TagChanges
  attr_reader :added, :deleted, :modified

  def initialize
    @added = {}      # Tags present in new but not in old
    @deleted = {}    # Tags present in old but not in new
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
  # @param old_tags [Hash<String, String>] Original tags
  # @param new_tags [Hash<String, String>] Updated tags
  # @return [TagChanges] Object containing all changes
  def detect_changes(old_tags, new_tags)
    changes = TagChanges.new

    old_keys = old_tags.keys.to_set
    new_keys = new_tags.keys.to_set

    # Find added tags (in new but not in old)
    (new_keys - old_keys).each do |tag_name|
      changes.added[tag_name] = new_tags[tag_name]
    end

    # Find deleted tags (in old but not in new)
    (old_keys - new_keys).each do |tag_name|
      changes.deleted[tag_name] = old_tags[tag_name]
    end

    # Find modified tags (in both but different text)
    (old_keys & new_keys).each do |tag_name|
      old_text = old_tags[tag_name]
      new_text = new_tags[tag_name]

      if old_text != new_text
        changes.modified[tag_name] = {
          "old" => old_text,
          "new" => new_text
        }
      end
    end

    changes
  end

  # Format and display changes
  # @param changes [TagChanges] Changes to display
  # @param old_file [String] Name of old file (for display)
  # @param new_file [String] Name of new file (for display)
  def display_changes(changes, old_file, new_file)
    puts "=" * 80
    puts "Tag Changes Report"
    puts "=" * 80
    puts "Old file: #{old_file}"
    puts "New file: #{new_file}"
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
          puts "      Old: #{truncate_text(texts['old'])}"
          puts "      New: #{truncate_text(texts['new'])}"
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

  # Export changes to a JSON file
  # @param changes [TagChanges] Changes to export
  # @param output_file [String] Path to output file
  def export_changes(changes, output_file)
    output = {
      "summary" => {
        "total_changes" => changes.total_changes,
        "added" => changes.added.size,
        "deleted" => changes.deleted.size,
        "modified" => changes.modified.size
      },
      "added" => changes.added,
      "deleted" => changes.deleted,
      "modified" => changes.modified
    }

    File.write(output_file, JSON.pretty_generate(output))
    puts "Changes exported to: #{output_file}"
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
    verbose: false,
    show_text: false,
    output_file: nil
  }

  parser = OptionParser.new do |opts|
    opts.banner = "Usage: #{File.basename($0)} [options] OLD_TAGS.json NEW_TAGS.json"
    opts.separator ""
    opts.separator "Detect changes in normative tags between two JSON files"
    opts.separator ""
    opts.separator "Options:"

    opts.on("-v", "--verbose", "Enable verbose output") do
      options[:verbose] = true
    end

    opts.on("-t", "--show-text", "Show tag text in the output") do
      options[:show_text] = true
    end

    opts.on("-o", "--output FILE", "Export changes to JSON file") do |file|
      options[:output_file] = file
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

  options[:old_file] = ARGV[0]
  options[:new_file] = ARGV[1]

  options
end

# Main execution
if __FILE__ == $0
  options = parse_options

  detector = TagChangeDetector.new(
    verbose: options[:verbose],
    show_text: options[:show_text]
  )

  # Load both tag files
  old_tags = detector.load_tags(options[:old_file])
  new_tags = detector.load_tags(options[:new_file])

  # Detect changes
  changes = detector.detect_changes(old_tags, new_tags)

  # Display changes
  detector.display_changes(changes, options[:old_file], options[:new_file])

  # Export if requested
  if options[:output_file]
    detector.export_changes(changes, options[:output_file])
  end

  # Exit with appropriate status code
  # Return 0 if no changes or only additions
  # Return 1 if any modifications or deletions detected
  has_modifications_or_deletions = !changes.modified.empty? || !changes.deleted.empty?
  exit(has_modifications_or_deletions ? 1 : 0)
end

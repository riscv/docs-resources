# frozen_string_literal: true

require 'asciidoctor/extensions'

require_relative 'asciidoctor-sail/sources'
require_relative 'asciidoctor-sail/macros'
require_relative 'asciidoctor-sail/highlighter'

Asciidoctor::Extensions.register do
  block_macro Asciidoctor::Sail::SourceBlockMacro
  include_processor Asciidoctor::Sail::SourceIncludeProcessor
  include_processor Asciidoctor::Sail::DocCommentIncludeProcessor
  include_processor Asciidoctor::Sail::WavedromIncludeProcessor
end

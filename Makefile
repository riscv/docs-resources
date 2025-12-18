# Makefile for tests for tools/scripts in docs-resources repository.
# Must be run in top-level directory of docs-resources repository.
#
# This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
# International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to
# Creative Commons, PO Box 1866, Mountain View, CA 94042, USA.
#
# SPDX-License-Identifier: CC-BY-SA-4.0
#
# This Makefile is designed to automate the process of running tests.
# Running with a preinstalled docker container is strongly recommended.
# Install by running:
#   docker pull riscvintl/riscv-docs-base-container-image:latest

# Directories all relative to the top-level.
CONVERTERS_DIR := converters
TOOLS_DIR := tools
BUILD_DIR := build
TESTS_DIR := tests
NORM_RULE_TESTS_DIR := $(TESTS_DIR)/norm-rule
TAGS_TESTS_DIR := $(TESTS_DIR)/tags
TAG_CHANGES_TESTS_DIR := $(TESTS_DIR)/tag-changes
NORM_RULE_DEF_DIR := $(NORM_RULE_TESTS_DIR)
NORM_RULE_EXPECTED_DIR := $(NORM_RULE_TESTS_DIR)/expected

# Ruby scripts being tested.
TAGS_BACKEND := tags.rb
CREATE_NORM_RULE_TOOL := $(TOOLS_DIR)/create_normative_rules.rb
CREATE_NORM_RULE_RUBY := ruby $(CREATE_NORM_RULE_TOOL)
DETECT_TAG_CHANGES_TOOL := $(TOOLS_DIR)/detect_tag_changes.rb
DETECT_TAG_CHANGES_RUBY := ruby $(DETECT_TAG_CHANGES_TOOL)

# Stuff for building mock standards document in HTML to have links into it.
DOCS = test
DOCS_HTML := $(addprefix $(BUILD_DIR)/, $(addsuffix .html, $(DOCS)))
ENV := LANG=C.utf8
ASCIIDOCTOR_HTML := $(ENV) asciidoctor

# Input and output file names
DOC_NORM_TAG_SUFFIX := -norm-tags.json
MAIN_TEST_ADOC_INPUT_FNAME := test.adoc
MAIN_TEST_HTML_FNAME := test.html
DUPLICATE_TEST_ADOC_INPUT_FNAME := duplicate.adoc
MAIN_NORM_TAGS_OUTPUT_FNAME := test$(DOC_NORM_TAG_SUFFIX)
DUPLICATE_NORM_TAGS_OUTPUT_FNAME := duplicate-tags.json
NORM_RULE_JSON_OUTPUT_FNAME := test-norm-rules.json
NORM_RULE_HTML_OUTPUT_FNAME := test-norm-rules.html
NORM_RULE_TAGS_NO_RULES_OUTPUT_FNAME := test-norm-rules_tags_no_rules.json

# Tag change detection test files
TAG_CHANGES_TEST_REFERENCE := reference.json
TAG_CHANGES_TEST_CURRENT := current.json
TAG_CHANGES_TEST_REFERENCE_PATH := $(TAG_CHANGES_TESTS_DIR)/$(TAG_CHANGES_TEST_REFERENCE)
TAG_CHANGES_TEST_CURRENT_PATH := $(TAG_CHANGES_TESTS_DIR)/$(TAG_CHANGES_TEST_CURRENT)

# Built output files
BUILT_MAIN_TEST_HTML := $(BUILD_DIR)/$(MAIN_TEST_HTML_FNAME)
BUILT_NORM_TAGS_MAIN := $(BUILD_DIR)/$(MAIN_NORM_TAGS_OUTPUT_FNAME)
BUILT_NORM_TAGS_DUPLICATE := $(BUILD_DIR)/$(DUPLICATE_NORM_TAGS_OUTPUT_FNAME)
BUILT_NORM_RULES_JSON := $(BUILD_DIR)/$(NORM_RULE_JSON_OUTPUT_FNAME)
BUILT_NORM_RULES_HTML := $(BUILD_DIR)/$(NORM_RULE_HTML_OUTPUT_FNAME)
BUILT_NORM_RULES_TAGS_NO_RULES := $(BUILD_DIR)/$(NORM_RULE_TAGS_NO_RULES_OUTPUT_FNAME)

# Copies of expected output files.
# Use make target "update-expected" to update from build dir contents.
EXPECTED_NORM_TAGS := $(NORM_RULE_EXPECTED_DIR)/$(MAIN_NORM_TAGS_OUTPUT_FNAME)
EXPECTED_NORM_RULES_JSON := $(NORM_RULE_EXPECTED_DIR)/$(NORM_RULE_JSON_OUTPUT_FNAME)
EXPECTED_NORM_RULES_HTML := $(NORM_RULE_EXPECTED_DIR)/$(NORM_RULE_HTML_OUTPUT_FNAME)

# Normative rule definition input YAML files.
GOOD_NORM_RULE_DEF_FILES := $(NORM_RULE_DEF_DIR)/test.yaml
BAD_NORM_RULE_DEF_FILES := $(NORM_RULE_DEF_DIR)/missing_tag_refs.yaml

# Add -t to each normative tag input filename and add prefix of "/" to make into absolute pathname.
NORM_TAG_FILE_ARGS := $(foreach relative_pname,$(BUILT_NORM_TAGS_MAIN),-t /$(relative_pname))

# Add -d to each normative rule definition filename
GOOD_NORM_RULE_DEF_ARGS := $(foreach relative_pname,$(GOOD_NORM_RULE_DEF_FILES),-d $(relative_pname))
BAD_NORM_RULE_DEF_ARGS := $(foreach relative_pname,$(BAD_NORM_RULE_DEF_FILES),-d $(relative_pname))

# Provide mapping from a stds doc norm tags JSON file to a URL that one can link to. Used to create links into stds doc.
NORM_RULE_DOC2URL_ARGS := $(foreach doc_name,$(DOCS),-tag2url /$(BUILD_DIR)/$(doc_name)$(DOC_NORM_TAG_SUFFIX) $(doc_name).html)

# Docker stuff
DOCKER_BIN ?= docker
SKIP_DOCKER ?= $(shell if command -v ${DOCKER_BIN}  >/dev/null 2>&1 ; then echo false; else echo true; fi)
DOCKER_IMG := riscvintl/riscv-docs-base-container-image:latest
ifneq ($(SKIP_DOCKER),true)
    DOCKER_IS_PODMAN = \
        $(shell ! ${DOCKER_BIN}  -v | grep podman >/dev/null ; echo $$?)
    ifeq "$(DOCKER_IS_PODMAN)" "1"
        # Modify the SELinux label for the host directory to indicate
        # that it can be shared with multiple containers. This is apparently
        # only required for Podman, though it is also supported by Docker.
        DOCKER_VOL_SUFFIX = :z
        DOCKER_EXTRA_VOL_SUFFIX = ,z
    else
        DOCKER_IS_ROOTLESS = \
            $(shell ! ${DOCKER_BIN} info -f '{{println .SecurityOptions}}' | grep rootless >/dev/null ; echo $$?)
        ifneq "$(DOCKER_IS_ROOTLESS)" "1"
            # Rooted Docker needs this flag so that the files it creates are
            # owned by the current user instead of root. Rootless docker does not
            # require it, and Podman doesn't either since it is always rootless.
            DOCKER_USER_ARG := --user $(shell id -u)
        endif
    endif

    DOCKER_CMD = \
        ${DOCKER_BIN} run --rm \
            -v ${PWD}/$@.workdir:/build${DOCKER_VOL_SUFFIX} \
            -v ${PWD}/${CONVERTERS_DIR}:/${CONVERTERS_DIR}:ro${DOCKER_EXTRA_VOL_SUFFIX} \
            -v ${PWD}/$(TOOLS_DIR):/$(TOOLS_DIR):ro${DOCKER_EXTRA_VOL_SUFFIX} \
            -v ${PWD}/$(TESTS_DIR):/$(TESTS_DIR):ro${DOCKER_EXTRA_VOL_SUFFIX} \
            -w /build \
            $(DOCKER_USER_ARG) \
            ${DOCKER_IMG} \
            /bin/sh -c
    DOCKER_QUOTE := "
else
    DOCKER_CMD = \
        cd $@.workdir &&
endif

WORKDIR_SETUP = \
    rm -rf $@.workdir && \
    mkdir -p $@.workdir && \
    ln -sfn ../../converters ../../tools ../../tests $@.workdir/

WORKDIR_TEARDOWN = \
    mv $@.workdir/$@ $@ && \
    rm -rf $@.workdir

ASCIIDOCTOR_TAGS := asciidoctor --backend tags --require=./$(CONVERTERS_DIR)/$(TAGS_BACKEND)

OPTIONS := --trace \
           -D build \
           --failure-level=WARN


# Default target
.PHONY: all
all: test

# Build tests and compare against expected
.PHONY: test
test: build-tests compare-tests test-tag-changes

# Build tests
.PHONY: build-tests build-test-tags build-test-norm-rules-json build-test-norm-rules-html build-test-tags-without-rules
build-tests: build-test-tags build-test-norm-rules-json build-test-norm-rules-html build-test-tags-without-rules
build-test-tags: $(BUILT_NORM_TAGS_MAIN) $(BUILT_NORM_TAGS_DUPLICATE)
build-test-norm-rules-json: $(BUILT_NORM_RULES_JSON)
build-test-norm-rules-html: $(BUILT_NORM_RULES_HTML)
build-test-tags-without-rules: $(BUILT_NORM_RULES_TAGS_NO_RULES)

# Compare tests against expected
.PHONY: compare-tests compare-test-tags compare-test-norm-rules-json compare-test-norm-rules-html
compare-tests: compare-test-tags compare-test-norm-rules-json compare-test-norm-rules-html

compare-test-tags: $(EXPECTED_NORM_TAGS) $(BUILT_NORM_TAGS_MAIN)
	@echo "CHECKING BUILT TAGS AGAINST EXPECTED TAGS"
	diff $(EXPECTED_NORM_TAGS) $(BUILT_NORM_TAGS_MAIN) && echo "diff PASSED" || (echo "diff FAILED"; exit 1)

compare-test-norm-rules: $(EXPECTED_NORM_RULES) $(BUILT_NORM_RULES)

compare-test-norm-rules-json: $(EXPECTED_NORM_RULES_JSON) $(BUILT_NORM_RULES_JSON)
	@echo "CHECKING JSON BUILT NORM RULES AGAINST EXPECTED NORM RULES"
	diff $(EXPECTED_NORM_RULES_JSON) $(BUILT_NORM_RULES_JSON) && echo "diff PASSED" || (echo "diff FAILED"; exit 1)

compare-test-norm-rules-html: $(EXPECTED_NORM_RULES_HTML) $(BUILT_NORM_RULES_HTML)
	@echo "CHECKING HTML BUILT NORM RULES AGAINST EXPECTED NORM RULES"
	diff $(EXPECTED_NORM_RULES_HTML) $(BUILT_NORM_RULES_HTML) && echo "diff PASSED" || (echo "diff FAILED"; exit 1)

# Test tag change detection
.PHONY: test-tag-changes test-tag-changes-basic test-tag-changes-verbose test-tag-changes-no-changes test-tag-changes-additions-only test-tag-changes-whitespace-only test-tag-changes-formatting-only test-tag-changes-update
test-tag-changes: test-tag-changes-basic test-tag-changes-verbose test-tag-changes-no-changes test-tag-changes-additions-only test-tag-changes-whitespace-only test-tag-changes-formatting-only test-tag-changes-update

test-tag-changes-basic: $(TAG_CHANGES_TEST_REFERENCE_PATH) $(TAG_CHANGES_TEST_CURRENT_PATH)
	@echo "TESTING TAG CHANGE DETECTION - BASIC OUTPUT (with modifications/deletions)"
	$(DETECT_TAG_CHANGES_RUBY) $(TAG_CHANGES_TEST_REFERENCE_PATH) $(TAG_CHANGES_TEST_CURRENT_PATH) && echo "test-tag-changes-basic FAILED (expected exit 1 for modifications/deletions)" || echo "test-tag-changes-basic PASSED"

test-tag-changes-verbose: $(TAG_CHANGES_TEST_REFERENCE_PATH) $(TAG_CHANGES_TEST_CURRENT_PATH)
	@echo "TESTING TAG CHANGE DETECTION - WITH VERBOSE OUTPUT (with modifications/deletions)"
	$(DETECT_TAG_CHANGES_RUBY) --verbose $(TAG_CHANGES_TEST_REFERENCE_PATH) $(TAG_CHANGES_TEST_CURRENT_PATH) && echo "test-tag-changes-verbose FAILED (expected exit 1 for modifications/deletions)" || echo "test-tag-changes-verbose PASSED"

test-tag-changes-no-changes: $(TAG_CHANGES_TEST_REFERENCE_PATH)
	@echo "TESTING TAG CHANGE DETECTION - NO CHANGES (expect exit 0)"
	$(DETECT_TAG_CHANGES_RUBY) $(TAG_CHANGES_TEST_REFERENCE_PATH) $(TAG_CHANGES_TEST_REFERENCE_PATH) && echo "test-tag-changes-no-changes PASSED" || echo "test-tag-changes-no-changes FAILED (no changes should return exit 0)"

test-tag-changes-additions-only: $(TAG_CHANGES_TEST_REFERENCE_PATH)
	@echo "TESTING TAG CHANGE DETECTION - ADDITIONS ONLY (expect exit 0)"
	$(DETECT_TAG_CHANGES_RUBY) $(TAG_CHANGES_TEST_REFERENCE_PATH) $(TAG_CHANGES_TESTS_DIR)/additions-only.json && echo "test-tag-changes-additions-only PASSED" || echo "test-tag-changes-additions-only FAILED (additions only should return exit 0)"

test-tag-changes-whitespace-only: $(TAG_CHANGES_TEST_REFERENCE_PATH)
	@echo "TESTING TAG CHANGE DETECTION - WHITESPACE ONLY (expect exit 0)"
	$(DETECT_TAG_CHANGES_RUBY) $(TAG_CHANGES_TEST_REFERENCE_PATH) $(TAG_CHANGES_TESTS_DIR)/whitespace-only.json && echo "test-tag-changes-whitespace-only PASSED" || echo "test-tag-changes-whitespace-only FAILED (whitespace-only changes should return exit 0)"

test-tag-changes-formatting-only: $(TAG_CHANGES_TEST_REFERENCE_PATH)
	@echo "TESTING TAG CHANGE DETECTION - FORMATTING ONLY (expect exit 0)"
	$(DETECT_TAG_CHANGES_RUBY) $(TAG_CHANGES_TEST_REFERENCE_PATH) $(TAG_CHANGES_TESTS_DIR)/formatting-only.json && echo "test-tag-changes-formatting-only PASSED" || echo "test-tag-changes-formatting-only FAILED (formatting-only changes should return exit 0)"

test-tag-changes-update: $(TAG_CHANGES_TEST_REFERENCE_PATH)
	@echo "TESTING TAG CHANGE DETECTION - UPDATE FILE"
	@cp -f $(TAG_CHANGES_TEST_REFERENCE_PATH) $(BUILD_DIR)/test-reference.json
	@$(DETECT_TAG_CHANGES_RUBY) $(BUILD_DIR)/test-reference.json $(TAG_CHANGES_TESTS_DIR)/additions-only.json --update-reference
	@ruby -rjson -e 'data = JSON.parse(File.read("$(BUILD_DIR)/test-reference.json")); exit(data["tags"].key?("norm:added-only-tag") ? 0 : 1)' || (echo "test-tag-changes-update FAILED (tag not added)"; exit 1)
	@$(DETECT_TAG_CHANGES_RUBY) $(BUILD_DIR)/test-reference.json $(TAG_CHANGES_TESTS_DIR)/additions-only.json > /dev/null 2>&1 && echo "test-tag-changes-update PASSED" || (echo "test-tag-changes-update FAILED (differences detected after update)"; exit 1)

# Update expected files from built files
.PHONY: update-expected update-test-tags update-test-norm-rules-json update-test-norm-rules-html
update-expected: update-test-tags update-test-norm-rules-json update-test-norm-rules-html

update-test-tags: $(BUILT_NORM_TAGS_MAIN)
	cp -f $(BUILT_NORM_TAGS_MAIN) $(EXPECTED_NORM_TAGS)

update-test-norm-rules-json: $(BUILT_NORM_RULES_JSON)
	cp -f $(BUILT_NORM_RULES_JSON) $(EXPECTED_NORM_RULES_JSON)

update-test-norm-rules-html: $(BUILT_NORM_RULES_HTML)
	cp -f $(BUILT_NORM_RULES_HTML) $(EXPECTED_NORM_RULES_HTML)

# Build normative tags with main adoc input
$(BUILT_NORM_TAGS_MAIN): $(NORM_RULE_TESTS_DIR)/$(MAIN_TEST_ADOC_INPUT_FNAME) $(CONVERTERS_DIR)/$(TAGS_BACKEND)
	$(WORKDIR_SETUP)
	$(DOCKER_CMD) $(DOCKER_QUOTE) $(ASCIIDOCTOR_TAGS) $(OPTIONS) -a tags-match-prefix='norm:' -a tags-output-suffix='-norm-tags.json' $< $(DOCKER_QUOTE)
	$(WORKDIR_TEARDOWN)

# Build normative tags with duplicate adoc input
# Asciidoctor should exit with a non-zero status and then we just "touch" the output file so it exists and make is happy.
$(BUILT_NORM_TAGS_DUPLICATE): $(TAGS_TESTS_DIR)/$(DUPLICATE_TEST_ADOC_INPUT_FNAME) $(CONVERTERS_DIR)/$(TAGS_BACKEND)
	$(WORKDIR_SETUP)
	$(DOCKER_CMD) $(DOCKER_QUOTE) $(ASCIIDOCTOR_TAGS) $(OPTIONS) -a tags-match-prefix='duplicate:' -a tags-output-suffix='-duplicate-tags.json' $< || touch $(BUILT_NORM_TAGS_DUPLICATE) $(DOCKER_QUOTE)
	$(WORKDIR_TEARDOWN)

# Build normative rules with JSON output format
$(BUILT_NORM_RULES_JSON): $(BUILT_NORM_TAGS_MAIN) $(GOOD_NORM_RULE_DEF_FILES)
	$(WORKDIR_SETUP)
	cp -f $(BUILT_NORM_TAGS_MAIN) $@.workdir
	mkdir -p $@.workdir/build
	$(DOCKER_CMD) $(DOCKER_QUOTE) $(CREATE_NORM_RULE_RUBY) -j $(NORM_TAG_FILE_ARGS) $(GOOD_NORM_RULE_DEF_ARGS) $(NORM_RULE_DOC2URL_ARGS) $@ $(DOCKER_QUOTE)
	$(WORKDIR_TEARDOWN)

$(BUILT_NORM_RULES_HTML): $(BUILT_MAIN_TEST_HTML) $(GOOD_NORM_RULE_DEF_FILES)
	$(WORKDIR_SETUP)
	cp -f $(BUILT_NORM_TAGS_MAIN) $@.workdir
	mkdir -p $@.workdir/build
	$(DOCKER_CMD) $(DOCKER_QUOTE) $(CREATE_NORM_RULE_RUBY) -h $(NORM_TAG_FILE_ARGS) $(GOOD_NORM_RULE_DEF_ARGS) $(NORM_RULE_DOC2URL_ARGS) $@ $(DOCKER_QUOTE)
	$(WORKDIR_TEARDOWN)

# This is the HTML file that represents the standards doc. THe norm rule HTML links into this HTML.
$(BUILT_MAIN_TEST_HTML) : $(NORM_RULE_TESTS_DIR)/$(MAIN_TEST_ADOC_INPUT_FNAME)
	$(WORKDIR_SETUP)
	mkdir -p $@.workdir/build
	$(DOCKER_CMD) $(DOCKER_QUOTE) $(ASCIIDOCTOR_HTML) -o $@ $< $(DOCKER_QUOTE)
	$(WORKDIR_TEARDOWN)

# Build normative rules with different YAML that should create an error due to tags without norm rules referencing them.
# Should exit with a non-zero status and then we just "touch" the output file so it exists and make is happy.
$(BUILT_NORM_RULES_TAGS_NO_RULES): $(BUILT_NORM_TAGS_MAIN) $(BAD_NORM_RULE_DEF_FILES)
	$(WORKDIR_SETUP)
	cp -f $(BUILT_NORM_TAGS_MAIN) $@.workdir
	mkdir -p $@.workdir/build
	$(DOCKER_CMD) $(DOCKER_QUOTE) $(CREATE_NORM_RULE_RUBY) $(NORM_TAG_FILE_ARGS) $(BAD_NORM_RULE_DEF_ARGS) $(NORM_RULE_DOC2URL_ARGS) $(BUILD_DIR)/bogus || touch $(BUILT_NORM_RULES_TAGS_NO_RULES) $(DOCKER_QUOTE)
	$(WORKDIR_TEARDOWN)

# Update docker image to latest
docker-pull-latest:
	${DOCKER_BIN} pull ${DOCKER_IMG}

clean:
	@echo "Cleaning up generated files..."
	rm -rf $(BUILD_DIR)
	@echo "Cleanup completed."

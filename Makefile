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
#   docker pull ghcr.io/riscv/riscv-docs-base-container-image:latest

# Directories all relative to the top-level.
CONVERTERS_DIR := converters
TOOLS_DIR := tools
BUILD_DIR := build
TESTS_DIR := tests
NORM_RULE_TESTS_DIR := $(TESTS_DIR)/norm-rule
TAGS_TESTS_DIR := $(TESTS_DIR)/tags
ADOC2HTML_TESTS_DIR := $(TESTS_DIR)/adoc2html
SHARED_UTILS_TESTS_DIR := $(TESTS_DIR)/shared_utils
TEXT_TO_HTML_TESTS_DIR := $(TESTS_DIR)/text_to_html
NORM_RULE_EXPECTED_DIR := $(NORM_RULE_TESTS_DIR)/expected

# Scripts being tested.
TAGS_BACKEND := tags.rb
CREATE_NORM_RULE_TOOL := $(TOOLS_DIR)/create_normative_rules.py
CREATE_NORM_RULE_PYTHON := python3 $(CREATE_NORM_RULE_TOOL)

# Stuff for building test standards document in HTML to have links into it.
DOCS = test-ch1 test-ch2
DOCS_HTML := $(addprefix $(BUILD_DIR)/, $(addsuffix .html, $(DOCS)))
ENV := LANG=C.utf8
ASCIIDOCTOR_HTML := $(ENV) asciidoctor

# Normative rule test files
DOC_NORM_TAG_SUFFIX := -norm-tags.json
TEST_CH1_INPUT_ADOC_FNAME := test-ch1.adoc
TEST_CH2_INPUT_ADOC_FNAME := test-ch2.adoc
TEST_CH1_HTML_FNAME := test-ch1.html
TEST_CH2_HTML_FNAME := test-ch2.html
TEST_CH1_NORM_TAGS_OUTPUT_FNAME := test-ch1$(DOC_NORM_TAG_SUFFIX)
TEST_CH2_NORM_TAGS_OUTPUT_FNAME := test-ch2$(DOC_NORM_TAG_SUFFIX)
NORM_RULE_JSON_OUTPUT_FNAME := test-norm-rules.json
NORM_RULE_HTML_OUTPUT_FNAME := test-norm-rules.html

# Tag extraction test files
DUPLICATE_TEST_ADOC_INPUT_FNAME := duplicate.adoc
DUPLICATE_NORM_TAGS_OUTPUT_FNAME := duplicate-tags.json
ADMONITION_TEST_ADOC_INPUT_FNAME := admonition.adoc
ADMONITION_NORM_TAGS_OUTPUT_FNAME := admonition-admonition-tags.json
ADMONITION_ERRORS_FNAME := admonition-errors.txt

# Built output files
BUILT_TEST_CH1_HTML_FNAME := $(BUILD_DIR)/$(TEST_CH1_HTML_FNAME)
BUILT_TEST_CH2_HTML_FNAME := $(BUILD_DIR)/$(TEST_CH2_HTML_FNAME)
BUILT_TEST_CH1_NORM_TAGS_FNAME := $(BUILD_DIR)/$(TEST_CH1_NORM_TAGS_OUTPUT_FNAME)
BUILT_TEST_CH2_NORM_TAGS_FNAME := $(BUILD_DIR)/$(TEST_CH2_NORM_TAGS_OUTPUT_FNAME)
BUILT_DUPLICATE_NORM_TAGS_FNAME := $(BUILD_DIR)/$(DUPLICATE_NORM_TAGS_OUTPUT_FNAME)
BUILT_ADMONITION_NORM_TAGS_FNAME := $(BUILD_DIR)/$(ADMONITION_NORM_TAGS_OUTPUT_FNAME)
BUILT_NORM_RULES_JSON := $(BUILD_DIR)/$(NORM_RULE_JSON_OUTPUT_FNAME)
BUILT_NORM_RULES_HTML := $(BUILD_DIR)/$(NORM_RULE_HTML_OUTPUT_FNAME)

# Combine separate fnames into lists.
BUILT_TEST_HTML_FNAMES := $(BUILT_TEST_CH1_HTML_FNAME) $(BUILT_TEST_CH2_HTML_FNAME)
BUILT_TEST_NORM_TAGS_FNAMES := $(BUILT_TEST_CH2_NORM_TAGS_FNAME) $(BUILT_TEST_CH1_NORM_TAGS_FNAME)

# Copies of expected output files.
# Use make target "update-expected" to update from build dir contents.
EXPECTED_CH1_NORM_TAGS := $(NORM_RULE_EXPECTED_DIR)/$(TEST_CH1_NORM_TAGS_OUTPUT_FNAME)
EXPECTED_CH2_NORM_TAGS := $(NORM_RULE_EXPECTED_DIR)/$(TEST_CH2_NORM_TAGS_OUTPUT_FNAME)
EXPECTED_NORM_RULES_JSON := $(NORM_RULE_EXPECTED_DIR)/$(NORM_RULE_JSON_OUTPUT_FNAME)
EXPECTED_NORM_RULES_HTML := $(NORM_RULE_EXPECTED_DIR)/$(NORM_RULE_HTML_OUTPUT_FNAME)

# Unit test scripts.
ADOC2HTML_TEST_SCRIPT := $(ADOC2HTML_TESTS_DIR)/test_adoc_to_html.py
SHARED_UTILS_TEST_SCRIPT := $(SHARED_UTILS_TESTS_DIR)/test_shared_utils.py
ADOC_TO_HTML_UNIT_TEST_SCRIPT := $(TEXT_TO_HTML_TESTS_DIR)/test_adoc_to_html_unit.py
DEF_TEXT_TO_HTML_UNIT_TEST_SCRIPT := $(TEXT_TO_HTML_TESTS_DIR)/test_def_text_to_html_unit.py
TAG_TEXT_TO_HTML_UNIT_TEST_SCRIPT := $(TEXT_TO_HTML_TESTS_DIR)/test_tag_text_to_html_unit.py

# Add -t to each normative tag input filename and add prefix of "/" to make into absolute pathname.
NORM_TAG_FILE_ARGS := $(foreach relative_pname,$(BUILT_TEST_NORM_TAGS_FNAMES),-t /$(relative_pname))

# Provide mapping from a stds doc norm tags JSON file to a URL that one can link to. Used to create links into stds doc.
NORM_RULE_DOC2URL_ARGS := $(foreach doc_name,$(DOCS),-tag2url /$(BUILD_DIR)/$(doc_name)$(DOC_NORM_TAG_SUFFIX) $(doc_name).html)

# Docker stuff
DOCKER_BIN ?= docker
SKIP_DOCKER ?= $(shell if command -v ${DOCKER_BIN}  >/dev/null 2>&1 ; then echo false; else echo true; fi)
DOCKER_IMG := ghcr.io/riscv/riscv-docs-base-container-image:latest
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
		mkdir -p $@.workdir/$(BUILD_DIR) && \
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
test: build-tests compare-tests test-adoc2html test-shared-utils test-text-to-html

# Build tests
.PHONY: build-tests build-test-tags build-test-norm-rules-json build-test-norm-rules-html
build-tests: build-test-tags build-test-norm-rules-json build-test-norm-rules-html
build-test-tags: $(BUILT_TEST_NORM_TAGS_FNAMES) $(BUILT_DUPLICATE_NORM_TAGS_FNAME) $(BUILT_ADMONITION_NORM_TAGS_FNAME)
build-test-norm-rules-json: $(BUILT_NORM_RULES_JSON)
build-test-norm-rules-html: $(BUILT_NORM_RULES_HTML)

# Compare tests against expected
.PHONY: compare-tests
compare-tests: compare-test-tags compare-test-norm-rules-json compare-test-norm-rules-html

.PHONY: compare-test-tags
compare-test-tags: compare-test-ch1-tags compare-test-ch2-tags

.PHONY: compare-test-ch1-tags
compare-test-ch1-tags: $(EXPECTED_CH1_NORM_TAGS) $(BUILT_TEST_CH1_NORM_TAGS_FNAME)
	@echo "CHECKING TEST-CH1 BUILT TAGS AGAINST EXPECTED TAGS"
	diff $(EXPECTED_CH1_NORM_TAGS) $(BUILT_TEST_CH1_NORM_TAGS_FNAME) && echo "diff PASSED" || (echo "diff FAILED"; exit 1)

.PHONY: compare-test-ch2-tags
compare-test-ch2-tags: $(EXPECTED_CH2_NORM_TAGS) $(BUILT_TEST_CH2_NORM_TAGS_FNAME)
	@echo "CHECKING TEST-CH2 BUILT TAGS AGAINST EXPECTED TAGS"
	diff $(EXPECTED_CH2_NORM_TAGS) $(BUILT_TEST_CH2_NORM_TAGS_FNAME) && echo "diff PASSED" || (echo "diff FAILED"; exit 1)

.PHONY: compare-test-norm-rules-json
compare-test-norm-rules-json: $(EXPECTED_NORM_RULES_JSON) $(BUILT_NORM_RULES_JSON)
	@echo "CHECKING JSON BUILT NORM RULES AGAINST EXPECTED NORM RULES"
	diff $(EXPECTED_NORM_RULES_JSON) $(BUILT_NORM_RULES_JSON) && echo "diff PASSED" || (echo "diff FAILED"; exit 1)

.PHONY: compare-test-norm-rules-html
compare-test-norm-rules-html: $(EXPECTED_NORM_RULES_HTML) $(BUILT_NORM_RULES_HTML)
	@echo "CHECKING HTML BUILT NORM RULES AGAINST EXPECTED NORM RULES"
	diff $(EXPECTED_NORM_RULES_HTML) $(BUILT_NORM_RULES_HTML) && echo "diff PASSED" || (echo "diff FAILED"; exit 1)

# Test Adoc2HTML converter behavior in isolation.
.PHONY: test-adoc2html
test-adoc2html: $(ADOC2HTML_TEST_SCRIPT) $(TOOLS_DIR)/adoc_to_html.py
	@echo "TESTING ADOC2HTML CONVERSION"
	python3 $(ADOC2HTML_TEST_SCRIPT) && echo "test-adoc2html PASSED" || (echo "test-adoc2html FAILED"; exit 1)

# Test shared_utils helpers in isolation.
.PHONY: test-shared-utils
test-shared-utils: $(SHARED_UTILS_TEST_SCRIPT) $(TOOLS_DIR)/shared_utils.py
	@echo "TESTING SHARED_UTILS HELPERS"
	python3 $(SHARED_UTILS_TEST_SCRIPT) && echo "test-shared-utils PASSED" || (echo "test-shared-utils FAILED"; exit 1)

# Test converter helpers in isolation.
.PHONY: test-text-to-html
test-text-to-html: test-adoc-to-html-unit test-def-text-to-html-unit test-tag-text-to-html-unit

.PHONY: test-adoc-to-html-unit
test-adoc-to-html-unit: $(ADOC_TO_HTML_UNIT_TEST_SCRIPT) $(TOOLS_DIR)/adoc_to_html.py
	@echo "TESTING ADOC_TO_HTML UNIT HELPERS"
	python3 $(ADOC_TO_HTML_UNIT_TEST_SCRIPT) && echo "test-adoc-to-html-unit PASSED" || (echo "test-adoc-to-html-unit FAILED"; exit 1)

.PHONY: test-def-text-to-html-unit
test-def-text-to-html-unit: $(DEF_TEXT_TO_HTML_UNIT_TEST_SCRIPT) $(TOOLS_DIR)/def_text_to_html.py $(TOOLS_DIR)/adoc_to_html.py
	@echo "TESTING DEF_TEXT_TO_HTML UNIT HELPERS"
	python3 $(DEF_TEXT_TO_HTML_UNIT_TEST_SCRIPT) && echo "test-def-text-to-html-unit PASSED" || (echo "test-def-text-to-html-unit FAILED"; exit 1)

.PHONY: test-tag-text-to-html-unit
test-tag-text-to-html-unit: $(TAG_TEXT_TO_HTML_UNIT_TEST_SCRIPT) $(TOOLS_DIR)/tag_text_to_html.py $(TOOLS_DIR)/def_text_to_html.py $(TOOLS_DIR)/adoc_to_html.py
	@echo "TESTING TAG_TEXT_TO_HTML UNIT HELPERS"
	python3 $(TAG_TEXT_TO_HTML_UNIT_TEST_SCRIPT) && echo "test-tag-text-to-html-unit PASSED" || (echo "test-tag-text-to-html-unit FAILED"; exit 1)

#
# Update expected files from built files
#

.PHONY: update-expected
update-expected: update-test-tags update-test-norm-rules-json update-test-norm-rules-html

.PHONY: update-test-tags
update-test-tags: update-test-ch1-tags update-test-ch2-tags

.PHONY: update-test-ch1-tags
update-test-ch1-tags: $(BUILT_TEST_CH1_NORM_TAGS_FNAME)
	cp -f $(BUILT_TEST_CH1_NORM_TAGS_FNAME) $(EXPECTED_CH1_NORM_TAGS)

.PHONY: update-test-ch2-tags
update-test-ch2-tags: $(BUILT_TEST_CH2_NORM_TAGS_FNAME)
	cp -f $(BUILT_TEST_CH2_NORM_TAGS_FNAME) $(EXPECTED_CH2_NORM_TAGS)

.PHONY: update-test-norm-rules-json
update-test-norm-rules-json: $(BUILT_NORM_RULES_JSON)
	cp -f $(BUILT_NORM_RULES_JSON) $(EXPECTED_NORM_RULES_JSON)

.PHONY: update-test-norm-rules-html
update-test-norm-rules-html: $(BUILT_NORM_RULES_HTML)
	cp -f $(BUILT_NORM_RULES_HTML) $(EXPECTED_NORM_RULES_HTML)

# Build normative tags with ch1 adoc input
$(BUILT_TEST_CH1_NORM_TAGS_FNAME): $(NORM_RULE_TESTS_DIR)/$(TEST_CH1_INPUT_ADOC_FNAME) $(CONVERTERS_DIR)/$(TAGS_BACKEND)
	$(WORKDIR_SETUP)
	$(DOCKER_CMD) $(DOCKER_QUOTE) $(ASCIIDOCTOR_TAGS) $(OPTIONS) -a tags-match-prefix='norm:' -a tags-output-suffix='-norm-tags.json' $< $(DOCKER_QUOTE)
	$(WORKDIR_TEARDOWN)

# Build normative tags with ch2 adoc input
$(BUILT_TEST_CH2_NORM_TAGS_FNAME): $(NORM_RULE_TESTS_DIR)/$(TEST_CH2_INPUT_ADOC_FNAME) $(CONVERTERS_DIR)/$(TAGS_BACKEND)
	$(WORKDIR_SETUP)
	$(DOCKER_CMD) $(DOCKER_QUOTE) $(ASCIIDOCTOR_TAGS) $(OPTIONS) -a tags-match-prefix='norm:' -a tags-output-suffix='-norm-tags.json' $< $(DOCKER_QUOTE)
	$(WORKDIR_TEARDOWN)

# Build normative tags with duplicate adoc input
# Asciidoctor should exit with a non-zero status and then we just "touch" the output file so it exists and make is happy.
$(BUILT_DUPLICATE_NORM_TAGS_FNAME): $(TAGS_TESTS_DIR)/$(DUPLICATE_TEST_ADOC_INPUT_FNAME) $(CONVERTERS_DIR)/$(TAGS_BACKEND)
	$(WORKDIR_SETUP)
	$(DOCKER_CMD) $(DOCKER_QUOTE) $(ASCIIDOCTOR_TAGS) $(OPTIONS) -a tags-match-prefix='duplicate:' -a tags-output-suffix='-duplicate-tags.json' $< || touch $(BUILT_DUPLICATE_NORM_TAGS_FNAME) $(DOCKER_QUOTE)
	$(WORKDIR_TEARDOWN)

# Build tags with admonition adoc input.
# Tags in or on an admonition are errors, so Asciidoctor must fail and report each "bad" tag.
$(BUILT_ADMONITION_NORM_TAGS_FNAME): $(TAGS_TESTS_DIR)/$(ADMONITION_TEST_ADOC_INPUT_FNAME) $(CONVERTERS_DIR)/$(TAGS_BACKEND)
	$(WORKDIR_SETUP)
	$(DOCKER_CMD) $(DOCKER_QUOTE) ! $(ASCIIDOCTOR_TAGS) $(OPTIONS) -a tags-match-prefix='admonition:' -a tags-output-suffix='-admonition-tags.json' $< 2> $(ADMONITION_ERRORS_FNAME) $(DOCKER_QUOTE)
	test "$$(grep -c "^asciidoctor: ERROR: Tag 'admonition:bad-.*' is in an admonition" $@.workdir/$(ADMONITION_ERRORS_FNAME))" -eq 5
	! grep -q "admonition:ok-" $@.workdir/$(ADMONITION_ERRORS_FNAME)
	$(WORKDIR_TEARDOWN)

# Build normative rules with JSON output format
$(BUILT_NORM_RULES_JSON): $(BUILT_TEST_NORM_TAGS_FNAMES) $(CREATE_NORM_RULE_TOOL)
	$(WORKDIR_SETUP)
	cp -f $(BUILT_TEST_NORM_TAGS_FNAMES) $@.workdir
	$(DOCKER_CMD) $(DOCKER_QUOTE) $(CREATE_NORM_RULE_TOOL) -j $(NORM_TAG_FILE_ARGS) $(NORM_RULE_DOC2URL_ARGS) $@ $(DOCKER_QUOTE)
	$(WORKDIR_TEARDOWN)

# Build normative rules with HTML output format
$(BUILT_NORM_RULES_HTML): $(BUILT_TEST_NORM_TAGS_FNAMES) $(CREATE_NORM_RULE_TOOL) $(BUILT_TEST_HTML_FNAMES)
	$(WORKDIR_SETUP)
	cp -f $(BUILT_TEST_NORM_TAGS_FNAMES) $@.workdir
	$(DOCKER_CMD) $(DOCKER_QUOTE) $(CREATE_NORM_RULE_TOOL) --html $(NORM_TAG_FILE_ARGS) $(NORM_RULE_DOC2URL_ARGS) $@ $(DOCKER_QUOTE)
	$(WORKDIR_TEARDOWN)

# This is the HTML file that represents the standards doc. THe norm rule HTML links into this HTML.
$(BUILT_TEST_CH1_HTML_FNAME) : $(NORM_RULE_TESTS_DIR)/$(TEST_CH1_INPUT_ADOC_FNAME)
	$(WORKDIR_SETUP)
	$(DOCKER_CMD) $(DOCKER_QUOTE) $(ASCIIDOCTOR_HTML) -o $@ $< $(DOCKER_QUOTE)
	$(WORKDIR_TEARDOWN)

# This is the HTML file that represents the standards doc. THe norm rule HTML links into this HTML.
$(BUILT_TEST_CH2_HTML_FNAME) : $(NORM_RULE_TESTS_DIR)/$(TEST_CH2_INPUT_ADOC_FNAME)
	$(WORKDIR_SETUP)
	$(DOCKER_CMD) $(DOCKER_QUOTE) $(ASCIIDOCTOR_HTML) -o $@ $< $(DOCKER_QUOTE)
	$(WORKDIR_TEARDOWN)

# Update docker image to latest
docker-pull-latest:
	${DOCKER_BIN} pull ${DOCKER_IMG}

clean:
	@echo "Cleaning up generated files..."
	rm -rf $(BUILD_DIR)
	@echo "Cleanup completed."

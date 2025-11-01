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
NORM_RULE_DEF_DIR := $(NORM_RULE_TESTS_DIR)
NORM_RULE_EXPECTED_DIR := $(NORM_RULE_TESTS_DIR)/expected

# Ruby scripts being tested.
TAGS_BACKEND := tags.rb
CREATE_NORM_RULE_TOOL := create_normative_rules.rb

# Input and output file names
MAIN_TEST_ADOC_INPUT_FNAME := test.adoc
DUPLICATE_TEST_ADOC_INPUT_FNAME := duplicate.adoc
MAIN_NORM_TAGS_OUTPUT_FNAME := test-norm-tags.json
DUPLICATE_NORM_TAGS_OUTPUT_FNAME := duplicate-tags.json
NORM_RULE_JSON_OUTPUT_FNAME := test-norm-rules.json
NORM_RULE_XLSX_OUTPUT_FNAME := test-norm-rules.xlsx
NORM_RULE_TAGS_NO_RULES_OUTPUT_FNAME := test-norm-rules_tags_no_rules.json

# Built output files
BUILT_NORM_TAGS_MAIN := $(BUILD_DIR)/$(MAIN_NORM_TAGS_OUTPUT_FNAME)
BUILT_NORM_TAGS_DUPLICATE := $(BUILD_DIR)/$(DUPLICATE_NORM_TAGS_OUTPUT_FNAME)
BUILT_NORM_RULES_JSON := $(BUILD_DIR)/$(NORM_RULE_JSON_OUTPUT_FNAME)
BUILT_NORM_RULES_XLSX := $(BUILD_DIR)/$(NORM_RULE_XLSX_OUTPUT_FNAME)
BUILT_NORM_RULES_TAGS_NO_RULES := $(BUILD_DIR)/$(NORM_RULE_TAGS_NO_RULES_OUTPUT_FNAME)

# Copies of expected output files.
# Use make target "update-expected" to update from build dir contents.
EXPECTED_NORM_TAGS := $(NORM_RULE_EXPECTED_DIR)/$(MAIN_NORM_TAGS_OUTPUT_FNAME)
EXPECTED_NORM_RULES_JSON := $(NORM_RULE_EXPECTED_DIR)/$(NORM_RULE_JSON_OUTPUT_FNAME)
EXPECTED_NORM_RULES_XLSX := $(NORM_RULE_EXPECTED_DIR)/$(NORM_RULE_XLSX_OUTPUT_FNAME)

# All normative rule definition input YAML files
NORM_RULE_DEF_FILES := $(wildcard $(NORM_RULE_DEF_DIR)/*.yaml)

# Add -t to each normative tag input filename and add prefix of "/" to make into absolute pathname.
NORM_TAG_FILE_ARGS := $(foreach relative_pname,$(BUILT_NORM_TAGS_MAIN),-t /$(relative_pname))

# Add -d to each normative rule definition filename
NORM_RULE_DEF_ARGS := $(foreach relative_pname,$(NORM_RULE_DEF_FILES),-d $(relative_pname))

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
test: build-tests compare-tests

# Build tests
.PHONY: build-tests build-test-tags build-test-norm-rules-json build-test-norm-rules-xlsx
build-tests: build-test-tags build-test-norm-rules-json build-test-norm-rules-xlsx build-test-tags-without-rules
build-test-tags: $(BUILT_NORM_TAGS_MAIN) $(BUILT_NORM_TAGS_DUPLICATE)
build-test-norm-rules-json: $(BUILT_NORM_RULES_JSON)
build-test-norm-rules-xlsx: $(BUILT_NORM_RULES_XLSX)
build-test-tags-without-rules: $(BUILT_NORM_RULES_TAGS_NO_RULES)

# Compare tests against expected
.PHONY: compare-tests
compare-tests: compare-test-tags compare-test-norm-rules-json

compare-test-tags: $(EXPECTED_NORM_TAGS) $(BUILT_NORM_TAGS_MAIN)
	@echo "CHECKING BUILT TAGS AGAINST EXPECTED TAGS"
	diff $(EXPECTED_NORM_TAGS) $(BUILT_NORM_TAGS_MAIN) && echo "diff PASSED" || (echo "diff FAILED"; exit 1)

compare-test-norm-rules: $(EXPECTED_NORM_RULES) $(BUILT_NORM_RULES)

compare-test-norm-rules-json: $(EXPECTED_NORM_RULES_JSON) $(BUILT_NORM_RULES_JSON)
	@echo "CHECKING JSON BUILT NORM RULES AGAINST EXPECTED NORM RULES"
	diff $(EXPECTED_NORM_RULES_JSON) $(BUILT_NORM_RULES_JSON) && echo "diff PASSED" || (echo "diff FAILED"; exit 1)

# Update expected files from built files
.PHONY: update-expected
update-expected: update-test-tags update-test-norm-rules-json update-test-norm-rules-xlsx

update-test-tags: $(BUILT_NORM_TAGS_MAIN)
	cp -f $(BUILT_NORM_TAGS_MAIN) $(EXPECTED_NORM_TAGS)

update-test-norm-rules-json: $(BUILT_NORM_RULES_JSON)
	cp -f $(BUILT_NORM_RULES_JSON) $(EXPECTED_NORM_RULES_JSON)

update-test-norm-rules-xlsx: $(BUILT_NORM_RULES_XLSX)
	cp -f $(BUILT_NORM_RULES_XLSX) $(EXPECTED_NORM_RULES_XLSX)

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
$(BUILT_NORM_RULES_JSON): $(BUILT_NORM_TAGS_MAIN) $(NORM_RULE_DEF_FILES)
	$(WORKDIR_SETUP)
	cp -f $(BUILT_NORM_TAGS_MAIN) $@.workdir
	mkdir -p $@.workdir/build
	$(DOCKER_CMD) $(DOCKER_QUOTE) ruby $(TOOLS_DIR)/$(CREATE_NORM_RULE_TOOL) -w $(NORM_TAG_FILE_ARGS) $(NORM_RULE_DEF_ARGS) $@ $(DOCKER_QUOTE)
	$(WORKDIR_TEARDOWN)

# Build normative rules with XLSX output format
$(BUILT_NORM_RULES_XLSX): $(BUILT_NORM_TAGS_MAIN) $(NORM_RULE_DEF_FILES)
	$(WORKDIR_SETUP)
	cp -f $(BUILT_NORM_TAGS_MAIN) $@.workdir
	mkdir -p $@.workdir/build
	$(DOCKER_CMD) $(DOCKER_QUOTE) ruby $(TOOLS_DIR)/$(CREATE_NORM_RULE_TOOL) -w -x $(NORM_TAG_FILE_ARGS) $(NORM_RULE_DEF_ARGS) $@ $(DOCKER_QUOTE)
	$(WORKDIR_TEARDOWN)

# Build normative rules that should create an error due to tags without norm rules referencing them
# Should exit with a non-zero status and then we just "touch" the output file so it exists and make is happy.
$(BUILT_NORM_RULES_TAGS_NO_RULES): $(BUILT_NORM_TAGS_MAIN) $(NORM_RULE_DEF_FILES)
	$(WORKDIR_SETUP)
	cp -f $(BUILT_NORM_TAGS_MAIN) $@.workdir
	mkdir -p $@.workdir/build
	$(DOCKER_CMD) $(DOCKER_QUOTE) ruby $(TOOLS_DIR)/$(CREATE_NORM_RULE_TOOL) $(NORM_TAG_FILE_ARGS) $(NORM_RULE_DEF_ARGS) $(BUILD_DIR)/bogus || touch $(BUILT_NORM_RULES_TAGS_NO_RULES) $(DOCKER_QUOTE)
	$(WORKDIR_TEARDOWN)

# Update docker image to latest
docker-pull-latest:
	${DOCKER_BIN} pull ${DOCKER_IMG}

clean:
	@echo "Cleaning up generated files..."
	rm -rf $(BUILD_DIR)
	@echo "Cleanup completed."

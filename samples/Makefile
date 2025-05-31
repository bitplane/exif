# Configuration
CACHE_DIR = .cache
DATA_DIR = data
DATA_DIRS = $(DATA_DIR)/device $(DATA_DIR)/software $(DATA_DIR)/tags $(DATA_DIR)/errors

# List of downloaders (add new ones here)
DOWNLOADERS = dpreview wikimedia

# Combined makefile from all sources
COMBINED_MK = $(CACHE_DIR)/combined.mk

.PHONY: all init configure clean clean-cache clean-data clean-venv backup help

# Default target - downloads all images
all: sources ## Generate all source makefiles

help: ## Show this help
	@egrep -h '\s##\s' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Include combined makefile
-include $(COMBINED_MK)

# Generate combined makefile
sources: $(COMBINED_MK) ## Generate combined makefile from all sources

# Build combined makefile from all params files
$(COMBINED_MK): $(foreach d,$(DOWNLOADERS),$(CACHE_DIR)/$(d).params) scripts/build_makefile.py
	./scripts/build_makefile.py $(DOWNLOADERS) > $@

# DPReview params generation
$(CACHE_DIR)/dpreview.params: $(CACHE_DIR)/dpreview.galleries scripts/dpreview/get_camera_names.sh | $(CACHE_DIR)
	@total=$$(wc -l < $<); \
	echo "Generating dpreview download params for $$total galleries..."; \
	count=0; \
	> $@.tmp; \
	while read -r line; do \
		url=$$(echo "$$line" | cut -f1); \
		title=$$(echo "$$line" | cut -f2); \
		camera=$$(echo "$$title" | scripts/dpreview/get_camera_names.sh); \
		echo "device/$$camera.jpg $$url" >> $@.tmp; \
		count=$$((count + 1)); \
		echo "[$$count/$$total]: $$camera"; \
	done < $< && mv $@.tmp $@
	@echo "Generated $$(wc -l < $@) dpreview params"

# Fetch gallery list from dpreview
$(CACHE_DIR)/dpreview.galleries: scripts/dpreview/get_gallery_list.py $(CACHE_DIR)/.venv-installed $(CACHE_DIR)/.dpreview.llama3-installed | $(CACHE_DIR)
	. .venv/bin/activate && python3 $< > $@.tmp && mv $@.tmp $@

# Run configuration check
configure: ## Check for required tools
	./configure

# Create virtual environment
.venv/bin/activate: scripts/venv.sh
	./scripts/venv.sh

# Install Python dependencies
$(CACHE_DIR)/.venv-installed: .venv/bin/activate requirements.txt | $(CACHE_DIR)
	. .venv/bin/activate && pip install -r requirements.txt
	@touch $@

# Install llama3 model for DPReview
$(CACHE_DIR)/.dpreview.llama3-installed: | $(CACHE_DIR)
	ollama pull llama3
	@touch $@

# Initialize virtual environment and install dependencies  
init: configure .venv/bin/activate $(CACHE_DIR)/.venv-installed $(CACHE_DIR)/.dpreview.llama3-installed ## Initialize environment and install dependencies

# Ensure directories exist
$(CACHE_DIR) $(DATA_DIRS):
	mkdir -p $@

# Pattern rule for extracting EXIF data
$(DATA_DIR)/%.exif: $(DATA_DIR)/%
	exiftool -j $< > $@

# Clean cache files
clean-cache: ## Remove cache files
	find $(CACHE_DIR) -type f ! -name '.gitkeep' -delete 2>/dev/null || true

# Clean data files
clean-data: ## Remove downloaded data files
	find $(DATA_DIR) -type f ! -name '.gitkeep' -delete 2>/dev/null || true
	find $(DATA_DIR) -type d -empty -delete 2>/dev/null || true

# Clean virtual environment
clean-venv: ## Remove Python virtual environment
	rm -rf .venv

# Clean everything
clean: clean-cache clean-data clean-venv ## Remove all generated files

# Wikimedia Commons samples
$(CACHE_DIR)/wikimedia.url: scripts/wikimedia/get_url.sh | $(CACHE_DIR)
	./scripts/wikimedia/get_url.sh $@

$(CACHE_DIR)/wikimedia.links: $(CACHE_DIR)/wikimedia.url scripts/wikimedia/download_and_extract.sh scripts/wikimedia/extract_links.php
	./scripts/wikimedia/download_and_extract.sh $$(cat $<) $@

$(CACHE_DIR)/wikimedia.params: $(CACHE_DIR)/wikimedia.links scripts/wikimedia/create_params.sh
	./scripts/wikimedia/create_params.sh $< $@

# Backup target
backup: ## Create timestamped backup of cache and EXIF data
	@mkdir -p backup
	@timestamp=$$(date +%Y-%m-%d_%H%M%S); \
	echo "Creating backup: $$timestamp"; \
	tar -cJf backup/$$timestamp.cache.tar.xz $(CACHE_DIR) && \
	echo "Created: backup/$$timestamp.cache.tar.xz"; \
	tar -cf backup/$$timestamp.data.tar --include='*.exif' --include='*.exif.errors' $(DATA_DIR) && \
	echo "Created: backup/$$timestamp.data.tar"


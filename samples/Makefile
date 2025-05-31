# Configuration
CACHE_DIR = .cache
DATA_DIR = data

# List of downloaders (add new ones here)
DOWNLOADERS = dpreview wikimedia

# Generate downloader command files
DOWNLOADER_COMMANDS = $(addprefix $(CACHE_DIR)/,$(addsuffix .commands,$(DOWNLOADERS)))

.PHONY: all init configure clean clean-all backup

# Default target - downloads all images
all: $(CACHE_DIR)/.downloaded

# Main download marker file - depends on all commands being executed
$(CACHE_DIR)/.downloaded: $(CACHE_DIR)/commands scripts/run.sh
	@echo "Executing all download commands..."
	@cat $(CACHE_DIR)/commands | scripts/run.sh
	@touch $@

# Concatenate all downloader command files
$(CACHE_DIR)/commands: $(DOWNLOADER_COMMANDS)
	@echo "Combining command files..."
	@cat $^ > $@
	@echo "Total commands: $$(wc -l < $@)"

# DPReview command generation
$(CACHE_DIR)/dpreview.commands: $(CACHE_DIR)/dpreview.galleries scripts/dpreview/get_camera_names.sh | $(CACHE_DIR)
	@total=$$(wc -l < $<); \
	echo "Generating dpreview download commands for $$total galleries..."; \
	count=0; \
	> $@.tmp; \
	while read -r line; do \
		url=$$(echo "$$line" | cut -f1); \
		title=$$(echo "$$line" | cut -f2); \
		camera=$$(echo "$$title" | scripts/dpreview/get_camera_names.sh); \
		echo "./scripts/dpreview/download_sample.py device/$$camera.jpg $$url" >> $@.tmp; \
		count=$$((count + 1)); \
		echo "[$$count/$$total]: $$camera"; \
	done < $< && mv $@.tmp $@
	@echo "Generated $$(wc -l < $@) dpreview commands"

# Fetch gallery list from dpreview
$(CACHE_DIR)/dpreview.galleries: scripts/dpreview/get_gallery_list.py .venv/bin/activate | $(CACHE_DIR)
	. .venv/bin/activate && python3 $< > $@.tmp && mv $@.tmp $@

# Run configuration check
configure:
	./configure

# Create virtual environment
.venv/bin/activate: scripts/venv.sh
	./scripts/venv.sh

# Initialize virtual environment and install dependencies  
init: configure .venv/bin/activate

# Ensure directories exist
$(CACHE_DIR) $(DATA_DIR)/device $(DATA_DIR)/software $(DATA_DIR)/tags $(DATA_DIR)/errors:
	mkdir -p $@

# Pattern rule for extracting EXIF data
$(DATA_DIR)/%.exif: $(DATA_DIR)/%
	exiftool -j $< > $@

# Clean up generated files (preserve .gitkeep files)
clean:
	find $(CACHE_DIR) -type f ! -name '.gitkeep' -delete 2>/dev/null || true
	find $(DATA_DIR) -type f ! -name '.gitkeep' -delete 2>/dev/null || true
	find $(DATA_DIR) -type d -empty -delete 2>/dev/null || true

# Clean everything including virtual environment
clean-all: clean
	rm -rf .venv

# Wikimedia Commons samples
$(CACHE_DIR)/wikimedia.url: scripts/wikimedia/get_url.sh | $(CACHE_DIR)
	./scripts/wikimedia/get_url.sh $@

$(CACHE_DIR)/wikimedia.links: $(CACHE_DIR)/wikimedia.url scripts/wikimedia/download_and_extract.sh scripts/wikimedia/extract_links.php
	./scripts/wikimedia/download_and_extract.sh $$(cat $<) $@

$(CACHE_DIR)/wikimedia.commands: $(CACHE_DIR)/wikimedia.links scripts/wikimedia/create_commands.sh
	./scripts/wikimedia/create_commands.sh $< $@

# Backup target
backup:
	@mkdir -p backup
	@timestamp=$$(date +%Y-%m-%d_%H%M%S); \
	echo "Creating backup: $$timestamp"; \
	tar -cJf backup/$$timestamp.cache.tar.xz $(CACHE_DIR) && \
	echo "Created: backup/$$timestamp.cache.tar.xz"; \
	tar -cf backup/$$timestamp.data.tar $(DATA_DIR) && \
	echo "Created: backup/$$timestamp.data.tar"

# Convenience targets
dpreview-list: $(CACHE_DIR)/dpreview.galleries
dpreview-commands: 
	rm -f $(CACHE_DIR)/dpreview.commands
	$(MAKE) $(CACHE_DIR)/dpreview.commands

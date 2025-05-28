# Configuration
CACHE_DIR = .cache
DATA_DIR = data
JPG_DIR = $(DATA_DIR)/jpg

# Define all image sources
DPREVIEW_GALLERIES = $(CACHE_DIR)/dpreview.com.galleries.tsv
DPREVIEW_SELECTED = $(CACHE_DIR)/dpreview.com.selected.tsv
DPREVIEW_IMAGES = $(shell [ -f $(DPREVIEW_SELECTED) ] && cut -f3 $(DPREVIEW_SELECTED) | sed 's,^,$(JPG_DIR)/,')

# All images from all sources
ALL_IMAGES = $(DPREVIEW_IMAGES)
ALL_EXIF = $(ALL_IMAGES:.jpg=.exif)

.PHONY: all init configure clean clean-all

# Default target
all: $(ALL_IMAGES)

# Run configuration check
configure:
	./configure

# Initialize virtual environment and install dependencies
init: configure
	python3 -m venv .venv
	. .venv/bin/activate && python3 -m pip install playwright==1.41.0
	. .venv/bin/activate && playwright install chromium

# Ensure directories exist
$(CACHE_DIR) $(JPG_DIR):
	mkdir -p $@

# Fetch gallery list from dpreview
$(DPREVIEW_GALLERIES): scripts/dpreview/get_gallery_list.py | $(CACHE_DIR)
	. .venv/bin/activate && python3 $< > $@

# Create selected galleries (25 random)
$(DPREVIEW_SELECTED): $(DPREVIEW_GALLERIES)
	shuf $< | head -25 | while IFS=$$'\t' read -r url title; do \
		camera=$$(echo "$$title" | scripts/dpreview/get_camera_names.sh); \
		echo "jpg\t$$url\t$$camera.jpg"; \
	done > $@
	@echo "Selected 25 random galleries from dpreview"

# Pattern rule for downloading images
$(JPG_DIR)/%.jpg: | $(JPG_DIR)
	@mkdir -p $$(dirname $@)
	@url=$$(grep -F "$*.jpg" $(DPREVIEW_SELECTED) | cut -f2); \
	if [ -n "$$url" ]; then \
		echo "Downloading $* from $$url"; \
		. .venv/bin/activate && python3 scripts/dpreview/download_sample.py "$$url" "$@"; \
	fi

# Pattern rule for extracting EXIF data
%.exif: %.jpg
	exiftool -j $< > $@

# Target to extract all EXIF data
exif: $(ALL_EXIF)

# Clean up generated files (preserve .gitignore files)
clean:
	find $(CACHE_DIR) -type f ! -name '.gitignore' -delete 2>/dev/null || true
	find $(DATA_DIR) -type f ! -name '.gitignore' -delete 2>/dev/null || true
	find $(DATA_DIR) -type d -empty -delete 2>/dev/null || true

# Clean everything including virtual environment
clean-all: clean
	rm -rf .venv

# Convenience targets
dpreview-list: $(DPREVIEW_GALLERIES)
dpreview-select: $(DPREVIEW_SELECTED)
dpreview: $(DPREVIEW_IMAGES)
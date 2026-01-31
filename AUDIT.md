# EncoreAuctions HiBid Tool - Functionality Audit

**Audit Date:** 2026-01-31
**Auditor:** Claude Code
**Tool Version:** Current (commit b8aa31e)

---

## Overview

This tool is a **production-grade web scraper and thumbnail processor** for EncoreAuctions HiBid auction catalogs. It consists of three main components:

| File | Purpose | Lines |
|------|---------|-------|
| `auction_tool.py` | CLI interface and orchestration | 110 |
| `scraper.py` | Playwright-based scraping engine | 427 |
| `thumbnails.py` | Image download and WebP conversion | 246 |

---

## What the Tool Does

### 1. Catalog Scraping (`scrape` command)

Extracts auction lot data from HiBid catalogs using a dual-mode architecture:

**Primary Mode (API Scraping):**
- Automatically detects JSON API endpoints during page load
- Monitors XHR/fetch requests for JSON responses containing lot data
- Handles pagination parameters (page, offset, size variants)
- Includes retry logic with exponential backoff

**Fallback Mode (DOM Scraping):**
- Activates when no API is detected
- Scrolls through infinite-scroll listings
- Supports next-page button pagination
- Uses CSS selectors: `.lot-tile`, `.lot-item`, `.lot-card`, `[data-lot-id]`

**Output:** JSON file with normalized lot data including:
- `auction_id`, `lot_id`, `title`, `subtitle`
- `category`, `current_bid`
- `lot_url`, `image_url`

### 2. Thumbnail Processing (`thumbs` command)

Downloads and optimizes lot images:
- Fetches lot page HTML to discover best image
- Priority order: `og:image` > `twitter:image` > JSON-LD > `<img>` tags
- Converts images to WebP format (320x320px @ 70% quality)
- Multi-threaded downloads (configurable workers)
- Resumable: skips existing non-empty files

---

## What Works Correctly

### CLI Interface
- Argument parsing and validation work correctly
- Help documentation is accurate and complete
- Mutually exclusive groups (`--auction-id` vs `--url`) function properly
- Output directories are created automatically

### Scraper Module
- Auction ID extraction from URLs works for multiple formats
- URL normalization handles relative and absolute URLs
- Lot item detection supports various JSON field naming conventions
- Deduplication by `(lot_id, lot_url)` tuple is functional
- Nested `lotNumber` dictionaries are handled (e.g., `{"value": "123"}`)
- Non-string subtitle values are handled gracefully
- Integer lot numbers are converted to strings

### Thumbnail Module
- Session retry strategy with exponential backoff works
- WebP conversion and thumbnail generation work correctly
- Srcset parsing correctly picks the largest image
- JSON-LD image extraction handles malformed JSON gracefully
- Image priority (og:image > twitter:image > img tags) is respected

---

## Issues Found

### Critical Issues

#### 1. Path Traversal Vulnerability (Security)
**Location:** `thumbnails.py:177`
**Issue:** `lot_id` is used directly in file paths without sanitization.
**Impact:** A malicious lot_id like `../../../etc/passwd` could write files outside the intended directory.
**Fix:** Sanitize lot_id to remove path separators and special characters.

```python
# Current (vulnerable):
output_path = output_dir / "img" / auction_id / f"{lot_id}.webp"

# Recommended:
import re
safe_lot_id = re.sub(r'[^\w\-.]', '_', lot_id)[:255]
output_path = output_dir / "img" / auction_id / f"{safe_lot_id}.webp"
```

#### 2. Data Loss in Deduplication
**Location:** `scraper.py:162`
**Issue:** Items with empty `lot_id` and `lot_url` are all deduplicated to a single item.
**Impact:** Multiple valid items without IDs could be lost.
**Fix:** Use a unique identifier or skip deduplication for items without proper keys.

### Performance Issues

#### 3. Session Created Per Item
**Location:** `thumbnails.py:181`
**Issue:** `_make_session()` is called inside `_process_item()`, creating a new HTTP session for every lot.
**Impact:** Connection pooling is defeated, causing unnecessary TCP handshakes.
**Fix:** Pass a shared session to worker threads or use `ThreadLocal` session storage.

#### 4. Ignores Existing `image_url` from JSON
**Location:** `thumbnails.py:183-188`
**Issue:** Even when `image_url` exists in the scraped JSON, the tool fetches the lot page HTML to discover images.
**Impact:** Unnecessary HTTP requests and slower processing.
**Fix:** Check and use `image_url` from JSON first, only fetch HTML as fallback.

```python
# Add at start of _process_item:
if item.get("image_url"):
    image_url = item["image_url"]
else:
    html = _fetch_html(session, lot_url)
    image_url = _select_best_image(base_url, html)
```

### Code Quality Issues

#### 5. Import Inside Function
**Location:** `scraper.py:303`
**Issue:** `import time` is inside the function body.
**Impact:** Minor performance penalty; violates Python conventions.
**Fix:** Move to module-level imports.

#### 6. Hardcoded Domain
**Location:** `scraper.py:352`
**Issue:** Default URL is hardcoded to `encoreauctions.hibid.com`.
**Impact:** Limits reusability for other HiBid auctions.
**Fix:** Make base URL configurable or remove the default.

### Missing Features

#### 7. No `requirements.txt`
**Issue:** Dependencies are documented in README but no pip-installable requirements file exists.
**Fix:** Add `requirements.txt`:
```
playwright>=1.40.0
beautifulsoup4>=4.12.0
lxml>=5.0.0
requests>=2.31.0
pillow>=10.0.0
```

#### 8. No Input Validation for `--workers`
**Location:** `auction_tool.py:56`
**Issue:** Workers can be set to 0 or negative values.
**Fix:** Add validation: `type=int, default=6, choices=range(1, 33)`

---

## Improvement Opportunities

### High Priority

1. **Add input sanitization** for lot_id to prevent path traversal
2. **Reuse HTTP sessions** across thumbnail downloads
3. **Use existing `image_url`** from JSON before fetching HTML
4. **Add `requirements.txt`** for reproducible installations

### Medium Priority

5. **Add progress bar** using `tqdm` for better UX
6. **Add `--dry-run` option** to preview operations without making changes
7. **Add image caching** to avoid re-downloading unchanged images
8. **Support custom User-Agent** via command-line flag
9. **Add JSON schema validation** for input files

### Low Priority

10. **Add structured logging** with configurable verbosity levels
11. **Add unit tests** with pytest and mock HTTP responses
12. **Add GitHub Actions CI** for automated testing
13. **Support other HiBid-based auction sites** via configurable base URL
14. **Add rate limiting** to prevent overwhelming target servers
15. **Add Dockerfile** for containerized deployment

---

## Test Results

All utility function tests passed:

```
✅ _extract_auction_id - Extracts IDs from URLs correctly
✅ _normalize_url - Handles relative/absolute URLs
✅ _find_lot_items - Locates lot arrays in JSON
✅ _coerce_item - Normalizes varying field names
✅ _dedupe_items - Removes duplicate lots
✅ _safe_int - Handles type coercion safely
✅ _load_items - Parses JSON input files
✅ _pick_srcset - Selects largest srcset image
✅ _extract_img_candidates - Finds images in HTML
✅ _extract_json_ld_images - Parses structured data
✅ _select_best_image - Prioritizes image sources correctly
```

CLI functionality verified:
- `--help` displays correct usage
- Subcommand help is accurate
- Argument validation works

---

## Summary

| Category | Count |
|----------|-------|
| Working Features | 12+ |
| Critical Issues | 2 |
| Performance Issues | 2 |
| Code Quality Issues | 2 |
| Missing Features | 2 |
| Improvement Ideas | 15 |

**Overall Assessment:** The tool is well-architected with good error handling and retry logic. The main concerns are the path traversal vulnerability and performance issues in the thumbnail processor. With the fixes above, this would be a solid production tool.

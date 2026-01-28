# EncoreAuctions HiBid Catalog Tool

Production-grade scraper and thumbnail helper for EncoreAuctions HiBid catalogs. It produces JSON suited for a separate categorization step, plus optional thumbnail downloads for GitHub Pages.

## Features
- **Playwright-based** scraper with automatic fallback to DOM pagination when API endpoints are unavailable.
- **Robust output** JSON format with stable keys and an optional auction label.
- **Thumbnail downloader** that scrapes lot pages (requests + BeautifulSoup) and converts images to WebP.
- **Retry/backoff** for network errors and clear progress logging.

## Setup
```bash
pip install playwright beautifulsoup4 lxml requests pillow
python -m playwright install
```

## Weekly Workflow (Option A)
1. Scrape Sunday auction + Monday auction:
   ```bash
   py auction_tool.py scrape --auction-id 702773 --label Sunday
   py auction_tool.py scrape --auction-id 702774 --label Monday
   ```
2. Raw JSONs are written to `auction_data/auction_<id>.json`.
3. Upload those JSONs to your separate assistant for categorization.
4. Receive categorized JSON + HTML back. (This tool does **not** categorize.)

## CLI Usage
### Scrape
```bash
py auction_tool.py scrape --auction-id 702773 --label Sunday
py auction_tool.py scrape --url "https://encoreauctions.hibid.com/catalog/702773/" --label Sunday
py auction_tool.py scrape --auction-id 702773 --visible
```

Output format:
```json
{
  "auction_id": "702773",
  "scraped_at": "2024-01-01T12:00:00+00:00",
  "auction_label": "Sunday",
  "items": [
    {
      "auction_id": "702773",
      "lot_id": "123",
      "title": "Lot title",
      "subtitle": "Short description",
      "category": "",
      "current_bid": null,
      "lot_url": "https://encoreauctions.hibid.com/lot/123",
      "image_url": "https://.../image.jpg"
    }
  ]
}
```

### Thumbnails
```bash
py auction_tool.py thumbs --auction-id 702773 --in auction_data/auction_702773.json --out auction_site --workers 6
```
This writes images to:
```
auction_site/img/<auction_id>/<lot_id>.webp
```

## Troubleshooting
- **No API detected**: The scraper will fall back to DOM pagination/infinite scroll.
- **Slow pages / missing items**: Run with `--visible` to watch pagination and confirm items load.
- **Thumbnails missing**: The downloader scans `og:image`, `twitter:image`, JSON-LD, and visible `<img>` tags. Some lots may not publish images.
- **Resumable downloads**: Existing non-zero `.webp` files are skipped.

## Notes on HiBid Behavior
- The scraper never alters catalog slugs. It only uses the auction ID or URL you provide.
- Pagination is verified by item count changes and next-page state.
- Output keys are stable and forward-compatible; unknown JSON keys are ignored on read.

#!/usr/bin/env python3
"""EncoreAuctions HiBid catalog scraper + thumbnail downloader."""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path

from scraper import scrape_auction
from thumbnails import download_thumbnails


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scrape EncoreAuctions HiBid catalogs and download thumbnails."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scrape_parser = subparsers.add_parser("scrape", help="Scrape a HiBid catalog.")
    scrape_group = scrape_parser.add_mutually_exclusive_group(required=True)
    scrape_group.add_argument("--auction-id", help="Auction ID (numeric)")
    scrape_group.add_argument("--url", help="Full catalog URL")
    scrape_parser.add_argument("--label", help="Auction label (e.g., Sunday/Monday)")
    scrape_parser.add_argument(
        "--visible",
        action="store_true",
        help="Run Playwright in headed mode for debugging.",
    )
    scrape_parser.add_argument(
        "--out",
        type=Path,
        default=Path("auction_data"),
        help="Output directory for JSON files.",
    )

    thumbs_parser = subparsers.add_parser(
        "thumbs", help="Download and process thumbnails for auction lots."
    )
    thumbs_parser.add_argument("--auction-id", required=True, help="Auction ID")
    thumbs_parser.add_argument(
        "--in",
        dest="input_json",
        type=Path,
        required=True,
        help="Input JSON file produced by scrape.",
    )
    thumbs_parser.add_argument(
        "--out",
        type=Path,
        default=Path("auction_site"),
        help="Output directory for thumbnails (auction_site).",
    )
    thumbs_parser.add_argument(
        "--workers",
        type=int,
        default=6,
        help="Number of concurrent download workers.",
    )

    return parser


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s: %(message)s",
    )


def main() -> None:
    configure_logging()
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "scrape":
        output_dir = args.out
        output_dir.mkdir(parents=True, exist_ok=True)
        result = asyncio.run(
            scrape_auction(
                auction_id=args.auction_id,
                catalog_url=args.url,
                label=args.label,
                visible=args.visible,
            )
        )
        output_path = output_dir / f"auction_{result['auction_id']}.json"
        output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        logging.info("Saved JSON to %s", output_path)
    elif args.command == "thumbs":
        summary = download_thumbnails(
            auction_id=args.auction_id,
            input_json=args.input_json,
            output_dir=args.out,
            workers=args.workers,
        )
        logging.info(
            "Thumbnails complete: total=%s downloaded=%s skipped=%s failed=%s",
            summary["total"],
            summary["downloaded"],
            summary["skipped"],
            summary["failed"],
        )
    else:
        parser.error("Unknown command")


if __name__ == "__main__":
    main()

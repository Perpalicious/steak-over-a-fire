from __future__ import annotations

import io
import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from PIL import Image
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


@dataclass
class ThumbSummary:
    total: int
    downloaded: int
    skipped: int
    failed: int


def _load_items(input_json: Path) -> List[Dict[str, Any]]:
    data = json.loads(input_json.read_text(encoding="utf-8"))
    return data.get("items", []) if isinstance(data, dict) else []


def _make_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (compatible; EncoreAuctionsBot/1.0)",
            "Accept": "text/html,application/xhtml+xml",
        }
    )
    return session


def _extract_json_ld_images(soup: BeautifulSoup) -> List[str]:
    images = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or "")
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            image = data.get("image")
            if isinstance(image, str):
                images.append(image)
            elif isinstance(image, list):
                images.extend([img for img in image if isinstance(img, str)])
        elif isinstance(data, list):
            for entry in data:
                if isinstance(entry, dict) and isinstance(entry.get("image"), str):
                    images.append(entry["image"])
    return images


def _pick_srcset(srcset: str) -> Optional[str]:
    candidates = []
    for entry in srcset.split(","):
        parts = entry.strip().split()
        if not parts:
            continue
        url = parts[0]
        size = 0
        if len(parts) > 1 and parts[1].endswith("w"):
            try:
                size = int(parts[1].rstrip("w"))
            except ValueError:
                size = 0
        candidates.append((size, url))
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[0])[1]


def _extract_img_candidates(soup: BeautifulSoup) -> List[str]:
    candidates = []
    for img in soup.find_all("img"):
        for attr in ("data-src", "src"):
            if img.get(attr):
                candidates.append(img.get(attr))
        if img.get("srcset"):
            best = _pick_srcset(img.get("srcset"))
            if best:
                candidates.append(best)
        style = img.get("style") or ""
        match = re.search(r"background-image:\s*url\(['\"]?(.*?)['\"]?\)", style)
        if match:
            candidates.append(match.group(1))
    return candidates


def _resolve_url(base: str, url: str) -> str:
    return urljoin(base, url)


def _select_best_image(base_url: str, html: str) -> Optional[str]:
    soup = BeautifulSoup(html, "lxml")
    meta_candidates = []
    for prop in ("og:image", "twitter:image"):
        tag = soup.find("meta", attrs={"property": prop}) or soup.find(
            "meta", attrs={"name": prop}
        )
        if tag and tag.get("content"):
            meta_candidates.append(tag["content"])
    json_ld = _extract_json_ld_images(soup)
    img_candidates = _extract_img_candidates(soup)

    for candidate_list in (meta_candidates, json_ld, img_candidates):
        for candidate in candidate_list:
            if candidate:
                return _resolve_url(base_url, candidate)
    return None


def _fetch_html(session: requests.Session, url: str) -> Optional[str]:
    for attempt in range(3):
        try:
            response = session.get(url, timeout=20)
            response.raise_for_status()
            return response.text
        except Exception as exc:
            wait = 0.5 * (2 ** attempt)
            logging.warning("HTML fetch failed (%s): %s", url, exc)
            time.sleep(wait)
    return None


def _download_image(session: requests.Session, url: str) -> Optional[bytes]:
    for attempt in range(3):
        try:
            response = session.get(url, timeout=30)
            response.raise_for_status()
            return response.content
        except Exception as exc:
            wait = 0.5 * (2 ** attempt)
            logging.warning("Image download failed (%s): %s", url, exc)
            time.sleep(wait)
    return None


def _save_webp(image_bytes: bytes, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(io.BytesIO(image_bytes)) as img:
        img = img.convert("RGB")
        img.thumbnail((320, 320))
        img.save(output_path, format="WEBP", quality=70, method=6)


def _process_item(
    item: Dict[str, Any],
    auction_id: str,
    output_dir: Path,
) -> Tuple[str, str]:
    lot_id = str(item.get("lot_id") or "").strip()
    lot_url = item.get("lot_url") or ""
    if not lot_id or not lot_url:
        return "skipped", "missing lot_id or lot_url"

    output_path = output_dir / "img" / auction_id / f"{lot_id}.webp"
    if output_path.exists() and output_path.stat().st_size > 0:
        return "skipped", "already exists"

    session = _make_session()
    time.sleep(0.1)
    html = _fetch_html(session, lot_url)
    if not html:
        return "failed", "html fetch failed"

    base_url = f"{urlparse(lot_url).scheme}://{urlparse(lot_url).netloc}"
    image_url = _select_best_image(base_url, html)
    if not image_url:
        return "failed", "no image candidate"

    image_bytes = _download_image(session, image_url)
    if not image_bytes:
        return "failed", "image download failed"

    try:
        _save_webp(image_bytes, output_path)
    except Exception as exc:
        return "failed", f"image processing failed: {exc}"

    return "downloaded", "ok"


def download_thumbnails(
    auction_id: str,
    input_json: Path,
    output_dir: Path,
    workers: int = 6,
) -> Dict[str, int]:
    items = _load_items(input_json)
    total = len(items)
    downloaded = 0
    skipped = 0
    failed = 0

    output_dir.mkdir(parents=True, exist_ok=True)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(_process_item, item, auction_id, output_dir): item
            for item in items
        }
        for future in as_completed(futures):
            status, reason = future.result()
            if status == "downloaded":
                downloaded += 1
            elif status == "skipped":
                skipped += 1
            else:
                failed += 1
            if (downloaded + skipped + failed) % 25 == 0:
                logging.info(
                    "Progress: %s/%s (downloaded=%s skipped=%s failed=%s)",
                    downloaded + skipped + failed,
                    total,
                    downloaded,
                    skipped,
                    failed,
                )

    return {
        "total": total,
        "downloaded": downloaded,
        "skipped": skipped,
        "failed": failed,
    }

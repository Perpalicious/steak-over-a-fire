from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

import requests
from playwright.async_api import async_playwright

DEFAULT_TIMEOUT_MS = 30000


@dataclass
class ApiCandidate:
    url: str
    method: str
    headers: Dict[str, str]
    post_data: Optional[str]
    sample_items: int


def _extract_auction_id(auction_id: Optional[str], catalog_url: Optional[str]) -> str:
    if auction_id:
        return str(auction_id)
    if not catalog_url:
        raise ValueError("Provide auction_id or catalog_url")
    match = re.search(r"/catalog/(\d+)", catalog_url)
    if match:
        return match.group(1)
    match = re.search(r"auctionId=(\d+)", catalog_url)
    if match:
        return match.group(1)
    raise ValueError("Unable to extract auction id from URL")


def _normalize_url(base: str, href: Optional[str]) -> str:
    if not href:
        return ""
    return urljoin(base, href)


def _find_lot_items(data: Any) -> List[Dict[str, Any]]:
    candidates: List[List[Dict[str, Any]]] = []

    def walk(obj: Any) -> None:
        if isinstance(obj, list):
            if obj and all(isinstance(item, dict) for item in obj):
                keys = {k.lower() for k in obj[0].keys()}
                if {"lotnumber", "lotid", "lot_id", "lot"} & keys:
                    candidates.append(obj)  # type: ignore[arg-type]
            for item in obj:
                walk(item)
        elif isinstance(obj, dict):
            for value in obj.values():
                walk(value)

    walk(data)
    if not candidates:
        return []
    return max(candidates, key=len)


def _coerce_item(raw: Dict[str, Any], auction_id: str, base_url: str) -> Dict[str, Any]:
    lot_id = raw.get("lotNumber") or raw.get("lot_number") or raw.get("lotId") or raw.get("lot_id")
    if isinstance(lot_id, dict):
        lot_id = lot_id.get("value")
    title = raw.get("title") or raw.get("lotTitle") or raw.get("name") or ""
    subtitle = raw.get("subtitle") or raw.get("shortDescription") or raw.get("description") or ""
    lot_url = raw.get("lotUrl") or raw.get("url") or raw.get("detailUrl") or ""
    image_url = raw.get("imageUrl") or raw.get("thumbnailUrl") or raw.get("image") or ""
    current_bid = raw.get("currentBid") or raw.get("bid") or raw.get("price")
    category = raw.get("category") or raw.get("categoryName") or raw.get("catalogCategory")

    return {
        "auction_id": auction_id,
        "lot_id": str(lot_id) if lot_id is not None else "",
        "title": title.strip(),
        "subtitle": subtitle.strip() if isinstance(subtitle, str) else "",
        "category": category or "",
        "current_bid": current_bid,
        "lot_url": _normalize_url(base_url, lot_url),
        "image_url": _normalize_url(base_url, image_url),
    }


def _parse_response_for_items(data: Any) -> Tuple[List[Dict[str, Any]], Optional[int]]:
    items = _find_lot_items(data)
    total = None
    if isinstance(data, dict):
        for key in ("totalLotCount", "total", "totalLots", "totalCount"):
            if key in data:
                total = data.get(key)
                break
        if total is None:
            for value in data.values():
                if isinstance(value, dict):
                    for key in ("totalLotCount", "total", "totalLots", "totalCount"):
                        if key in value:
                            total = value.get(key)
                            break
    return items, total


def _build_session_from_playwright(headers: Dict[str, str], cookies: List[Dict[str, Any]]) -> requests.Session:
    session = requests.Session()
    session.headers.update(headers)
    for cookie in cookies:
        session.cookies.set(cookie["name"], cookie["value"], domain=cookie.get("domain"))
    return session


def _extract_pagination_params(url: str, post_data: Optional[str]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    query_params = {k: v[0] for k, v in query.items()}

    body_params: Dict[str, Any] = {}
    if post_data:
        try:
            body_params = json.loads(post_data)
        except json.JSONDecodeError:
            body_params = dict(parse_qs(post_data))
    return query_params, body_params


def _update_pagination(params: Dict[str, Any], page: int, size: int) -> bool:
    updated = False
    for key in ("page", "pageIndex", "pageNumber", "pageNum", "pg"):
        if key in params:
            params[key] = str(page)
            updated = True
    for key in ("start", "offset"):
        if key in params:
            params[key] = str(page * size)
            updated = True
    for key in ("size", "pageSize", "limit", "perPage", "take"):
        if key in params:
            params[key] = str(size)
            updated = True
    return updated


def _apply_query(url: str, params: Dict[str, Any]) -> str:
    parsed = urlparse(url)
    query = urlencode(params, doseq=True)
    return urlunparse(parsed._replace(query=query))


def _log_progress(message: str) -> None:
    logging.info(message)


def _dedupe_items(items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    result = []
    for item in items:
        key = (item.get("lot_id"), item.get("lot_url"))
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


async def _extract_cards_from_page(page, base_url: str, auction_id: str) -> List[Dict[str, Any]]:
    selectors = [
        ".lot-tile",
        ".lot-item",
        ".lot-card",
        ".auction-lot-item",
        "[data-lot-id]",
    ]
    cards = []
    for selector in selectors:
        cards = await page.query_selector_all(selector)
        if cards:
            break
    items = []
    for card in cards:
        lot_id = ""
        if await card.get_attribute("data-lot-id"):
            lot_id = await card.get_attribute("data-lot-id") or ""
        title = ""
        title_node = await card.query_selector(".lot-title, .lot-desc, .title, h3, h4")
        if title_node:
            title = (await title_node.inner_text()).strip()
        lot_num_node = await card.query_selector(".lot-number, .lot-num, .lot-no")
        if lot_num_node and not lot_id:
            lot_id = (await lot_num_node.inner_text()).strip()
        link_node = await card.query_selector("a")
        lot_url = _normalize_url(
            base_url, await link_node.get_attribute("href") if link_node else ""
        )
        img_node = await card.query_selector("img")
        image_url = _normalize_url(
            base_url, await img_node.get_attribute("src") if img_node else ""
        )
        if img_node and not image_url:
            image_url = _normalize_url(base_url, await img_node.get_attribute("data-src"))
        items.append(
            {
                "auction_id": auction_id,
                "lot_id": lot_id,
                "title": title,
                "subtitle": "",
                "category": "",
                "current_bid": None,
                "lot_url": lot_url,
                "image_url": image_url,
            }
        )
    return items


async def _is_next_enabled(page) -> Optional[Any]:
    next_selectors = [
        "a[rel='next']",
        ".pagination .next a",
        ".pagination .next button",
        "button[aria-label='Next']",
    ]
    for selector in next_selectors:
        node = await page.query_selector(selector)
        if node:
            if await node.is_disabled():
                return None
            return node
    return None


def _safe_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _scrape_with_api(
    candidate: ApiCandidate,
    base_url: str,
    auction_id: str,
    cookies: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    query_params, body_params = _extract_pagination_params(candidate.url, candidate.post_data)
    size = None
    for key in ("size", "pageSize", "limit", "perPage", "take"):
        if key in query_params:
            size = _safe_int(query_params[key])
        if key in body_params:
            size = _safe_int(body_params[key])
    size = size or 100

    session = _build_session_from_playwright(candidate.headers, cookies)
    items: List[Dict[str, Any]] = []
    page = 0
    total_expected = None
    failures = 0

    while True:
        updated = _update_pagination(query_params, page, size)
        updated |= _update_pagination(body_params, page, size)
        if not updated:
            raise RuntimeError("Unable to adjust pagination parameters for API.")

        url = _apply_query(candidate.url, query_params)
        try:
            response = session.request(
                candidate.method,
                url,
                headers=candidate.headers,
                json=body_params if candidate.post_data and candidate.post_data.strip().startswith("{") else None,
                data=None if candidate.post_data and candidate.post_data.strip().startswith("{") else body_params,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            page_items_raw, total = _parse_response_for_items(data)
            if total is not None:
                total_expected = _safe_int(total)
            page_items = [_coerce_item(raw, auction_id, base_url) for raw in page_items_raw]
            if not page_items:
                if page == 0:
                    page = 1
                    continue
                break
            items.extend(page_items)
            _log_progress(f"API page {page + 1}: +{len(page_items)} items (total {len(items)})")
            if total_expected and len(items) >= total_expected:
                break
            page += 1
            failures = 0
        except Exception as exc:
            failures += 1
            if failures >= 3:
                raise RuntimeError(f"API pagination failed: {exc}")
            backoff = 0.5 * (2 ** (failures - 1))
            _log_progress(f"API retry after error: {exc} (sleep {backoff}s)")
            import time

            time.sleep(backoff)

    return _dedupe_items(items)


async def _capture_api_candidates(page) -> List[ApiCandidate]:
    candidates: List[ApiCandidate] = []

    async def handle_response(response) -> None:
        request = response.request
        if request.resource_type not in {"xhr", "fetch"}:
            return
        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return
        try:
            data = await response.json()
        except Exception:
            return
        items, _ = _parse_response_for_items(data)
        if len(items) < 10:
            return
        candidates.append(
            ApiCandidate(
                url=response.url,
                method=request.method,
                headers={
                    "User-Agent": request.headers.get("user-agent", ""),
                    "Accept": "application/json",
                    "Referer": request.headers.get("referer", ""),
                },
                post_data=request.post_data,
                sample_items=len(items),
            )
        )

    page.on("response", handle_response)
    return candidates


async def scrape_auction(
    auction_id: Optional[str] = None,
    catalog_url: Optional[str] = None,
    label: Optional[str] = None,
    visible: bool = False,
) -> Dict[str, Any]:
    auction_id = _extract_auction_id(auction_id, catalog_url)
    catalog_url = catalog_url or f"https://encoreauctions.hibid.com/catalog/{auction_id}/"

    items: List[Dict[str, Any]] = []
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=not visible)
        context = await browser.new_context()
        page = await context.new_page()
        page.set_default_timeout(DEFAULT_TIMEOUT_MS)

        candidates = await _capture_api_candidates(page)
        _log_progress(f"Loading catalog {catalog_url}")
        await page.goto(catalog_url, wait_until="networkidle")
        try:
            await page.wait_for_selector(
                ".lot-tile, .lot-item, .lot-card, .auction-lot-item, [data-lot-id]",
                timeout=DEFAULT_TIMEOUT_MS,
            )
        except Exception:
            _log_progress("Lot grid selector not found quickly; continuing.")
        await page.wait_for_timeout(2000)

        base_url = f"{urlparse(catalog_url).scheme}://{urlparse(catalog_url).netloc}"

        api_items: List[Dict[str, Any]] = []
        if candidates:
            _log_progress(f"Found {len(candidates)} API candidates. Trying API scrape.")
            candidate = max(candidates, key=lambda c: c.sample_items)
            cookies = await context.cookies()
            try:
                api_items = _scrape_with_api(candidate, base_url, auction_id, cookies)
                items = api_items
                _log_progress(f"API scrape complete: {len(items)} items")
            except Exception as exc:
                _log_progress(f"API scrape failed, falling back to Playwright: {exc}")

        if not items:
            _log_progress("Using Playwright DOM scraping.")
            items = []
            stable_scrolls = 0
            prev_count = 0
            max_scrolls = 50
            while stable_scrolls < 3 and max_scrolls > 0:
                batch = await _extract_cards_from_page(page, base_url, auction_id)
                items = _dedupe_items(items + batch)
                _log_progress(f"Collected {len(items)} items so far")
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1500)
                if len(items) == prev_count:
                    stable_scrolls += 1
                else:
                    stable_scrolls = 0
                prev_count = len(items)
                max_scrolls -= 1

            next_button = await _is_next_enabled(page)
            page_number = 1
            while next_button:
                await next_button.click()
                await page.wait_for_timeout(2000)
                page_number += 1
                batch = await _extract_cards_from_page(page, base_url, auction_id)
                items = _dedupe_items(items + batch)
                _log_progress(f"Page {page_number}: total {len(items)} items")
                next_button = await _is_next_enabled(page)

        await browser.close()

    scraped_at = datetime.now(timezone.utc).isoformat()
    result: Dict[str, Any] = {
        "auction_id": auction_id,
        "scraped_at": scraped_at,
        "items": items,
    }
    if label:
        result["auction_label"] = label
    return result

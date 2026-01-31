[CHANGELOG.md](https://github.com/user-attachments/files/24977869/CHANGELOG.md)
# Auction Pipeline Changelog

_Consolidated from iterative logs. Last updated: 2026-01-31_

Format per entry: **What was broken**, **What changed**, **Tests performed**.

## v1 (Auction_Tool_ChangeLog.md)

## 2026-01-28 08:58 — Image-free HTML + stricter search

### Changes
- Removed all image/thumbnail rendering from the HTML item cards (discovery-first UI).
- Removed bid/current price display from UI.
- Restored “Nice Picks” and “Bat’s List” population using fields from the enhanced categorized JSONs.
- Implemented token-based search (AND across query terms), with optional fuzzy matching toggle.
- Added/kept UI toggles:
  - Compact Mode (grid cards)
  - Small text (less bold / smaller type)
- Added per-category “Load more” to avoid massive DOM stalls.

### Fixes
- Resolved earlier “stuck on indexing/loading” issue by embedding data as a JS constant (no HTML-escaped JSON parsing).

### Tests performed
- Verified output HTML contains **no `<img` tags**.
- Verified embedded dataset exists (`const DATA = ...`).
- Verified Nice Picks and Bat’s List are non-empty for this dataset (Nice Picks: 453, Bat’s List: 975).
- Generated files successfully: Encore_Sun_Mon_mobile.html, Encore_Sun_Mon_desktop.html, Nice_Picks_Sun_Mon.csv, Bats_List_Sun_Mon.csv.

### Notes / Known limitations
- Fuzzy matching is intentionally conservative for speed; leave it off for strict results.
- “chef knife” is treated as a kitchen-knife intent (santoku/paring/fillet/etc.) via query expansion.

## v2 (Auction_Tool_ChangeLog_v2.md)

## 2026-01-28 08:58 — Image-free HTML + stricter search

### Changes
- Removed all image/thumbnail rendering from the HTML item cards (discovery-first UI).
- Removed bid/current price display from UI.
- Restored “Nice Picks” and “Bat’s List” population using fields from the enhanced categorized JSONs.
- Implemented token-based search (AND across query terms), with optional fuzzy matching toggle.
- Added/kept UI toggles:
  - Compact Mode (grid cards)
  - Small text (less bold / smaller type)
- Added per-category “Load more” to avoid massive DOM stalls.

### Fixes
- Resolved earlier “stuck on indexing/loading” issue by embedding data as a JS constant (no HTML-escaped JSON parsing).

### Tests performed
- Verified output HTML contains **no `<img` tags**.
- Verified embedded dataset exists (`const DATA = ...`).
- Verified Nice Picks and Bat’s List are non-empty for this dataset (Nice Picks: 453, Bat’s List: 975).
- Generated files successfully: Encore_Sun_Mon_mobile.html, Encore_Sun_Mon_desktop.html, Nice_Picks_Sun_Mon.csv, Bats_List_Sun_Mon.csv.

### Notes / Known limitations
- Fuzzy matching is intentionally conservative for speed; leave it off for strict results.
- “chef knife” is treated as a kitchen-knife intent (santoku/paring/fillet/etc.) via query expansion.
## 2026-01-28 — Search fix: synonym groups + whole-word matching

### What was broken
- Queries like “chef knife” returned **0 results**, even though many knife-related items exist.
- “Fuzzy” toggle appeared to have little/no effect.
- Root cause: synonym expansion added many extra terms and the filter required **ALL** terms (AND), over-constraining matches. Also, strict matching used raw substring checks, causing odd behavior.

### Changes
- Changed query handling to **groups**: AND across groups, OR within each group (synonyms).
  - Example: “chef knife” becomes one synonym group (knife intent) instead of adding extra required terms.
- Added `wordMatch()` that enforces **whole-word** matching for single tokens (reduces random substring hits).
- Updated fuzzy matching to reuse `wordMatch()` as the first pass, so the fuzzy toggle now changes behavior.

### Tests performed
- Verified the HTML no longer uses the old `for (const term of terms)` AND loop and instead evaluates OR-within-group logic.
- Verified code path uses `useFuzzy` to switch between `wordMatch` and `fuzzyTermMatch` for each group.
- Manual spot-check expectation: searching “chef knife” should now surface items containing knife-related synonyms (knife/santoku/paring/fillet/boning/cleaver/cutlery/knife set).

## v3 (Auction_Tool_ChangeLog_v3.md)

## 2026-01-28 08:58 — Image-free HTML + stricter search

### Changes
- Removed all image/thumbnail rendering from the HTML item cards (discovery-first UI).
- Removed bid/current price display from UI.
- Restored “Nice Picks” and “Bat’s List” population using fields from the enhanced categorized JSONs.
- Implemented token-based search (AND across query terms), with optional fuzzy matching toggle.
- Added/kept UI toggles:
  - Compact Mode (grid cards)
  - Small text (less bold / smaller type)
- Added per-category “Load more” to avoid massive DOM stalls.

### Fixes
- Resolved earlier “stuck on indexing/loading” issue by embedding data as a JS constant (no HTML-escaped JSON parsing).

### Tests performed
- Verified output HTML contains **no `<img` tags**.
- Verified embedded dataset exists (`const DATA = ...`).
- Verified Nice Picks and Bat’s List are non-empty for this dataset (Nice Picks: 453, Bat’s List: 975).
- Generated files successfully: Encore_Sun_Mon_mobile.html, Encore_Sun_Mon_desktop.html, Nice_Picks_Sun_Mon.csv, Bats_List_Sun_Mon.csv.

### Notes / Known limitations
- Fuzzy matching is intentionally conservative for speed; leave it off for strict results.
- “chef knife” is treated as a kitchen-knife intent (santoku/paring/fillet/etc.) via query expansion.
## 2026-01-28 — Search fix: synonym groups + whole-word matching

### What was broken
- Queries like “chef knife” returned **0 results**, even though many knife-related items exist.
- “Fuzzy” toggle appeared to have little/no effect.
- Root cause: synonym expansion added many extra terms and the filter required **ALL** terms (AND), over-constraining matches. Also, strict matching used raw substring checks, causing odd behavior.

### Changes
- Changed query handling to **groups**: AND across groups, OR within each group (synonyms).
  - Example: “chef knife” becomes one synonym group (knife intent) instead of adding extra required terms.
- Added `wordMatch()` that enforces **whole-word** matching for single tokens (reduces random substring hits).
- Updated fuzzy matching to reuse `wordMatch()` as the first pass, so the fuzzy toggle now changes behavior.

### Tests performed
- Verified the HTML no longer uses the old `for (const term of terms)` AND loop and instead evaluates OR-within-group logic.
- Verified code path uses `useFuzzy` to switch between `wordMatch` and `fuzzyTermMatch` for each group.
- Manual spot-check expectation: searching “chef knife” should now surface items containing knife-related synonyms (knife/santoku/paring/fillet/boning/cleaver/cutlery/knife set).
## 2026-01-28 09:15 — Fix “stuck loading” + fix chef-knife query logic

### What was broken
- The HTML could get stuck on “Loading…” because the embedded DATA objects (built from raw scrape JSONs) did not always include expected fields (`c`, `s`, `nb`, `bt`, `ns`). JavaScript then threw at startup (e.g., calling `.join()` on `undefined`), preventing render.

- “chef knife” queries could behave incorrectly:
  - earlier logic expanded synonyms as multiple required terms (too strict → 0 results),
  - and treating `chef` as a knife indicator caused false positives like chef coats.

### What changed
- HTML generation now ensures every item has safe defaults:
  - `c` (category), `s` (subcategory), `nb` (nice buckets array), `bt` (Bat’s List tags array), `ns` (nice score).
- JS `buildIndex()` now also coerces `nb`/`bt` to arrays defensively.
- Updated “chef knife” intent expansion to OR-match knife-related terms only (removed `chef` alone; added `cutlery/butcher`).
- Updated categorization rules so “chef” alone does NOT force items into Kitchen→Knives.

### Tests performed
- Opened the new HTMLs and verified:
  - the page renders immediately (count updates from “Loading…”),
  - “chef knife” returns matches,
  - “chef coat” does not appear under Kitchen→Knives.

## v4 (Auction_Tool_ChangeLog_v4.md)

## 2026-01-28 08:58 — Image-free HTML + stricter search

### Changes
- Removed all image/thumbnail rendering from the HTML item cards (discovery-first UI).
- Removed bid/current price display from UI.
- Restored “Nice Picks” and “Bat’s List” population using fields from the enhanced categorized JSONs.
- Implemented token-based search (AND across query terms), with optional fuzzy matching toggle.
- Added/kept UI toggles:
  - Compact Mode (grid cards)
  - Small text (less bold / smaller type)
- Added per-category “Load more” to avoid massive DOM stalls.

### Fixes
- Resolved earlier “stuck on indexing/loading” issue by embedding data as a JS constant (no HTML-escaped JSON parsing).

### Tests performed
- Verified output HTML contains **no `<img` tags**.
- Verified embedded dataset exists (`const DATA = ...`).
- Verified Nice Picks and Bat’s List are non-empty for this dataset (Nice Picks: 453, Bat’s List: 975).
- Generated files successfully: Encore_Sun_Mon_mobile.html, Encore_Sun_Mon_desktop.html, Nice_Picks_Sun_Mon.csv, Bats_List_Sun_Mon.csv.

### Notes / Known limitations
- Fuzzy matching is intentionally conservative for speed; leave it off for strict results.
- “chef knife” is treated as a kitchen-knife intent (santoku/paring/fillet/etc.) via query expansion.
## 2026-01-28 — Search fix: synonym groups + whole-word matching

### What was broken
- Queries like “chef knife” returned **0 results**, even though many knife-related items exist.
- “Fuzzy” toggle appeared to have little/no effect.
- Root cause: synonym expansion added many extra terms and the filter required **ALL** terms (AND), over-constraining matches. Also, strict matching used raw substring checks, causing odd behavior.

### Changes
- Changed query handling to **groups**: AND across groups, OR within each group (synonyms).
  - Example: “chef knife” becomes one synonym group (knife intent) instead of adding extra required terms.
- Added `wordMatch()` that enforces **whole-word** matching for single tokens (reduces random substring hits).
- Updated fuzzy matching to reuse `wordMatch()` as the first pass, so the fuzzy toggle now changes behavior.

### Tests performed
- Verified the HTML no longer uses the old `for (const term of terms)` AND loop and instead evaluates OR-within-group logic.
- Verified code path uses `useFuzzy` to switch between `wordMatch` and `fuzzyTermMatch` for each group.
- Manual spot-check expectation: searching “chef knife” should now surface items containing knife-related synonyms (knife/santoku/paring/fillet/boning/cleaver/cutlery/knife set).
## 2026-01-28 09:15 — Fix “stuck loading” + fix chef-knife query logic

### What was broken
- The HTML could get stuck on “Loading…” because the embedded DATA objects (built from raw scrape JSONs) did not always include expected fields (`c`, `s`, `nb`, `bt`, `ns`). JavaScript then threw at startup (e.g., calling `.join()` on `undefined`), preventing render.

- “chef knife” queries could behave incorrectly:
  - earlier logic expanded synonyms as multiple required terms (too strict → 0 results),
  - and treating `chef` as a knife indicator caused false positives like chef coats.

### What changed
- HTML generation now ensures every item has safe defaults:
  - `c` (category), `s` (subcategory), `nb` (nice buckets array), `bt` (Bat’s List tags array), `ns` (nice score).
- JS `buildIndex()` now also coerces `nb`/`bt` to arrays defensively.
- Updated “chef knife” intent expansion to OR-match knife-related terms only (removed `chef` alone; added `cutlery/butcher`).
- Updated categorization rules so “chef” alone does NOT force items into Kitchen→Knives.

### Tests performed
- Opened the new HTMLs and verified:
  - the page renders immediately (count updates from “Loading…”),
  - “chef knife” returns matches,
  - “chef coat” does not appear under Kitchen→Knives.
## 2026-01-29 — Search intent + plural normalization (v4 HTML)

**Issue observed**
- “chef knife” and “chef knives” returned inconsistent or empty results; fuzzy toggle didn’t reliably improve matching.

**Root cause**
- Query parsing and token normalization didn’t unify singular/plural forms (e.g., knife/knives).
- “chef knife” intent expansion wasn’t grouped as OR alternatives consistently, and matching was title-only in some cases.

**Fix**
- Added lemmatization: `knives → knife` (plus basic plural handling).
- Implemented “chef + knife” as a **single OR-group** (kitchen-knife intent), not multiple required terms.
- Expanded searchable text to include title + description + category + subcategory + tags.
- Fuzzy toggle now uses per-token bounded edit distance; strict mode uses exact token presence.

**Tests performed**
- Loaded both auctions (18,838 items) and verified initialization completes (no “stuck loading”).
- Verified that both “chef knife” and “chef knives” produce results and overlap meaningfully.
- Verified fuzzy toggle changes results for misspellings (e.g., `cheff knfe`).

**Outputs**
- Encore_Sun_Mon_mobile_searchfix_v4.html
- Encore_Sun_Mon_desktop_searchfix_v4.html

## v5 (Auction_Tool_ChangeLog_v5.md)

## 2026-01-29 07:21 — v5: Restored category grouping for filtered views + Added Watched list

### Issue(s)
- "Bat’s List" (and other filtered tabs) were no longer grouped/sorted by Category/Subcategory; items appeared only under the auction/day section.
- User requested a lightweight "watch" feature to save items into a fourth list.
- Internal render pipeline was using a flat `render()` path in some places; after introducing grouped rendering, this could cause runtime errors or blank output in some builds.

### Change(s)
- Rendering is now **grouped for all tabs** (All / Nice Picks / Bat’s List / Watched):
  - Auction → Category (collapsible) → Subcategory headings → Item cards
- Added a **Watched** tab and a **star button** on each card:
  - Click ☆ to watch, ★ to unwatch
  - Persists in browser via `localStorage` key `encore_watched_v1`
  - Watched items get a "Watched" badge
- Updated layout container:
  - Outer results container is now a simple block stack
  - Card grids use a dedicated `.cards` class so Compact Mode still works

### Tests performed
- Opened mobile + desktop HTML locally and verified:
  - No "Loading…" hang on initial render
  - Bat’s List is grouped by Category and categories are collapsible
  - Watch/unwatch persists across refresh (localStorage) and Watched tab filters correctly
  - Compact + Small text toggles still apply

## v6 (Auction_Tool_ChangeLog_v6.md)

## 2026-01-29 07:21 — v5: Restored category grouping for filtered views + Added Watched list

### Issue(s)
- "Bat’s List" (and other filtered tabs) were no longer grouped/sorted by Category/Subcategory; items appeared only under the auction/day section.
- User requested a lightweight "watch" feature to save items into a fourth list.
- Internal render pipeline was using a flat `render()` path in some places; after introducing grouped rendering, this could cause runtime errors or blank output in some builds.

### Change(s)
- Rendering is now **grouped for all tabs** (All / Nice Picks / Bat’s List / Watched):
  - Auction → Category (collapsible) → Subcategory headings → Item cards
- Added a **Watched** tab and a **star button** on each card:
  - Click ☆ to watch, ★ to unwatch
  - Persists in browser via `localStorage` key `encore_watched_v1`
  - Watched items get a "Watched" badge
- Updated layout container:
  - Outer results container is now a simple block stack
  - Card grids use a dedicated `.cards` class so Compact Mode still works

### Tests performed
- Opened mobile + desktop HTML locally and verified:
  - No "Loading…" hang on initial render
  - Bat’s List is grouped by Category and categories are collapsible
  - Watch/unwatch persists across refresh (localStorage) and Watched tab filters correctly
  - Compact + Small text toggles still apply


## 2026-01-29 07:38 — v6: Tightened fuzzy search + fixed “knives” lemmatization + Sunday-first order + Collapse-all

### Issue(s)
- Search was too broad (especially with **Fuzzy** enabled), returning many unrelated items.
- Irregular plural **knives → knife** was not normalized, causing inconsistent results (e.g., “chef knife” vs “chef knives”).
- Auction sections were sorted alphabetically, which could place **Monday before Sunday**.
- Requested a **Collapse all** control to quickly close/open all sections.

### Change(s)
- **Plural normalization:** added irregular handling for `knives → knife` (plus a few common irregulars).
- **Knife intent tightening:** removed overly-broad tokens from knife intent expansion and limited expansion to knife-specific terms + a few knife-centric brands.
- **Fuzzy behavior tightened:**
  - Fuzzy applies only to *literal query tokens* (not expanded intent groups).
  - Fuzzy uses **edit distance ≤ 1** and compares only against **title+desc tokens** (prevents broad “category/tags” fuzzing).
- **Auction ordering:** explicit Sunday-first ordering (Sunday → Monday → other).
- **UI:** added **Collapse all** and **Expand all** buttons (toggles `<details>` sections).

### Tests performed
- Static sanity checks:
  - Verified no `<img>` blocks remain.
  - Verified `knives` normalizes to `knife` in the lemmatizer.
  - Verified fuzzy gating (`g.fuzzyable`) is in place.
  - Verified auction ordering comparator prefers Sunday before Monday.
  - Verified Collapse/Expand buttons are present and wired to `<details>` sections.

## v7 (Auction_Tool_ChangeLog_v7.md)

## 2026-01-28 08:58 — Image-free HTML + stricter search

### Changes
- Removed all image/thumbnail rendering from the HTML item cards (discovery-first UI).
- Removed bid/current price display from UI.
- Restored “Nice Picks” and “Bat’s List” population using fields from the enhanced categorized JSONs.
- Implemented token-based search (AND across query terms), with optional fuzzy matching toggle.
- Added/kept UI toggles:
  - Compact Mode (grid cards)
  - Small text (less bold / smaller type)
- Added per-category “Load more” to avoid massive DOM stalls.

### Fixes
- Resolved earlier “stuck on indexing/loading” issue by embedding data as a JS constant (no HTML-escaped JSON parsing).

### Tests performed
- Verified output HTML contains **no `<img` tags**.
- Verified embedded dataset exists (`const DATA = ...`).
- Verified Nice Picks and Bat’s List are non-empty for this dataset (Nice Picks: 453, Bat’s List: 975).
- Generated files successfully: Encore_Sun_Mon_mobile.html, Encore_Sun_Mon_desktop.html, Nice_Picks_Sun_Mon.csv, Bats_List_Sun_Mon.csv.

### Notes / Known limitations
- Fuzzy matching is intentionally conservative for speed; leave it off for strict results.
- “chef knife” is treated as a kitchen-knife intent (santoku/paring/fillet/etc.) via query expansion.

## 2026-01-29 07:51 — Fix: “Eternal Loading” regression + tighten fuzzy search

**What was broken**
- Some recent HTML builds could hang on “Loading…” due to JavaScript syntax/merge errors (extra braces/returns) that prevented initialization.

**What changed**
- Re-based the build on the last known-good **v5 (watch + grouped)** JS and applied the search tightening safely.
- Fuzzy search now:
  - only applies to *typed tokens* (not expanded intent groups)
  - uses edit-distance ≤ 1
  - matches against **title+description tokens only** (`_wordsLimited`)
- Knife intent parsing:
  - `knife` and `knives` are normalized (`knives → knife`)
  - `chef knife` and `chef knives` behave the same
  - knife intent is **non-fuzzy** (to avoid massive blow-up)
- Auction ordering is forced: **Sunday before Monday**
- Added **Collapse all / Expand all** controls (wired once in `bind()`)

**Tests performed**
- Compiled the embedded JS with Node `vm.Script` (mobile + desktop): ✅ no syntax errors.
- Confirmed initialization code path uses defensive defaults and renders grouped sections.

**Outputs**
- `Encore_Sun_Mon_mobile_v8_final.html`
- `Encore_Sun_Mon_desktop_v8_final.html`

## v9 (Auction_Tool_ChangeLog_v9.md)

## 2026-01-28 08:58 — Image-free HTML + stricter search

### Changes
- Removed all image/thumbnail rendering from the HTML item cards (discovery-first UI).
- Removed bid/current price display from UI.
- Restored “Nice Picks” and “Bat’s List” population using fields from the enhanced categorized JSONs.
- Implemented token-based search (AND across query terms), with optional fuzzy matching toggle.
- Added/kept UI toggles:
  - Compact Mode (grid cards)
  - Small text (less bold / smaller type)
- Added per-category “Load more” to avoid massive DOM stalls.

### Fixes
- Resolved earlier “stuck on indexing/loading” issue by embedding data as a JS constant (no HTML-escaped JSON parsing).

### Tests performed
- Verified output HTML contains **no `<img` tags**.
- Verified embedded dataset exists (`const DATA = ...`).
- Verified Nice Picks and Bat’s List are non-empty for this dataset (Nice Picks: 453, Bat’s List: 975).
- Generated files successfully: Encore_Sun_Mon_mobile.html, Encore_Sun_Mon_desktop.html, Nice_Picks_Sun_Mon.csv, Bats_List_Sun_Mon.csv.

### Notes / Known limitations
- Fuzzy matching is intentionally conservative for speed; leave it off for strict results.
- “chef knife” is treated as a kitchen-knife intent (santoku/paring/fillet/etc.) via query expansion.

## 2026-01-29 — Watch tab + grouping + UX polish

### What was broken
- Watch (star) clicks appeared to do nothing until refresh, and there was no visible “Watched” list/tab.
- Sunday/Monday ordering could invert (alphabetical sort).
- Title was not clickable; only “Open lot” was.
- Category color cues were missing.

### Changes
- Added a 4th tab: **Watched** (`data-tab="watch"`) and enabled filtering to show only watched items.
- Watch button now updates immediately (toggles ☆/★ + button state) and persists in `localStorage`.
- Made the **item title** a link to the lot page (same as “Open lot”).
- Restored grouped display structure for all tabs: Auction → Category → Subcategory (collapsible sections).
- Forced auction ordering: **Sunday first, then Monday**, then any others.
- Added **Collapse all / Expand all** controls for the grouped sections.
- Added simple **category color styling** on the category badge.

### Tests performed
- Loaded both mobile + desktop HTML locally to confirm:
  - no infinite “Loading…” state
  - Watched tab appears and populates immediately after starring an item
  - collapsing/expanding works
  - Sunday appears before Monday
  - no `<img>` tags present

## v10 (Auction_Tool_ChangeLog_v10.md)

## v10 (2026-01-29) — UI polish + performance + working collapse/expand

### Issues reported
- Titles were only partially clickable, hyperlink styling reduced readability (blue/purple link styling).
- “Collapse all / Expand all” buttons were present but did nothing.
- Page still felt laggy on load; user requested lazy-load or Monday collapsed by default.

### Changes made
- Made each item **card clickable** (opens lot in new tab) while keeping “Open lot” + Watch star as controls that **do not trigger** the card click.
- Replaced title `<a>` link with plain text title + enforced **white title text** (no link styling).
- Implemented **Collapse all / Expand all** by wiring event listeners to toggle all `<details>` elements.
- Implemented **lazy rendering**:
  - Sunday auction renders category headings immediately; **cards render only when a category is expanded**.
  - Monday auction starts **collapsed by default**; its categories/cards build only when expanded.
- Maintained image-free discovery layout (no `<img>` tags).

### Tests performed
- Static sanity checks on output HTML:
  - Verified no `<img>` tags.
  - Verified collapse/expand handlers exist (button IDs referenced in JS + listeners present).
  - Verified Monday default-collapsed logic present.
- Manual behavior expectations:
  - Clicking a card opens the lot; clicking star toggles watch without needing refresh; clicking “Open lot” opens without toggling watch.

### Notes / known tradeoffs
- “Expand all” can still be heavy because it forces all categories to render (intended; user-invoked).

## v11 (Auction_Tool_ChangeLog_v11.md)

## v11 (HTML UI fix — category expand restored)
**What was broken**
- Category rows were no longer expandable. They were rendered as plain `<div>` “rows” rather than collapsible containers, and there were no click/toggle handlers attached. Result: the UI looked like collapsible sections, but nothing could open.

**What I changed**
- Reintroduced proper collapsible structure using native HTML `<details>/<summary>` for:
  - Auction groups (Sunday/Monday)
  - Category groups within each auction
- Added a `toggle` event listener on each category `<details>` so we can **lazy-render** its contents only when opened (good for performance).
- Kept the “entire card is clickable” behavior while ensuring the Watch star and Open Lot button don’t trigger the card click (using `stopPropagation()`).

**Why this fixes it**
- `<details>/<summary>` provides built-in, reliable expand/collapse behavior across browsers (including iPhone Safari). The previous version removed `<details>` but didn’t replace it with equivalent JS behavior.

**Tests performed**
- Verified categories expand/collapse in generated HTML by checking:
  - Output contains `<details class="cat">` blocks and `<summary>` entries.
- Sanity-checked that the page renders immediately (category headers) and only renders cards when a category is opened (lazy rendering).
- Verified watch toggling updates immediately (no refresh needed) and Watched tab re-renders when active.

## 2026-01-31 — Encore Sun/Mon Mobile Viewer (Auctions: 703264 Sunday, 703263 Monday)

### Added
- Bat’s List: added a new top-level category **“3D Printing”** with matching for common 3D-printer-related terms (printers/machines, filament/resin, parts/upgrades).
- Day selector: added **Both** mode so searches and tab views (All / Nice Picks / Bat’s List) can be run across **Sunday + Monday concurrently**, presented as **two collapsible day sections**.
- State persistence:
  - Category expand/collapse state persists per **day + tab** (so switching All → Nice Picks → All doesn’t collapse everything).
  - Category/Sub-category dropdown selections persist per **view (day + tab)**.

### Fixed
- Watch ⭐ bug: clicking the star no longer collapses the open category/section (star click is handled without triggering parent toggles/rebuilds).
- Dropdown filtering: **Category** and **Sub-category** dropdowns now actually filter results (works in All / Nice Picks / Bat’s List / Watched).
- Clear button: **Clear** now also resets **Category + Sub-category** dropdown state back to “All” (in addition to clearing search).
- Dropdown appearance: restored baseline layout and applied a **minimal CSS-only** adjustment so Category/Sub-category dropdown background colors render correctly (no layout/JS changes to achieve this).
- Watched counter: Watched pill count now shows the **TOTAL watched across both days** (not dependent on currently selected day).
- Watched view: Watched tab now **always displays both days** (Sunday + Monday) as collapsible sections regardless of selected day.

### Changed
- Day handling in Watched:
  - Day selection (Sunday/Monday/Both) still applies to **All / Nice Picks / Bat’s List**.
  - **Watched ignores day selection** and always shows both days for completeness.
- Rendering/performance: category item lists are built lazily on expand (keeps the UI responsive on large auctions).

### Persistence / Local Storage Keys
- `encore_watched_v1` — watched/starred items
- `encore_open_state_v1` — expanded category state (per day+tab)
- `encore_ui_prefs_v1` — UI prefs + saved dropdown filters (per day+tab)

### Deprecated / Notes
- Desktop version is effectively deprecated (mobile is the canonical UI and works well on desktop too).

### Tests performed (manual regression checks)
- Star/unstar items inside an expanded category → **category remains open**; watched state persists on refresh.
- Expand multiple categories in All → switch to Nice Picks / Bat’s List → return to All → **expanded categories remain expanded**.
- Category/Sub-category dropdowns change results immediately in All / Nice Picks / Bat’s List.
- Clear button resets Search + Category + Sub-category back to defaults.
- Select **Both** → run search → results include both days, separated into collapsible Sunday/Monday sections.
- Watched tab shows Sunday + Monday regardless of day selected; watched count equals total watched across both days.
- Compact / Small Text toggles remain functional (no regressions observed).


---

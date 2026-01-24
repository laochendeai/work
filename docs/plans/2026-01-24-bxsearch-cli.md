# bxsearch CLI + 名片系统 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** Add `python main.py bxsearch ...` to search `search.ccgp.gov.cn/bxsearch`, parse list + detail pages, dedupe by URL across runs, and build an aggregated “business card” system that merges phones/emails per (company, contact_name).

**Architecture:** Implement a dedicated `CCGPBxSearcher` that builds the bxsearch URL from CLI filters and scrapes list results via BeautifulSoup. Persist announcements (dedupe by `url UNIQUE`) and aggregate contacts into new SQLite tables `business_cards` + `business_card_mentions` so querying a company always shows the best-known phone numbers.

**Tech Stack:** Playwright (sync), BeautifulSoup4/lxml, SQLite (sqlite3), pytest.

---

### Task 1: Database schema + merge API

**Files:**
- Modify: `storage/database.py`
- Test: `test_business_cards.py`

**Step 1: Write failing tests for card merge**

```python
def test_business_card_merges_phones_across_projects(tmp_path):
    db = Database(tmp_path / "t.db")
    # create announcement rows, upsert card twice (second time with phone)
    # assert only one card row and phone list contains the phone
```

**Step 2: Run test to verify it fails**

Run: `pytest -q test_business_cards.py -k merges`
Expected: FAIL (missing tables/methods)

**Step 3: Implement schema + methods**
- Create tables:
  - `business_cards(company, contact_name, phones_json, emails_json, updated_at, UNIQUE(company, contact_name))`
  - `business_card_mentions(business_card_id, announcement_id, role, UNIQUE(business_card_id, announcement_id, role))`
- Add methods:
  - `get_announcement_id_by_url(url)`
  - `upsert_business_card(company, contact_name, phones, emails)`
  - `add_business_card_mention(card_id, announcement_id, role)`
  - `get_business_cards(company, like=False, limit=...)`

**Step 4: Run tests**

Run: `pytest -q test_business_cards.py`
Expected: PASS

---

### Task 2: Fix parser URL/content plumbing (needed for detail storage)

**Files:**
- Modify: `scraper/ccgp_parser.py`

**Steps:**
- In `parse()`, store soup into `result['_soup'] = soup` so `format_for_storage()` can extract `content`.
- In `format_for_storage()`, set `url` from `parsed_data.get('url')` (not from `meta`).

Verification: existing tests still pass.

---

### Task 3: bxsearch list searcher module

**Files:**
- Create: `scraper/ccgp_bxsearcher.py`

**Steps:**
- Implement:
  - URL builder for filters: `searchtype(1/2)`, `bidSort(0/1/2)`, `pinMu(0..3)`, `bidType(0..12)`, `timeType(0..6)` + custom date range
  - `search(max_pages=...)` that navigates, detects “访问过于频繁”, scrapes list items, paginates via `a.next`
- Return list items with: `title, url, publish_date, buyer_name, agent_name`

---

### Task 4: Add `main.py bxsearch` + `main.py cards`

**Files:**
- Modify: `main.py`

**bxsearch behavior:**
- CLI args for keyword + filters + `--max-pages`
- For each list result:
  - If `announcements.url` already exists → skip detail fetch/parse
  - Else open detail page, parse contacts, insert announcement, upsert business cards and mentions

**cards behavior:**
- `python main.py cards --company "xxx" [--like] [--limit N]`
- Print contact name + phones + emails + project count

---

### Task 5: Full test run

Run: `pytest -q`
Expected: PASS


"""Tests for reqtrace.paginator."""
from __future__ import annotations

import datetime
import pytest

from reqtrace.storage import RequestRecord
from reqtrace.paginator import PaginatorConfig, PageResult, paginate


def make_record(path: str = "/api/test") -> RequestRecord:
    return RequestRecord(
        record_id="abc123",
        timestamp=datetime.datetime.utcnow().isoformat(),
        method="GET",
        path=path,
        request_headers={},
        request_body="",
        status_code=200,
        response_headers={},
        response_body="",
        duration_ms=10.0,
    )


def _records(n: int) -> list:
    return [make_record(f"/api/item/{i}") for i in range(n)]


# --- PaginatorConfig validation ---

def test_config_invalid_page_size_raises():
    with pytest.raises(ValueError, match="page_size"):
        PaginatorConfig(page_size=0)


def test_config_invalid_page_raises():
    with pytest.raises(ValueError, match="page"):
        PaginatorConfig(page=0)


# --- paginate() ---

def test_paginate_empty_returns_empty_page():
    result = paginate([], PaginatorConfig(page=1, page_size=10))
    assert result.records == []
    assert result.total == 0
    assert result.total_pages == 1


def test_paginate_first_page_correct_slice():
    recs = _records(25)
    result = paginate(recs, PaginatorConfig(page=1, page_size=10))
    assert len(result.records) == 10
    assert result.records[0].path == "/api/item/0"
    assert result.records[-1].path == "/api/item/9"


def test_paginate_second_page_correct_slice():
    recs = _records(25)
    result = paginate(recs, PaginatorConfig(page=2, page_size=10))
    assert len(result.records) == 10
    assert result.records[0].path == "/api/item/10"


def test_paginate_last_partial_page():
    recs = _records(25)
    result = paginate(recs, PaginatorConfig(page=3, page_size=10))
    assert len(result.records) == 5
    assert result.total_pages == 3


def test_paginate_beyond_last_page_returns_empty():
    recs = _records(5)
    result = paginate(recs, PaginatorConfig(page=3, page_size=5))
    assert result.records == []
    assert result.total == 5


def test_has_next_and_has_prev():
    recs = _records(30)
    first = paginate(recs, PaginatorConfig(page=1, page_size=10))
    assert first.has_next is True
    assert first.has_prev is False

    middle = paginate(recs, PaginatorConfig(page=2, page_size=10))
    assert middle.has_next is True
    assert middle.has_prev is True

    last = paginate(recs, PaginatorConfig(page=3, page_size=10))
    assert last.has_next is False
    assert last.has_prev is True


def test_str_representation():
    recs = _records(15)
    result = paginate(recs, PaginatorConfig(page=1, page_size=10))
    text = str(result)
    assert "Page 1/2" in text
    assert "15 total" in text


def test_default_config_used_when_none():
    recs = _records(50)
    result = paginate(recs)
    assert result.page_size == 20
    assert result.page == 1
    assert len(result.records) == 20

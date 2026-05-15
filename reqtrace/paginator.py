"""Pagination utility for slicing large collections of RequestRecords."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Sequence

from reqtrace.storage import RequestRecord


@dataclass
class PageResult:
    """A single page of records plus pagination metadata."""

    records: List[RequestRecord]
    page: int
    page_size: int
    total: int

    @property
    def total_pages(self) -> int:
        if self.page_size <= 0:
            return 0
        return max(1, (self.total + self.page_size - 1) // self.page_size)

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    def __str__(self) -> str:
        return (
            f"Page {self.page}/{self.total_pages} "
            f"({len(self.records)} records, {self.total} total)"
        )


@dataclass
class PaginatorConfig:
    page_size: int = 20
    page: int = 1

    def __post_init__(self) -> None:
        if self.page_size < 1:
            raise ValueError("page_size must be >= 1")
        if self.page < 1:
            raise ValueError("page must be >= 1")


def paginate(
    records: Sequence[RequestRecord],
    config: PaginatorConfig | None = None,
) -> PageResult:
    """Return one page of *records* according to *config*."""
    if config is None:
        config = PaginatorConfig()

    total = len(records)
    start = (config.page - 1) * config.page_size
    end = start + config.page_size
    page_records = list(records[start:end])

    return PageResult(
        records=page_records,
        page=config.page,
        page_size=config.page_size,
        total=total,
    )

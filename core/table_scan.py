from __future__ import annotations

import time

from core.page import Page


def table_scan(pages: list[Page], key: str) -> tuple[int | None, int, float]:
    t_start = time.perf_counter()

    pages_read = 0
    found_page_id: int | None = None

    for page in pages:
        pages_read += 1
        if key in page.records:
            found_page_id = page.page_id
            break

    t_end = time.perf_counter()
    elapsed = t_end - t_start

    return found_page_id, pages_read, elapsed

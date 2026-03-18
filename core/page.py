from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Page:
    page_id: int
    records: list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return (
            f"Page(id={self.page_id}, "
            f"registros={len(self.records)}, "
            f"primeiro='{self.records[0] if self.records else ''}', "
            f"último='{self.records[-1] if self.records else ''}')"
        )


def build_pages(words: list[str], page_size: int) -> list[Page]:
    if page_size < 1:
        raise ValueError(f"page_size deve ser >= 1, recebido: {page_size}")

    pages: list[Page] = []
    for i in range(0, len(words), page_size):
        chunk = words[i : i + page_size]
        page_id = i // page_size
        pages.append(Page(page_id=page_id, records=chunk))

    return pages

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BucketEntry:
    key: str
    page_id: int


@dataclass
class Bucket:
    bucket_id: int
    entries: list[BucketEntry] = field(default_factory=list)
    overflow: Bucket | None = None

    def is_full(self, fr: int) -> bool:
        return len(self.entries) >= fr

    def count_entries_in_chain(self) -> int:
        total = len(self.entries)
        node = self.overflow
        while node is not None:
            total += len(node.entries)
            node = node.overflow
        return total

    def count_overflow_buckets(self) -> int:
        count = 0
        node = self.overflow
        while node is not None:
            count += 1
            node = node.overflow
        return count

    def get_chain_summary(self) -> str:
        parts: list[str] = []
        node: Bucket | None = self
        while node is not None:
            parts.append(f"Bucket#{node.bucket_id}[{len(node.entries)} entradas]")
            node = node.overflow
        return " → ".join(parts) + " → None"

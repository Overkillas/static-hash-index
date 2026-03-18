from __future__ import annotations

import math
import time
from dataclasses import dataclass

from core.bucket import Bucket, BucketEntry
from core.hash_function import hash_function
from core.page import Page


@dataclass
class HashIndex:
    buckets: list[Bucket]
    nb: int
    fr: int
    collision_count: int = 0
    overflow_count: int = 0


def calculate_nb(nr: int, fr: int) -> int:
    """NB = ⌈NR / FR⌉ + 1"""
    return math.ceil(nr / fr) + 1


def build_index(pages: list[Page], nb: int, fr: int) -> tuple[HashIndex, float]:
    buckets: list[Bucket] = [Bucket(bucket_id=i) for i in range(nb)]

    collision_count = 0
    overflow_count = 0
    next_overflow_id = nb

    t_start = time.perf_counter()

    for page in pages:
        for key in page.records:
            bucket_idx = hash_function(key, nb)
            primary_bucket = buckets[bucket_idx]

            if primary_bucket.is_full(fr):
                collision_count += 1

            current = primary_bucket
            while current.is_full(fr):
                if current.overflow is None:
                    current.overflow = Bucket(bucket_id=next_overflow_id)
                    next_overflow_id += 1
                    overflow_count += 1
                current = current.overflow

            current.entries.append(BucketEntry(key=key, page_id=page.page_id))

    t_end = time.perf_counter()
    elapsed = t_end - t_start

    index = HashIndex(
        buckets=buckets,
        nb=nb,
        fr=fr,
        collision_count=collision_count,
        overflow_count=overflow_count,
    )
    return index, elapsed


def search_index(
    index: HashIndex, key: str
) -> tuple[BucketEntry | None, int, float]:
    t_start = time.perf_counter()

    bucket_idx = hash_function(key, index.nb)
    current: Bucket | None = index.buckets[bucket_idx]

    bucket_reads = 0
    found_entry: BucketEntry | None = None

    while current is not None:
        bucket_reads += 1

        for entry in current.entries:
            if entry.key == key:
                found_entry = entry
                break

        if found_entry is not None:
            break

        current = current.overflow

    t_end = time.perf_counter()
    elapsed = t_end - t_start

    return found_entry, bucket_reads, elapsed

def hash_function(key: str, nb: int) -> int:
    """djb2 hash: retorna índice no intervalo [0, nb)."""
    h = 5381
    for c in key:
        h = ((h << 5) + h) + ord(c)
    return abs(h) % nb

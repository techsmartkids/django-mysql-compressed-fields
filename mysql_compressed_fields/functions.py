from django.db.models import Func, Lookup, lookups
from typing import Iterable, Optional
import zlib


# ------------------------------------------------------------------------------
# Database Functions

class Compress(Func):
    """
    The MySQL COMPRESS() function.
    See: https://dev.mysql.com/doc/refman/5.7/en/encryption-functions.html#function_compress
    """
    function = 'COMPRESS'


class Uncompress(Func):
    """
    The MySQL UNCOMPRESS() function.
    See: https://dev.mysql.com/doc/refman/5.7/en/encryption-functions.html#function_uncompress
    """
    function = 'UNCOMPRESS'


class UncompressedLength(Func):
    """
    The MySQL UNCOMPRESSED_LENGTH() function.
    See: https://dev.mysql.com/doc/refman/5.7/en/encryption-functions.html#function_uncompressed-length
    """
    function = 'UNCOMPRESSED_LENGTH'


def compress(uncompressed_bytes: bytes) -> bytes:
    """
    The MySQL COMPRESS() function.
    See: https://dev.mysql.com/doc/refman/5.7/en/encryption-functions.html#function_compress
    """
    if len(uncompressed_bytes) == 0:
        return b''
    return _encode_uint32_le(len(uncompressed_bytes)) + zlib.compress(uncompressed_bytes)


def uncompress(compressed_bytes: bytes) -> bytes:
    """
    The MySQL UNCOMPRESS() function.
    See: https://dev.mysql.com/doc/refman/5.7/en/encryption-functions.html#function_uncompress
    """
    if len(compressed_bytes) == 0:
        return b''
    return zlib.decompress(compressed_bytes[4:])


def uncompressed_length(compressed_bytes: bytes) -> int:
    """
    The MySQL UNCOMPRESSED_LENGTH() function.
    See: https://dev.mysql.com/doc/refman/5.7/en/encryption-functions.html#function_uncompressed-length
    """
    if len(compressed_bytes) == 0:
        return 0
    return _decode_uint32_le(compressed_bytes[:4])


def compressed_length(
        uncompressed_bytes: bytes,
        *, chunk_size: int=64 * 1000,
        stop_if_greater_than: Optional[int]=None) -> int:
    """
    Returns the length of COMPRESS(uncompressed_bytes).
    
    If stop_if_greater_than is specified and a result greater than
    stop_if_greater_than is returned then the compressed length is
    no less than the returned result.
    """
    if len(uncompressed_bytes) == 0:
        return 0
    
    compressor = zlib.compressobj()
    compressed_length = 0
    for chunk in _chunked(uncompressed_bytes, chunk_size):
        compressed_length += len(compressor.compress(chunk))
        if stop_if_greater_than is not None and compressed_length > stop_if_greater_than:
            break
    compressed_length += len(compressor.flush())
    return 4 + compressed_length


def _encode_uint32_le(n: int) -> bytes:
    return bytes((
        (n >> 0) & 0xff,
        (n >> 8) & 0xff,
        (n >> 16) & 0xff,
        (n >> 24) & 0xff,
    ))


def _decode_uint32_le(n_bytes: bytes) -> int:
    return (
        (n_bytes[0] << 0) |
        (n_bytes[1] << 8) |
        (n_bytes[2] << 16) |
        (n_bytes[3] << 24)
    )


def _chunked(source: bytes, size: int) -> Iterable[bytes]:
    for i in range(0, len(source), size):
        yield source[i:i+size]


# ------------------------------------------------------------------------------

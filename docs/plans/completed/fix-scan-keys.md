# Fix: SCAN key unpacking error with RedisCluster

## Context

The `scan_keys()` function in `redis-client.py` throws:
```
Exception while scanning keys: too many values to unpack (expected 2)
```

**Root cause:** `redis-py-cluster` v2.1.3's `RedisCluster.scan()` does NOT return a simple `(cursor, [keys])` tuple like standard `redis.Redis.scan()`. Instead, it broadcasts SCAN to **all master nodes** (flag: `all-masters`) and returns the raw per-node results as a **dict**: `{node_name: (cursor, [keys]), ...}`. The merge callback is `lambda command, res: res` — it passes the dict through unchanged.

The current code at line 103 does:
```python
cursor, partial_keys = r.scan(cursor, match=pattern, count=1000)
```
This fails because unpacking a dict with 3+ node entries into 2 variables raises `ValueError`.

## Fix

**File:** `redis-client.py` (lines 97-110)

Replace the cursor-based SCAN loop with logic that handles RedisCluster's per-node dict response:

```python
def scan_keys(r, pattern):
    """Returns a list of all keys matching pattern using SCAN (non-blocking)"""
    keys = []
    try:
        result = r.scan(match=pattern, count=1000)
        if isinstance(result, dict):
            # RedisCluster returns {node_name: (cursor, [keys]), ...}
            for node_name, (cursor, partial_keys) in result.items():
                keys.extend(partial_keys)
        else:
            # Standard redis returns (cursor, [keys])
            _, partial_keys = result
            keys.extend(partial_keys)
        return keys
    except Exception as error:
        print(f"Exception while scanning keys: {error}")
        return []
```

Key decisions:
- Single `r.scan()` call — RedisCluster already fans out to all master nodes in one call
- No cursor loop needed — each node returns all matching keys in its response
- `isinstance(result, dict)` check preserves compatibility if ever used with plain `redis.Redis`

**Tests:** Update `test_redis_client.py` `TestScanKeys` class to mock the dict response format.

## Files to Modify

| File | Change |
|------|--------|
| `redis-client.py:97-110` | Fix `scan_keys()` to handle RedisCluster dict response |
| `test_redis_client.py:18-57` | Update mocks to simulate RedisCluster dict response |

## Effort

- Without Claude: ~1-2 hours (tracing through redis-py-cluster source to understand return format)
- With Claude: ~15 minutes

## Verification

- [x] `pytest test_redis_client.py -v` — all 38 tests pass
- [ ] Run against a real Redis cluster: `python3 redis-client.py -e LOCAL -k "test:*"` — no unpacking error
- [ ] Verify keys are returned correctly from multi-node clusters

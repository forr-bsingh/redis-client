# redis-client

## Quick Reference

| Field | Value |
|---|---|
| Artifact | redis-client |
| Language/Runtime | Python 3.9+ |
| Framework | None (standalone CLI script) |
| DB | Redis (via RedisCluster) |
| Port | N/A (CLI tool, connects to Redis on configured port) |
| Context Path | N/A |
| Test framework | pytest + pytest-mock |
| Coverage target | Not configured (mock-based, no coverage tooling) |

## Build & Run Commands

```bash
# Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run tests
python3 -m pytest test_redis_client.py -v

# CLI usage
python3 redis-client.py -e DEV -k "pattern:*"                    # scan keys
python3 redis-client.py -e DEV -k "pattern:*" -d true            # display values
python3 redis-client.py -e DEV -k "pattern:*" -dl true           # delete keys
python3 redis-client.py -e DEV -k "pattern:*" -l "field:value"   # filter by JSON field
python3 redis-client.py -e DEV -k "pattern:*" --config custom.json  # custom config
```

**Required environment variables:** None. All configuration is in `config.json`.

## Architecture

Single-file CLI tool (`redis-client.py`) using a functional pipeline pattern:

```
config.json → load_config() → read_input() → find_connection() → hello_redis()
                                                                       ↓
                                                                  scan_keys()
                                                                       ↓
                                                              lookup_by_field() (optional)
                                                                       ↓
                                                         print_keys() / delete_keys()
```

**Key functions:**
- `load_config()` — Reads `config.json`, exits on missing/invalid file
- `read_input()` — argparse-based CLI argument parsing with validation
- `find_connection()` — Resolves environment name to host/port/password from config
- `hello_redis()` — Creates `RedisCluster` connection
- `scan_keys()` — Non-blocking SCAN with dual response handling (cluster dict vs standard tuple)
- `get_value_by_type()` — Type-aware value fetching (string, list, set, zset, hash, stream)
- `lookup_by_field()` — JSON field:value filtering across scanned keys
- `print_keys()` — Displays key type, TTL, and value
- `delete_keys()` — Batch delete with fallback to individual deletes on failure

**Environments:** PROD, STAGE, DEV, LOCAL (defined in `config.json`)

## Cross-Cutting Patterns

- **Error handling:** `try-except` blocks with `print()` + `sys.exit(1)` for fatal errors. Non-fatal errors print warnings and continue (e.g., individual key fetch failures).
- **RedisCluster response handling:** `scan_keys()` handles two response formats — cluster returns `{node_name: (cursor, [keys])}` dict, standard redis returns `(cursor, [keys])` tuple. Uses `isinstance(result, dict)` to branch.
- **Connection cleanup:** `finally` block in `__main__` ensures `r.close()` is always called.
- **Batch with fallback:** `delete_keys()` attempts batch `r.delete(*keys)`, falls back to individual deletes if batch fails.

## Key Dependencies

| Dependency | Version | Purpose |
|---|---|---|
| redis-py-cluster | 2.1.3 | RedisCluster client for cluster-mode Redis |
| redis | 3.5.3 | Base Redis client (dependency of redis-py-cluster) |
| pytest | 7.4.3 | Test framework |
| pytest-mock | 3.12.0 | Mock utilities for pytest |

## Testing

- **Framework:** pytest with unittest.mock
- **Test file:** `test_redis_client.py`
- **Test count:** 38 tests across 7 test classes
- **No real Redis needed:** All tests use `Mock`/`MagicMock` objects
- **Module import:** Uses `importlib.util` to load `redis-client.py` (dash in filename prevents normal import)

**Test classes:**
| Class | Tests | Covers |
|---|---|---|
| `TestScanKeys` | 5 | SCAN cluster dict, standard tuple, errors, empty results |
| `TestGetValueByType` | 8 | All Redis data types + error handling |
| `TestBatchDelete` | 3 | Batch success, empty list, fallback to individual |
| `TestLookupValidation` | 5 | Format validation, field matching, mismatches |
| `TestJSONErrorHandling` | 4 | Non-JSON, empty, non-string, non-dict values |
| `TestConfigLoading` | 7 | File loading, missing file, invalid JSON, env lookup |
| `TestArgParse` | 6 | Valid args, long args, custom config, missing/invalid args |

```bash
# Run all tests
python3 -m pytest test_redis_client.py -v

# Run single test class
python3 -m pytest test_redis_client.py::TestScanKeys -v

# Run single test
python3 -m pytest test_redis_client.py::TestScanKeys::test_scan_keys_cluster_dict_response -v
```

## Docker

N/A — No Docker setup. This is a local CLI tool.

## Logging

Print-based output only (no logging framework). Key output patterns:
- Status messages: `print(f"Setting up for {env}")`
- Key display: Formatted with `=` separators showing KEY, TYPE, TTL
- Errors: `print(f"Error: ...")` followed by `sys.exit(1)` for fatal errors

## Coding Conventions

**Language-level:**
- `snake_case` for functions and variables
- `PascalCase` for test class names (prefixed with `Test`)
- No type hints — uses docstrings for function documentation
- f-strings for string formatting
- Single file structure (no packages/modules)

**Project-level:**
- Functional style — no classes in main code, only standalone functions
- Config-driven — all environment details in `config.json`, no hardcoded values
- argparse for CLI interface with short (`-e`) and long (`--env`) flags
- Tests mirror function structure — one test class per logical group

## Key Files

| File | Purpose |
|---|---|
| `redis-client.py` | Main CLI tool (~220 lines) — all Redis operations |
| `test_redis_client.py` | Test suite (~490 lines) — 38 tests in 7 classes |
| `config.json` | Environment configuration (host/port/password per env) |
| `requirements.txt` | Python dependencies (4 packages) |
| `Readme.MD` | Comprehensive usage guide with examples |
| `COST.md` | Development cost report |
| `.gitignore` | Standard Python gitignore |

## Notes / Known Issues

- **config.json is required** — The tool exits with error if config.json is missing. There are no hardcoded defaults.
- **redis-py-cluster is legacy** — The `redis-py-cluster` package (2.1.3) is unmaintained. `redis-py` 4.1+ has native cluster support via `redis.cluster.RedisCluster`. Migration would simplify dependencies.
- **Single SCAN call** — `scan_keys()` makes one SCAN call with `count=1000`. For datasets with more than ~1000 keys matching the pattern, not all keys may be returned. A cursor-based loop would be more thorough.
- **Lookup only supports exact match** — The `-l` flag matches `field == value` exactly. No support for nested fields, arrays, or partial matching (noted as TODO in code).
- **File naming** — `redis-client.py` uses a dash, requiring `importlib.util` for test imports instead of standard `import`.

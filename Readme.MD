# Redis Client - Pattern-Based Key Management Tool

A high-performance command-line tool for managing Redis keys across multiple environments with pattern matching, filtering, and batch operations.

## Features

- **Non-blocking Operations**: Uses SCAN cursor iteration instead of blocking KEYS command
- **Batch Deletion**: Deletes multiple keys in a single operation for better performance
- **Pattern Matching**: Find keys using wildcard patterns (e.g., `user:*`, `session:*`)
- **Field Filtering**: Filter keys by JSON field values (e.g., `userId:12345`)
- **Multi-Environment Support**: Easily switch between PROD, STAGE, DEV, and LOCAL environments
- **External Configuration**: JSON-based config file for easy environment management
- **Safe Operations**: Graceful error handling and connection cleanup
- **Display & Delete**: View key details before deletion
- **Comprehensive Testing**: 35+ unit tests ensuring reliability

## Installation

### 1. Clone or Navigate to Repository

```bash
cd /path/to/redis-client
```

### 2. Set Up Virtual Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
# Install all required packages
pip install -r requirements.txt
```

## Configuration

### config.json (Required)

The tool requires `config.json` for environment configuration. Create or edit this file to add your Redis connection details:

```json
{
  "environments": {
    "PROD": {
      "host": "redis-prod.example.com",
      "port": 6379,
      "password": ""
    },
    "STAGE": {
      "host": "redis-stage.example.com",
      "port": 6379,
      "password": ""
    },
    "DEV": {
      "host": "redis-dev.example.com",
      "port": 6379,
      "password": ""
    },
    "LOCAL": {
      "host": "localhost",
      "port": 6379,
      "password": ""
    }
  }
}
```

### Custom Config File

You can specify a custom configuration file:

```bash
python3 redis-client.py -e DEV -k "test:*" --config /path/to/custom-config.json
```

**Note**: The `config.json` file is required. The tool will exit with an error if the configuration file is not found or contains invalid JSON.

## Usage

### Command-Line Options

```
usage: redis-client.py [-h] -e {PROD,STAGE,DEV,LOCAL} -k KEY [-l LOOKUP]
                       [-d DISPLAY] [-dl DELETE] [--config CONFIG]

Arguments:
  -h, --help            Show help message and exit
  -e, --env ENV         Redis environment (PROD, STAGE, DEV, or LOCAL)
  -k, --key KEY         Key pattern with wildcard (e.g., "user:*")
  -l, --lookup LOOKUP   Filter by field:value (e.g., "userId:12345")
  -d, --display         Display key values (pass "true" to enable)
  -dl, --delete         Delete matching keys (pass "true" to enable)
  --config CONFIG       Path to configuration file (default: config.json)
```

### Basic Examples

#### 1. Display Help

```bash
python3 redis-client.py --help
```

#### 2. Find Keys Matching Pattern

```bash
# Find all keys starting with "user:"
python3 redis-client.py -e DEV -k "user:*"
```

Output:
```
Setting up for DEV
Trying to connect to redis-dev.example.com:6379
Connected successfully redis-dev.example.com:6379
Looking for keys matching the pattern: user:*
Found 42 keys
Connection closed
```

#### 3. Display Key Values

```bash
# Display all session keys and their values
python3 redis-client.py -e DEV -k "session:*" -d true
```

Output:
```
=============================[KEY: session:abc123, TYPE: string, TTL(ms): 3600000]=============================
VALUE: {"userId":"12345","loginTime":"2024-01-01T10:00:00Z"}
Keys found with given pattern: 5
```

#### 4. Filter by Field Value

```bash
# Find keys where userId field equals "12345"
python3 redis-client.py -e DEV -k "user:*" -l "userId:12345" -d true
```

#### 5. Delete Keys (with Preview)

```bash
# Step 1: Preview keys to be deleted
python3 redis-client.py -e DEV -k "temp:*" -d true

# Step 2: Delete after confirming
python3 redis-client.py -e DEV -k "temp:*" -dl true
```

Output:
```
Deleting 100 keys in batch
Successfully deleted 100 keys
```

#### 6. Combined Operations

```bash
# Find, filter, display, and delete in one command
python3 redis-client.py -e DEV -k "cache:*" -l "expired:true" -d true -dl true
```

### Advanced Examples

#### Long-Form Arguments

```bash
python3 redis-client.py --env PROD --key "session:*" --display true --delete false
```

#### Using Custom Config

```bash
python3 redis-client.py -e DEV -k "test:*" --config production-config.json
```

#### Production Safe Deletion

```bash
# 1. Count keys in PROD
python3 redis-client.py -e PROD -k "old-session:*"

# 2. Review sample keys
python3 redis-client.py -e PROD -k "old-session:*" -d true

# 3. Delete after approval
python3 redis-client.py -e PROD -k "old-session:*" -dl true
```

## Field Lookup (JSON Filtering)

The `-l` or `--lookup` option allows filtering keys based on JSON field values stored in Redis.

### Lookup Format

```
field:value
```

### Examples

```bash
# Find users with specific status
python3 redis-client.py -e DEV -k "user:*" -l "status:active"

# Find sessions for specific user ID
python3 redis-client.py -e DEV -k "session:*" -l "userId:12345"

# Find orders with specific state
python3 redis-client.py -e DEV -k "order:*" -l "state:pending"
```

### How It Works

1. Retrieves all keys matching the pattern
2. Fetches the value for each key
3. Parses values as JSON (skips non-JSON values gracefully)
4. Checks if the specified field equals the specified value
5. Returns only matching keys

### Supported Value Types

The lookup works with:
- **String values** containing JSON
- **Hash values** (automatically converted to dict)

Other Redis types (lists, sets) are skipped during lookup filtering.

## Performance Optimizations

### SCAN vs KEYS

**Old behavior (blocking)**:
```python
r.keys(pattern)  # Blocks Redis server
```

**New behavior (non-blocking)**:
```python
# Cursor-based iteration, never blocks
cursor = 0
while True:
    cursor, keys = r.scan(cursor, match=pattern, count=1000)
    if cursor == 0:
        break
```

**Impact**: Safe to use on production Redis instances with millions of keys.

### Batch Deletion

**Old behavior**:
```python
for key in keys:
    r.delete(key)  # N network round-trips
```

**New behavior**:
```python
r.delete(*keys)  # Single network round-trip
```

**Impact**: 10-100x faster for large key deletions.

### Code Deduplication

Eliminates duplicate value-fetching logic with reusable `get_value_by_type()` helper function.

## Testing

### Run All Tests

```bash
# Activate virtual environment
source .venv/bin/activate

# Run tests with verbose output
python3 -m pytest test_redis_client.py -v
```

### Test Coverage

- **SCAN Operations**: Pagination, error handling, empty results
- **Value Fetching**: All Redis data types (string, list, set, zset, hash, stream)
- **Batch Delete**: Success, empty list, fallback on failure
- **Lookup Validation**: Format validation, field matching, value mismatches
- **JSON Handling**: Non-JSON values, empty values, malformed JSON
- **Config Loading**: File loading, fallback, invalid JSON
- **Argument Parsing**: Valid args, missing args, invalid environments

### Example Test Output

```
============================= test session starts ==============================
test_redis_client.py::TestScanKeys::test_scan_keys_pagination PASSED     [  2%]
test_redis_client.py::TestGetValueByType::test_get_string_value PASSED   [ 11%]
test_redis_client.py::TestBatchDelete::test_batch_delete_success PASSED  [ 34%]
...
============================== 35 passed in 0.04s =============================
```

## Common Use Cases

### 1. Session Cleanup

```bash
# Find expired sessions
python3 redis-client.py -e PROD -k "session:*" -l "expired:true" -d true

# Delete expired sessions
python3 redis-client.py -e PROD -k "session:*" -l "expired:true" -dl true
```

### 2. Cache Management

```bash
# Clear all cache entries for specific service
python3 redis-client.py -e DEV -k "cache:user-service:*" -dl true

# Preview cache before clearing
python3 redis-client.py -e DEV -k "cache:*" -d true
```

### 3. Data Migration/Cleanup

```bash
# Find old data format keys
python3 redis-client.py -e PROD -k "old-format:*"

# Verify count and sample data
python3 redis-client.py -e PROD -k "old-format:*" -d true

# Delete after migration
python3 redis-client.py -e PROD -k "old-format:*" -dl true
```

### 4. Debugging

```bash
# Inspect specific user's data
python3 redis-client.py -e DEV -k "user:12345:*" -d true

# Find all keys with specific attribute
python3 redis-client.py -e DEV -k "user:*" -l "role:admin" -d true
```

## Troubleshooting

### Connection Issues

```bash
# Verify connection to Redis
python3 redis-client.py -e LOCAL -k "test:*"
```

If connection fails:
1. Check Redis is running: `redis-cli ping`
2. Verify host/port in `config.json`
3. Check password if required

### Pattern Not Matching

Ensure your pattern includes the `*` wildcard:

```bash
# ❌ Wrong
python3 redis-client.py -e DEV -k "user"

# ✓ Correct
python3 redis-client.py -e DEV -k "user*"
python3 redis-client.py -e DEV -k "user:*"
python3 redis-client.py -e DEV -k "*user*"
```

### Lookup Not Finding Keys

1. Verify the field exists in your JSON data
2. Check the field name is exact (case-sensitive)
3. Ensure the value matches exactly
4. Test without lookup first to see all keys

```bash
# First see all keys
python3 redis-client.py -e DEV -k "user:*" -d true

# Then add lookup filter
python3 redis-client.py -e DEV -k "user:*" -l "userId:12345" -d true
```

## Safety Features

- **Non-blocking operations**: SCAN doesn't freeze Redis server
- **Batch delete fallback**: Falls back to individual deletes if batch fails
- **Connection cleanup**: Ensures connections are properly closed
- **Error handling**: Graceful handling of connection errors, invalid JSON, missing fields
- **Config validation**: Validates configuration format and falls back to defaults
- **Pattern validation**: Requires wildcard in pattern to prevent accidental operations

## Backward Compatibility

All existing command formats continue to work:

```bash
# Old format still supported
python redis-client.py -e dev --key res* --display true --delete true

# New format (recommended)
python3 redis-client.py -e DEV -k "res*" -d true -dl true
```

## Requirements

- Python 3.9+
- redis-py-cluster 2.1.3
- redis 3.5.3
- pytest 7.4.3 (for testing)
- pytest-mock 3.12.0 (for testing)

## Contributing

When adding new features:

1. Update the code with proper error handling
2. Add unit tests to `test_redis_client.py`
3. Update this README with usage examples
4. Test against local Redis before production

## License

Internal tool for Redis key management.

## Support

For issues or questions:
1. Check the Troubleshooting section
2. Review test cases for usage patterns
3. Verify configuration in `config.json`
4. Test against LOCAL environment first

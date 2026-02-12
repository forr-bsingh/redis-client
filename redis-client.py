#!/usr/bin/env python3

# step 1: import the redis-py client package
from rediscluster import RedisCluster
import sys
import json
import argparse

servers = dict([
    ('PROD','redis-prod.example.com'),
    ('STAGE','redis-stage.example.com'),
    ('DEV','redis-dev.example.com'),
    ('LOCAL', 'localhost')
    ])

ports = dict([
    ('PROD','6379'),
    ('STAGE','6379'),
    ('DEV','6379'),
    ('LOCAL', '6379')
    ])

# step 2: define our connection information for Redis
# Replaces with your configuration information

def load_config(config_path="config.json"):
    """Load configuration from JSON file"""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: Config file {config_path} not found, using defaults")
        return None
    except json.JSONDecodeError as e:
        print(f"Warning: Invalid JSON in config file: {e}, using defaults")
        return None

def read_input(argv):
    """Read parameters using argparse (backward compatible interface)"""
    parser = argparse.ArgumentParser(
        description='Redis cluster management tool for pattern-based key operations',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('-e', '--env', required=True,
                       choices=['PROD', 'STAGE', 'DEV', 'LOCAL'],
                       help='Redis environment')
    parser.add_argument('-k', '--key', required=True,
                       help='Key pattern (must contain * wildcard)')
    parser.add_argument('-l', '--lookup', default="",
                       help='Filter by field:value (e.g., userId:12345)')
    parser.add_argument('-d', '--display',
                       type=lambda x: x.lower() == 'true', default=False,
                       help='Display key values (pass "true" to enable)')
    parser.add_argument('-dl', '--delete',
                       type=lambda x: x.lower() == 'true', default=False,
                       help='Delete matching keys (pass "true" to enable)')
    parser.add_argument('--config', default='config.json',
                       help='Path to configuration file')

    args = parser.parse_args(argv)

    # Validate key pattern
    if '*' not in args.key:
        parser.error("Key pattern must contain '*' for pattern matching")

    return args.env.upper(), args.key, args.lookup, args.display, args.delete, args.config

def find_connection(env, config=None):
    """Find connection details based on env from config or defaults"""
    if config and "environments" in config:
        env_config = config["environments"].get(env)
        if env_config:
            return env_config["host"], env_config["port"], env_config.get("password", "")

    # Fallback to hardcoded values
    return servers.get(env), ports.get(env), ""    

def hello_redis(redis_host, redis_port, redis_password=''):
    "Connect to redis at given host and port"
    return RedisCluster(host=redis_host, port=redis_port, password=redis_password, decode_responses=True, skip_full_coverage_check=True)


def get_value_by_type(r, key):
    """Fetch value based on Redis data type"""
    try:
        key_type = r.type(key)
        if key_type == "string":
            return r.get(key)
        elif key_type == "list":
            return r.lrange(key, 0, -1)
        elif key_type == "set":
            return r.smembers(key)
        elif key_type == "zset":
            return r.zrange(key, 0, -1, False, True)
        elif key_type == "hash":
            return r.hgetall(key)
        elif key_type == "stream":
            return ""
        else:
            return ""
    except Exception as cause:
        print(f"Could not fetch value for key {key}: {cause}")
        return ""

def scan_keys(r, pattern):
    """Returns a list of all keys matching pattern using SCAN (non-blocking)"""
    keys = []
    cursor = 0
    try:
        while True:
            cursor, partial_keys = r.scan(cursor, match=pattern, count=1000)
            keys.extend(partial_keys)
            if cursor == 0:
                break
        return keys
    except Exception as error:
        print(f"Exception while scanning keys: {error}")
        return []

def lookup_by_field(r, result, lookup):
    "Lookup for keys with given field and data"
    # TODO: Fix this -:>
    # Support patterns for look up can be field:data,data,data or field.field.field:data,data,data or field.[].field:data,data,data
    # jobj = json.loads(value);
    # print([x for x in jobj["userAccessGroups"] if x["registrationID"] == "1-74B5S4" ])
    # print([x for x in jobj["services"] if x["accessLevel"] == "VIP" ])
    # print(jobj["userAccessGroups"][0]["registrationID"])

    if ":" not in lookup or lookup.count(":") != 1:
        print("Error: Lookup must be in format field:value")
        return []

    field, data = lookup.split(":", 1)
    filtered_result = []

    for key in result:
        try:
            value = get_value_by_type(r, key)
            if value and isinstance(value, str):
                try:
                    jobj = json.loads(value)
                    if isinstance(jobj, dict) and field in jobj and jobj[field] == data:
                        print(f"Found key for [{lookup}]: {key}")
                        filtered_result.append(key)
                except json.JSONDecodeError:
                    pass  # Skip non-JSON values
        except Exception as cause:
            print(f"Could not fetch value for key {key}: {cause}")

    return filtered_result
    
def print_keys(r, result):
    "Print keys to standard display"

    for key in result:
        try:
            key_type = r.type(key)
            ttl = r.pttl(key)
            print(f"{'='*29}[KEY: {key}, TYPE: {key_type}, TTL(ms): {ttl}]{'='*29}")
            value = get_value_by_type(r, key)
            print(f"VALUE: {value}")
            # Use the below code to handle json formatting.
            # print("VALUE: ", json.dumps(json.loads(value), indent=4))
        except Exception as cause:
            print(f"Could not fetch value for key {key}: {cause}")
    print(f"Keys found with given pattern: {len(result)}")

def delete_keys(r, result):
    """Delete the given list of keys in a single batch operation"""
    if not result:
        print("No keys to delete")
        return

    print(f"Deleting {len(result)} keys in batch")
    try:
        deleted_count = r.delete(*result)
        print(f"Successfully deleted {deleted_count} keys")
    except Exception as cause:
        print(f"Batch delete failed, falling back to individual deletes: {cause}")
        # Fallback to individual deletes if batch fails
        for key in result:
            try:
                r.delete(key)
                print(f"Deleted: {key}")
            except Exception as e:
                print(f"Delete failed for key {key}: {e}")

if __name__ == '__main__':
    r = None
    try:
        env, key_pattern, lookup, display, delete, config_path = read_input(sys.argv[1:])
        print(f'Setting up for {env}')

        # Load configuration
        config = load_config(config_path)

        # Get connection details
        redis_host, redis_port, redis_password = find_connection(env, config)
        print(f"Trying to connect to {redis_host}:{redis_port}")

        # Connect to Redis
        r = hello_redis(redis_host, redis_port, redis_password)
        print(f"Connected successfully {redis_host}:{redis_port}")

        # Scan for keys
        print(f"Looking for keys matching the pattern: {key_pattern}")
        result = scan_keys(r, key_pattern)
        print(f"Found {len(result)} keys")

        # Apply lookup filter if provided
        if lookup != "":
            print(f"Looking for keys matching the lookup pattern: {lookup}")
            result = lookup_by_field(r, result, lookup)
            print(f"Lookup found {len(result)} keys")

        # Display keys if requested
        if display:
            print_keys(r, result)

        # Delete keys if requested
        if delete:
            delete_keys(r, result)

    finally:
        if r:
            r.close()
            print("Connection closed")

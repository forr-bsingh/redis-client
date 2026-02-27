#!/usr/bin/env python3

import pytest
import json
import sys
import os
from unittest.mock import Mock, MagicMock, patch, mock_open
from io import StringIO

# Import the functions we want to test
# We need to handle the redis-client.py module name with a dash
import importlib.util
spec = importlib.util.spec_from_file_location("redis_client", "redis-client.py")
redis_client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(redis_client)


class TestScanKeys:
    """Test the SCAN-based key scanning functionality"""

    def test_scan_keys_cluster_dict_response(self):
        """Verify handling of RedisCluster dict response from multiple nodes"""
        mock_redis = Mock()
        # RedisCluster returns {node_name: (cursor, [keys]), ...}
        mock_redis.scan.return_value = {
            "10.0.0.1:6379": (0, ["key1", "key2", "key3"]),
            "10.0.0.2:6379": (0, ["key4", "key5"]),
            "10.0.0.3:6379": (0, ["key6"]),
        }

        result = redis_client.scan_keys(mock_redis, "test:*")

        assert len(result) == 6
        assert mock_redis.scan.call_count == 1
        mock_redis.scan.assert_called_once_with(match="test:*", count=1000)

    def test_scan_keys_standard_redis_response(self):
        """Verify handling of standard redis (cursor, [keys]) response"""
        mock_redis = Mock()
        mock_redis.scan.return_value = (0, ["key1", "key2"])

        result = redis_client.scan_keys(mock_redis, "test:*")

        assert len(result) == 2
        assert result == ["key1", "key2"]

    def test_scan_keys_error_handling(self):
        """Verify error handling returns empty list"""
        mock_redis = Mock()
        mock_redis.scan.side_effect = Exception("Connection error")

        result = redis_client.scan_keys(mock_redis, "test:*")

        assert result == []

    def test_scan_keys_empty_result(self):
        """Verify handling of pattern with no matches on cluster"""
        mock_redis = Mock()
        mock_redis.scan.return_value = {
            "10.0.0.1:6379": (0, []),
            "10.0.0.2:6379": (0, []),
        }

        result = redis_client.scan_keys(mock_redis, "nonexistent:*")

        assert result == []

    def test_scan_keys_empty_standard_response(self):
        """Verify handling of empty standard redis response"""
        mock_redis = Mock()
        mock_redis.scan.return_value = (0, [])

        result = redis_client.scan_keys(mock_redis, "nonexistent:*")

        assert result == []


class TestGetValueByType:
    """Test value fetching by Redis data type"""

    def test_get_string_value(self):
        """Test fetching string type"""
        mock_redis = Mock()
        mock_redis.type.return_value = "string"
        mock_redis.get.return_value = "test_value"

        result = redis_client.get_value_by_type(mock_redis, "test:key")

        assert result == "test_value"
        mock_redis.get.assert_called_once_with("test:key")

    def test_get_list_value(self):
        """Test fetching list type"""
        mock_redis = Mock()
        mock_redis.type.return_value = "list"
        mock_redis.lrange.return_value = ["item1", "item2", "item3"]

        result = redis_client.get_value_by_type(mock_redis, "test:list")

        assert result == ["item1", "item2", "item3"]
        mock_redis.lrange.assert_called_once_with("test:list", 0, -1)

    def test_get_set_value(self):
        """Test fetching set type"""
        mock_redis = Mock()
        mock_redis.type.return_value = "set"
        mock_redis.smembers.return_value = {"member1", "member2"}

        result = redis_client.get_value_by_type(mock_redis, "test:set")

        assert result == {"member1", "member2"}

    def test_get_zset_value(self):
        """Test fetching sorted set type"""
        mock_redis = Mock()
        mock_redis.type.return_value = "zset"
        mock_redis.zrange.return_value = [("member1", 1.0), ("member2", 2.0)]

        result = redis_client.get_value_by_type(mock_redis, "test:zset")

        assert result == [("member1", 1.0), ("member2", 2.0)]
        mock_redis.zrange.assert_called_once_with("test:zset", 0, -1, False, True)

    def test_get_hash_value(self):
        """Test fetching hash type"""
        mock_redis = Mock()
        mock_redis.type.return_value = "hash"
        mock_redis.hgetall.return_value = {"field1": "value1", "field2": "value2"}

        result = redis_client.get_value_by_type(mock_redis, "test:hash")

        assert result == {"field1": "value1", "field2": "value2"}

    def test_get_stream_value(self):
        """Test fetching stream type returns empty"""
        mock_redis = Mock()
        mock_redis.type.return_value = "stream"

        result = redis_client.get_value_by_type(mock_redis, "test:stream")

        assert result == ""

    def test_get_unknown_type(self):
        """Test fetching unknown type returns empty"""
        mock_redis = Mock()
        mock_redis.type.return_value = "unknown"

        result = redis_client.get_value_by_type(mock_redis, "test:unknown")

        assert result == ""

    def test_get_value_error_handling(self):
        """Test error handling in get_value_by_type"""
        mock_redis = Mock()
        mock_redis.type.side_effect = Exception("Connection error")

        result = redis_client.get_value_by_type(mock_redis, "test:key")

        assert result == ""


class TestBatchDelete:
    """Test batch deletion functionality"""

    def test_batch_delete_success(self, capsys):
        """Verify single delete command with multiple keys"""
        mock_redis = Mock()
        mock_redis.delete.return_value = 3
        keys = ["key1", "key2", "key3"]

        redis_client.delete_keys(mock_redis, keys)

        # Verify single delete call with all keys
        mock_redis.delete.assert_called_once_with("key1", "key2", "key3")

        # Verify output
        captured = capsys.readouterr()
        assert "Deleting 3 keys in batch" in captured.out
        assert "Successfully deleted 3 keys" in captured.out

    def test_batch_delete_empty_list(self, capsys):
        """Verify handling of empty key list"""
        mock_redis = Mock()

        redis_client.delete_keys(mock_redis, [])

        # Verify no delete call
        mock_redis.delete.assert_not_called()

        # Verify output
        captured = capsys.readouterr()
        assert "No keys to delete" in captured.out

    def test_batch_delete_fallback(self, capsys):
        """Verify fallback to individual deletes on batch failure"""
        mock_redis = Mock()
        # First call (batch) fails, subsequent calls (individual) succeed
        mock_redis.delete.side_effect = [
            Exception("Batch delete failed"),
            None,  # key1 deleted
            None,  # key2 deleted
            None   # key3 deleted
        ]
        keys = ["key1", "key2", "key3"]

        redis_client.delete_keys(mock_redis, keys)

        # Verify 4 calls: 1 batch attempt + 3 individual
        assert mock_redis.delete.call_count == 4

        # Verify output
        captured = capsys.readouterr()
        assert "Batch delete failed, falling back to individual deletes" in captured.out
        assert "Deleted: key1" in captured.out
        assert "Deleted: key2" in captured.out
        assert "Deleted: key3" in captured.out


class TestLookupValidation:
    """Test lookup field:value format validation"""

    def test_lookup_valid_format(self):
        """Test valid field:value format"""
        mock_redis = Mock()
        mock_redis.type.return_value = "string"
        test_data = {"userId": "12345", "status": "active"}
        mock_redis.get.return_value = json.dumps(test_data)

        result = redis_client.lookup_by_field(mock_redis, ["test:key"], "userId:12345")

        assert len(result) == 1
        assert result[0] == "test:key"

    def test_lookup_invalid_format_no_colon(self, capsys):
        """Test lookup without colon"""
        mock_redis = Mock()

        result = redis_client.lookup_by_field(mock_redis, ["test:key"], "invalidformat")

        assert result == []
        captured = capsys.readouterr()
        assert "Error: Lookup must be in format field:value" in captured.out

    def test_lookup_invalid_format_multiple_colons(self, capsys):
        """Test lookup with multiple colons"""
        mock_redis = Mock()

        result = redis_client.lookup_by_field(mock_redis, ["test:key"], "field:value:extra")

        assert result == []
        captured = capsys.readouterr()
        assert "Error: Lookup must be in format field:value" in captured.out

    def test_lookup_field_not_found(self):
        """Test lookup when field doesn't exist in JSON"""
        mock_redis = Mock()
        mock_redis.type.return_value = "string"
        test_data = {"status": "active"}
        mock_redis.get.return_value = json.dumps(test_data)

        result = redis_client.lookup_by_field(mock_redis, ["test:key"], "userId:12345")

        assert result == []

    def test_lookup_field_value_mismatch(self):
        """Test lookup when field exists but value doesn't match"""
        mock_redis = Mock()
        mock_redis.type.return_value = "string"
        test_data = {"userId": "99999"}
        mock_redis.get.return_value = json.dumps(test_data)

        result = redis_client.lookup_by_field(mock_redis, ["test:key"], "userId:12345")

        assert result == []


class TestJSONErrorHandling:
    """Test graceful handling of non-JSON values"""

    def test_lookup_non_json_value(self):
        """Test lookup skips non-JSON values gracefully"""
        mock_redis = Mock()
        mock_redis.type.return_value = "string"
        mock_redis.get.return_value = "not a json string"

        result = redis_client.lookup_by_field(mock_redis, ["test:key"], "field:value")

        assert result == []

    def test_lookup_empty_value(self):
        """Test lookup handles empty values"""
        mock_redis = Mock()
        mock_redis.type.return_value = "string"
        mock_redis.get.return_value = ""

        result = redis_client.lookup_by_field(mock_redis, ["test:key"], "field:value")

        assert result == []

    def test_lookup_non_string_value(self):
        """Test lookup handles non-string values"""
        mock_redis = Mock()
        mock_redis.type.return_value = "list"
        mock_redis.lrange.return_value = ["item1", "item2"]

        result = redis_client.lookup_by_field(mock_redis, ["test:key"], "field:value")

        assert result == []

    def test_lookup_non_dict_json(self):
        """Test lookup handles JSON that isn't a dictionary"""
        mock_redis = Mock()
        mock_redis.type.return_value = "string"
        mock_redis.get.return_value = json.dumps(["array", "of", "values"])

        result = redis_client.lookup_by_field(mock_redis, ["test:key"], "field:value")

        assert result == []


class TestConfigLoading:
    """Test configuration file loading with fallbacks"""

    def test_load_config_success(self):
        """Test successful config loading"""
        config_data = {
            "environments": {
                "TEST": {
                    "host": "test.example.com",
                    "port": 6379,
                    "password": "testpass"
                }
            }
        }
        mock_file = mock_open(read_data=json.dumps(config_data))

        with patch('builtins.open', mock_file):
            config = redis_client.load_config("config.json")

        assert config is not None
        assert "environments" in config
        assert "TEST" in config["environments"]
        assert config["environments"]["TEST"]["host"] == "test.example.com"

    def test_load_config_file_not_found(self, capsys):
        """Test config loading when file doesn't exist - should exit"""
        with patch('builtins.open', side_effect=FileNotFoundError):
            with pytest.raises(SystemExit) as exc_info:
                redis_client.load_config("nonexistent.json")

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error: Config file nonexistent.json not found" in captured.out

    def test_load_config_invalid_json(self, capsys):
        """Test config loading with invalid JSON - should exit"""
        mock_file = mock_open(read_data="{ invalid json }")

        with patch('builtins.open', mock_file):
            with pytest.raises(SystemExit) as exc_info:
                redis_client.load_config("config.json")

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error: Invalid JSON in config file" in captured.out

    def test_find_connection_with_config(self):
        """Test find_connection using config"""
        config = {
            "environments": {
                "TEST": {
                    "host": "test.example.com",
                    "port": 6380,
                    "password": "testpass"
                }
            }
        }

        host, port, password = redis_client.find_connection("TEST", config)

        assert host == "test.example.com"
        assert port == 6380
        assert password == "testpass"

    def test_find_connection_without_config(self, capsys):
        """Test find_connection exits when no config provided"""
        with pytest.raises(SystemExit) as exc_info:
            redis_client.find_connection("LOCAL", None)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Invalid configuration format" in captured.out

    def test_find_connection_missing_password(self):
        """Test find_connection with config missing password"""
        config = {
            "environments": {
                "TEST": {
                    "host": "test.example.com",
                    "port": 6379
                }
            }
        }

        host, port, password = redis_client.find_connection("TEST", config)

        assert host == "test.example.com"
        assert port == 6379
        assert password == ""

    def test_find_connection_env_not_found(self, capsys):
        """Test find_connection exits when environment not in config"""
        config = {
            "environments": {
                "TEST": {
                    "host": "test.example.com",
                    "port": 6379
                }
            }
        }

        with pytest.raises(SystemExit) as exc_info:
            redis_client.find_connection("NONEXISTENT", config)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Environment 'NONEXISTENT' not found" in captured.out


class TestArgParse:
    """Test argparse implementation"""

    def test_read_input_valid_args(self):
        """Test reading valid arguments"""
        argv = ["-e", "DEV", "-k", "test:*", "-l", "field:value", "-d", "true", "-dl", "false"]

        env, key, lookup, display, delete, config = redis_client.read_input(argv)

        assert env == "DEV"
        assert key == "test:*"
        assert lookup == "field:value"
        assert display is True
        assert delete is False
        assert config == "config.json"

    def test_read_input_long_args(self):
        """Test reading long-form arguments"""
        argv = ["--env", "PROD", "--key", "session:*", "--display", "true"]

        env, key, lookup, display, delete, config = redis_client.read_input(argv)

        assert env == "PROD"
        assert key == "session:*"
        assert display is True

    def test_read_input_custom_config(self):
        """Test reading with custom config path"""
        argv = ["-e", "LOCAL", "-k", "test:*", "--config", "custom.json"]

        env, key, lookup, display, delete, config = redis_client.read_input(argv)

        assert config == "custom.json"

    def test_read_input_missing_wildcard(self):
        """Test validation of key pattern requires wildcard"""
        argv = ["-e", "DEV", "-k", "testwithoutstar"]

        with pytest.raises(SystemExit):
            redis_client.read_input(argv)

    def test_read_input_missing_required_args(self):
        """Test error when required args are missing"""
        argv = ["-e", "DEV"]  # Missing -k

        with pytest.raises(SystemExit):
            redis_client.read_input(argv)

    def test_read_input_invalid_env(self):
        """Test error with invalid environment"""
        argv = ["-e", "INVALID", "-k", "test:*"]

        with pytest.raises(SystemExit):
            redis_client.read_input(argv)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

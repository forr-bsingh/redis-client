# Plan: Create CLAUDE.md for redis-client

## Context
The redis-client project lacks a CLAUDE.md file. This is a Python CLI tool for managing Redis keys across multiple environments (PROD, STAGE, DEV, LOCAL) using non-blocking SCAN operations. Creating CLAUDE.md will improve project understanding for future sessions.

## Tasks

- [ ] Create `CLAUDE.md` at project root with all 11 required sections per template
- [ ] Verify all sections are present and accurate
- [ ] Run tests to confirm test count and passing status

## Sections to Include

1. **Quick Reference** - Python 3.9+, pip, pytest, redis-py-cluster, no framework
2. **Build & Run Commands** - venv setup, pip install, pytest, CLI usage examples
3. **Architecture** - Functional pipeline: config -> args -> connect -> scan -> filter -> display/delete
4. **Cross-Cutting Patterns** - Error handling (try-except + sys.exit), RedisCluster dict response handling
5. **Key Dependencies** - redis-py-cluster 2.1.3, redis 3.5.3, pytest 7.4.3, pytest-mock 3.12.0
6. **Testing** - pytest, 35+ tests in 7 classes, mock-based (no real Redis needed)
7. **Docker** - N/A
8. **Logging** - Print-based output (no logging framework)
9. **Coding Conventions** - snake_case functions, PascalCase test classes, no type hints
10. **Key Files** - redis-client.py, test_redis_client.py, config.json, requirements.txt
11. **Notes / Known Issues** - config.json required, redis-py-cluster is legacy

## Effort
- Without Claude: ~30 min
- With Claude: ~2 min

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Core Development Commands

### Installation and Setup
```bash
# Install with development dependencies
make install-dev

# Install in editable mode (preferred for development)
make install-editable

# Set up environment
cp .env.template .env
# Edit .env to enable plugins (set PLUGINS_ENABLED=true)
```

### Testing
```bash
# Run all tests
make test

# Run tests with coverage and detailed output (configured in pytest.ini)
pytest tests

# Run specific test file
pytest tests/test_kubectlcmdprocessor.py
```

### Code Quality
```bash
# Fix linting issues (uses black + ruff)
make lint-fix

# Check for linting issues without fixing
make lint-check

# Target specific files
make lint-fix path/to/file.py
```

### Container Operations
```bash
# Build container image
make build

# Run container server
make start

# Stop container
make stop

# View container logs
make container-logs

# Open shell in running container
make container-shell
```

## Project Architecture

### Core Components

**kubectlcmdprocessor/**: Main package containing the kubectl command processing logic
- `parser.py`: Contains `KubectlParser` class that tokenizes and parses kubectl commands into structured data
- `plugin.py`: Implements `KubectlCmdProcessor` plugin that integrates with MCP Gateway framework
- `__init__.py`: Package metadata and version information

**Plugin Framework Integration**: Built on top of `mcp-contextforge-gateway` and `chuk-mcp-runtime`
- Implements hook-based architecture with pre/post processing for prompts and tools
- Supports multiple execution hooks: `prompt_pre_fetch`, `prompt_post_fetch`, `tool_pre_invoke`, `tool_post_invoke`

### Configuration Structure

**resources/plugins/config.yaml**: Plugin configuration defining:
- Plugin registration with MCP Gateway
- Hook assignments and priorities
- Execution modes (enforce/permissive/disabled)
- Plugin-specific settings

**resources/runtime/config.yaml**: Chuck MCP Runtime configuration for:
- Server types (stdio/sse/streamable-http)
- Logging levels and quiet library settings
- HTTP server configuration (host, port, endpoints)
- Session and artifact management settings

### Key Dependencies

- `chuk-mcp-runtime>=0.6.5`: Runtime framework for MCP server execution
- `mcp-contextforge-gateway`: Plugin framework for MCP Gateway integration
- Development tools: black, ruff, pytest suite with asyncio support

### Testing Strategy

Tests use pytest with asyncio support and focus on:
- Plugin hook functionality verification
- Command parsing validation (see comprehensive test cases in `parser.py` main function)
- Integration with MCP Gateway framework

### Container Deployment

Supports both Docker and Podman with automatic runtime detection:
- Multi-architecture builds (linux/amd64, linux/arm64)
- Health checks and resource limits
- Environment-based configuration via `.env` file

## Development Workflow

1. Make changes to parser logic in `kubectlcmdprocessor/parser.py`
2. Update plugin hooks in `kubectlcmdprocessor/plugin.py` if needed
3. Run `make lint-fix` to ensure code quality
4. Run `make test` to verify functionality
5. Test containerized deployment with `make build && make start`

The parser supports comprehensive kubectl command patterns including resource operations, file-based operations, complex flags, subcommands, and edge cases. See the main function in `parser.py` for extensive test examples.
# MCP Server Template

A clean template for building Model Context Protocol (MCP) servers using Python and `fastmcp`.

This template is configured to use **SSE (Server-Sent Events) transport** over HTTP on port **9000**, making it compatible with various MCP clients that support HTTP/SSE.

## Features

- 🚀 **FastMCP**: Built on top of the high-performance FastMCP framework.
- 📡 **HTTP/SSE Transport**: Ready for remote connections or local HTTP integration.
- 📦 **Modern Tooling**: managed with `uv`.

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended for dependency management)

## Installation

1. Install dependencies:

```bash
uv sync
```

2. (Optional) Configure environment variables:

```bash
cp .env.example .env
# Edit .env if needed
```

## Usage

### Running the Server

You can run the server directly using `uv`:

```bash
uv run mcp-server
```

Or using python directly:

```bash
uv run python -m template_server.server
```

The server will start on `http://127.0.0.1:9000/sse`.

### Customization

1. **Rename the project**: Edit `pyproject.toml` and change `name` and `description`.
2. **Add Tools**: Open `src/template_server/server.py` and add your own functions decorated with `@mcp.tool()`.
3. **Add Resources**: Use `@mcp.resource()` to expose data resources.

## Project Structure

```
mcp-template/
├── src/
│   └── template_server/
│       ├── __init__.py
│       └── server.py      # Main server logic and tools
├── pyproject.toml         # Dependencies and Metadata
├── .env.example           # Environment variable template
└── README.md              # Documentation
```

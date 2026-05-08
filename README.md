<div align="center">

# Hr Management Ai MCP

**MCP server for hr management ai mcp operations**

[![PyPI](https://img.shields.io/pypi/v/meok-hr-management-ai-mcp)](https://pypi.org/project/meok-hr-management-ai-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MEOK AI Labs](https://img.shields.io/badge/MEOK_AI_Labs-MCP_Server-purple)](https://meok.ai)

</div>

## Overview

Hr Management Ai MCP provides AI-powered tools via the Model Context Protocol (MCP).

## Tools

| Tool | Description |
|------|-------------|
| `leave_calculator` | Calculate leave balance, accrual rate, and year-end projections based on |
| `payroll_estimator` | Estimate net pay with tax brackets, Social Security, Medicare, retirement |
| `performance_review` | Draft a structured performance review with tier assessment, strengths, |
| `onboarding_checklist` | Generate a phased onboarding checklist covering pre-start through 90 days |
| `compliance_checker` | Check applicable employment compliance frameworks based on region, |

## Installation

```bash
pip install meok-hr-management-ai-mcp
```

## Usage with Claude Desktop

Add to your Claude Desktop MCP config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "hr-management-ai-mcp": {
      "command": "python",
      "args": ["-m", "meok_hr_management_ai_mcp.server"]
    }
  }
}
```

## Usage with FastMCP

```python
from mcp.server.fastmcp import FastMCP

# This server exposes 5 tool(s) via MCP
# See server.py for full implementation
```

## License

MIT © [MEOK AI Labs](https://meok.ai)

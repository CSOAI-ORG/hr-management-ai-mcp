# HR Management AI MCP Server
**By MEOK AI Labs** | [meok.ai](https://meok.ai)

Human resources toolkit: leave calculation, payroll estimation, performance reviews, onboarding checklists, and compliance checking.

## Tools

| Tool | Description |
|------|-------------|
| `leave_calculator` | Calculate leave balance with regional policies and tenure bonuses |
| `payroll_estimator` | Net pay estimation with tax brackets and deductions |
| `performance_review` | Structured performance review with tier assessment |
| `onboarding_checklist` | Phased onboarding checklist from pre-start through 90 days |
| `compliance_checker` | Check applicable employment compliance frameworks |

## Installation

```bash
pip install mcp
```

## Usage

### Run the server

```bash
python server.py
```

### Claude Desktop config

```json
{
  "mcpServers": {
    "hr-management": {
      "command": "python",
      "args": ["/path/to/hr-management-ai-mcp/server.py"]
    }
  }
}
```

## Pricing

| Tier | Limit | Price |
|------|-------|-------|
| Free | 30 calls/day | $0 |
| Pro | Unlimited + premium features | $9/mo |
| Enterprise | Custom + SLA + support | Contact us |

## License

MIT

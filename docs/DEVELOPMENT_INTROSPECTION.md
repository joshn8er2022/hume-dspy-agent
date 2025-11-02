# Development Introspection System

## Overview

StrategyAgent now has the ability to introspect system behavior via Phoenix traces and communicate development needs. This enables self-aware debugging and optimization.

## Architecture

### Components

1. **DevelopmentIntrospection** (`agents/development_introspection.py`)
   - Analyzes Phoenix spans for patterns
   - Detects development needs (bugs, performance, optimizations)
   - Identifies system "levers" (configurable parameters)

2. **DevelopmentAgentExtension** (`agents/development_agent_extension.py`)
   - Hooks into StrategyAgent's execution lifecycle
   - Triggers Phoenix analysis on errors or development requests
   - Formats insights for developer communication

3. **Phoenix MCP Integration**
   - Uses Phoenix MCP server to query traces
   - Reads last 100 spans for pattern analysis
   - Provides observability data for decision-making

## How It Works

### Automatic Triggering

The extension automatically triggers when:

1. **Errors occur** - Detects patterns like:
   - High error rates (>10% of spans)
   - Repeated failures
   - Timeout/connection issues
   - Critical system errors

2. **Development keywords detected** - In user messages:
   - "debug", "analyze", "investigate"
   - "phoenix", "traces", "spans"
   - "development", "issue"

3. **Periodic analysis** - Every 6 hours:
   - Analyzes recent behavior
   - Identifies trends and patterns
   - Flags optimization opportunities

### Phoenix MCP Query

When triggered, the system:

1. **Queries Phoenix MCP** for recent spans:
   ```python
   # Uses mcp_phoenix_get_spans tool
   spans = await get_phoenix_spans_via_mcp(
       project_name="hume-dspy-agent",
       limit=100,
       hours_back=24
   )
   ```

2. **Analyzes spans** for:
   - Error patterns and rates
   - Latency distributions (avg, P95, max)
   - Repeated operations
   - Timeout configurations
   - Retry patterns
   - Model selection patterns

3. **Generates insights**:
   - Development needs (bugs, performance)
   - System levers (configurable parameters)
   - Recommendations

4. **Formats for communication**:
   - Structured markdown report
   - Severity levels
   - Actionable recommendations

## System Levers Identified

The system can identify these "levers":

1. **Request Timeouts**
   - Impact: Higher = more reliability, slower failures
   - Evidence: Timeout attributes in spans

2. **Retry Configuration**
   - Impact: More retries = better reliability, more latency
   - Evidence: Retry-related spans

3. **LLM Model Selection**
   - Impact: Affects cost, latency, quality
   - Evidence: Model attributes in spans

4. **Batch Sizes**
   - Impact: Larger = more efficiency, more memory
   - Evidence: Batch operation patterns

5. **Cache TTLs**
   - Impact: Longer = better performance, stale data
   - Evidence: Cache hit/miss patterns

## Usage

### Automatic (Recommended)

The extension runs automatically when:
- Errors occur
- Development keywords in messages
- Periodic analysis interval

### Manual Triggering

From StrategyAgent conversation:
```
"Can you analyze Phoenix traces for development insights?"
"What levers can we tune based on recent behavior?"
"Debug why we're seeing slow performance"
```

### API Endpoint (Future)

Could add endpoint for manual triggering:
```python
POST /agents/strategy/development/analyze
{
    "span_limit": 100,
    "hours_back": 24
}
```

## Output Format

### Development Insights

```markdown
## 🎯 Development Insights

### HIGH: High error rate detected
**Type:** bug
**Description:** 25/100 spans show errors (25.0%)
**Recommendations:**
- Review error patterns in Phoenix dashboard
- Check Railway logs for detailed error messages
- Identify common failure patterns

### MEDIUM: High latency detected
**Type:** performance
**Description:** Average latency: 5234ms, P95: 8234ms
**Recommendations:**
- Profile slow operations
- Consider caching frequently accessed data
- Review database query performance
```

### System Levers

```markdown
## 🎛️ System Levers Identified

### Request Timeouts
**Description:** Timeout configurations for external API calls
**Impact:** Higher timeouts = more reliability but slower failures
**Current:** Not detected
**Suggested:** Monitor for timeout patterns

### LLM Model Selection
**Description:** Which models are being used for different tasks
**Impact:** Model choice affects cost, latency, and quality
**Evidence:** Found 45 spans with model selection
```

## Integration with Phoenix MCP

### Requirements

1. **Phoenix MCP Server** configured in `.cursor/mcp.json`:
```json
{
  "phoenix": {
    "command": "npx",
    "args": ["-y", "@arizeai/phoenix-mcp@latest"],
    "env": {
      "PHOENIX_API_KEY": "...",
      "PHOENIX_PROJECT_NAME": "hume-dspy-agent"
    }
  }
}
```

2. **Phoenix Project** must match:
   - Project name: `hume-dspy-agent`
   - Or set via `PHOENIX_PROJECT_NAME` environment variable

3. **MCP Tools Available**:
   - `mcp_phoenix_get_spans` - Query traces
   - `mcp_phoenix_get_span_annotations` - Get annotations
   - `mcp_phoenix_phoenix_support` - Get help

### Access Pattern

Since StrategyAgent runs in Railway (not in Cursor), it can't directly call MCP tools. However:

**Option 1: Via Developer (Recommended)**
- StrategyAgent detects development need
- Formats request with context
- Developer (me, the AI assistant) queries Phoenix MCP
- Results communicated back via Slack or log

**Option 2: Via API Endpoint**
- Create `/agents/strategy/phoenix/analyze` endpoint
- Endpoint calls Phoenix API directly (not MCP)
- StrategyAgent triggers endpoint when needed

**Option 3: Direct Phoenix API**
- StrategyAgent calls Phoenix REST API directly
- Requires Phoenix API key in Railway environment
- No MCP needed, but requires API key management

## Example Flow

1. **Error occurs** in StrategyAgent
2. **Extension triggers** `on_error` hook
3. **Detection logic** identifies as development-relevant
4. **Phoenix query** requested (either via MCP or API)
5. **Analysis** of last 100 spans
6. **Insights generated**:
   - Error rate: 15% (high)
   - Avg latency: 4.2s (acceptable)
   - Repeated pattern: Database queries
7. **Formatted message** created
8. **Communication**:
   - Sent to Slack developer channel
   - Or logged for developer review
   - Or returned in StrategyAgent response

## Benefits

1. **Self-Aware System** - Agent knows when it needs help
2. **Data-Driven Decisions** - Based on actual trace data
3. **Proactive Debugging** - Catches issues before they escalate
4. **Optimization Discovery** - Identifies tuning opportunities
5. **Developer Efficiency** - Pre-analyzed insights save time

## Future Enhancements

- Real-time Phoenix API integration (not just MCP)
- Automated fix proposals based on patterns
- Integration with monitoring/alerting
- Historical trend analysis
- Predictive insights (anomaly detection)
- Auto-tuning of system levers

## Configuration

Environment variables:
- `PHOENIX_PROJECT_NAME` - Project name (default: "hume-dspy-agent")
- `PHOENIX_API_KEY` - For direct API access (optional)
- `DEV_INTROSPECTION_ENABLED` - Enable/disable (default: true)
- `DEV_ANALYSIS_INTERVAL_HOURS` - Periodic analysis interval (default: 6)


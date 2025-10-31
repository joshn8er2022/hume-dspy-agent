# PerformanceAgent Documentation

## Overview

PerformanceAgent is the 8th agent in the Hume DSPy Agent system, responsible for autonomous performance monitoring, anomaly detection, and optimization triggering across all agents.

## Architecture

### Core Components

1. **DSPy Modules** (`dspy_modules/performance_signatures.py`)
   - `PerformanceAnalysis` - Aggregates raw metrics into insights
   - `AnomalyDetection` - Detects performance degradations
   - `OptimizationRecommendation` - Recommends optimization strategies
   - `PerformanceReport` - Generates formatted Slack reports

2. **Main Agent** (`agents/performance_agent.py`)
   - Inherits from `SelfOptimizingAgent`
   - Uses LangGraph StateGraph for workflow orchestration
   - Integrates with Phoenix MCP, Railway, and Supabase

3. **Workflow States**
   - `collect_data` - Query Phoenix, Railway, Supabase
   - `analyze_performance` - Calculate metrics per agent
   - `detect_anomalies` - Identify issues
   - `trigger_optimization` - Run GEPA/BootstrapFewShot
   - `send_reports` - Slack notifications
   - `schedule_next` - Schedule next run

## Data Collection

### Phoenix MCP Integration

Collects trace data from the last 30 minutes:

```python
spans = await phoenix_client.get_spans(
    projectName="hume-dspy-agent",
    startTime=last_check_time,
    endTime=current_time,
    limit=1000
)
```

### Supabase Integration

Queries `agent_state` table for task counts:

```sql
SELECT agent_name, COUNT(*) as task_count
FROM agent_state
WHERE status = 'completed'
GROUP BY agent_name
```

### Railway Logs

Parses application logs for errors and warnings.

## Optimization Triggering Logic

### StrategyAgent (Strategic)

- **Threshold**: 20+ tasks
- **Optimizer**: GEPA
- **Cost**: $30
- **Approval**: Required (Slack)
- **Expected Improvement**: 20-40%

### Execution Agents (Autonomous)

- **Threshold**: 10+ tasks
- **Optimizer**: BootstrapFewShot
- **Cost**: $5
- **Approval**: Not required (auto-trigger)
- **Expected Improvement**: 10-25%

## Slack Notifications

### Anomaly Alerts

Sent immediately when high/critical severity anomalies detected:

```
🚨 PERFORMANCE ALERT

Agent: InboundAgent
Severity: HIGH
Type: success_drop

Root Cause: Model degradation
Recommended Action: IMMEDIATE

Details: Success rate dropped from 85% to 0%
```

### Daily Summaries

Sent at 9 AM daily:

```
📊 Daily Performance Summary - 2025-10-27

Agent Performance:
- StrategyAgent: 92/100
- InboundAgent: 45/100

Optimization Status:
- StrategyAgent: GEPA (pending approval)
- InboundAgent: BootstrapFewShot (triggered)

Anomalies: 1 detected (high severity)
```

## Configuration

### Environment Variables

```bash
PHOENIX_PROJECT_NAME=hume-dspy-agent
PHOENIX_API_KEY=your_api_key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_key
SLACK_BOT_TOKEN=xoxb-your-token
```

### Scheduling

Runs every 30 minutes via cron:

```
*/30 * * * *
```

## API Endpoints

### Manual Trigger

```bash
POST /agents/performance/trigger
```

Response:
```json
{
  "success": true,
  "agents_analyzed": 7,
  "anomalies_detected": 1,
  "optimizations_triggered": 2,
  "slack_messages_sent": 3
}
```

### Status Check

```bash
GET /agents/performance/status
```

## Monitored Agents

1. StrategyAgent
2. InboundAgent
3. FollowUpAgent
4. ResearchAgent
5. AuditAgent
6. AccountOrchestrator
7. Introspection

## Metrics Tracked

- **Success Rate**: Percentage of successful tasks
- **Average Latency**: Mean response time in milliseconds
- **Error Count**: Total errors in period
- **Performance Score**: Overall score (0-100)
- **Trend**: improving, stable, or degrading

## Troubleshooting

### No data collected

- Verify Phoenix MCP connection
- Check Supabase credentials
- Ensure agents are running

### Optimizations not triggering

- Check task count thresholds
- Verify Slack approval workflow
- Review agent_state table

### Slack notifications not sending

- Verify SLACK_BOT_TOKEN
- Check channel permissions
- Review Slack API logs

## Testing

Run the test suite:

```bash
python test_performance_agent.py
```

Expected output:
```
ALL TESTS PASSED
PerformanceAgent implementation validated!
```

## Production Deployment

1. Set environment variables
2. Deploy to Railway
3. Configure cron job
4. Monitor Slack #ai-performance channel
5. Review daily summaries

## Future Enhancements

- Machine learning-based anomaly detection
- Predictive optimization triggering
- Custom metric definitions
- Multi-channel notifications (email, SMS)
- Historical trend analysis dashboard


# Quick Reference - Hybrid DSPy + Agent-Zero System

**Created:** 2025-10-30
**Status:** Ready for Phase 0 Implementation

---

## 📁 Document Locations

1. **MASTER PLAN** - `~/MASTER-IMPLEMENTATION-PLAN.md` (2,810 lines)
2. **Codebase Audit** - `~/codebase-audit-comparison.md` (2,810 lines)
3. **Extensibility Design** - `~/extensibility-integration-analysis.md` (47 pages)
4. **Multi-Agent Design** - `~/hybrid-multiagent-architecture.md` (59KB)
5. **Error Handling Design** - `~/error-handling-integration.md` (29 pages)
6. **Bug Diagnosis** - `~/broken-functionality-diagnosis.md`
7. **Tool System Design** - `~/pydantic-tool-system-design.md` (800 lines)
8. **Supabase Project** - `~/supabase-local-project/`

---

## 🐛 Critical Bugs to Fix First (Week 1)

### Bug #1: `analyze_pipeline()` returns mock data
- **File:** `~/hume-dspy-agent/agents/strategy_agent.py:1283`
- **Fix:** Query real Supabase data instead of hardcoded values
- **Time:** 3 hours
- **Code:** See `~/broken-functionality-diagnosis.md` Section 2.1

### Bug #2: `recommend_outbound_targets()` returns fake companies
- **File:** `~/hume-dspy-agent/agents/strategy_agent.py:1341`
- **Fix:** Use real lead patterns from Supabase
- **Time:** 4 hours
- **Code:** See `~/broken-functionality-diagnosis.md` Section 2.2

---

## 🎯 Implementation Phases

### Phase 0: Bug Fixes (Week 1) - **START HERE**
- Fix 2 broken functions above
- Zero regressions
- Ship to staging

### Phase 1: Error Handling (Weeks 1-2)
- 3-tier exceptions: `InterventionException`, `RepairableException`, `HandledException`
- DSPy-powered self-repair
- `@with_retry_logic` decorator
- **Expected:** 80% crash reduction

### Phase 2: Dynamic Tools (Weeks 2-3)
- Pydantic `BaseTool` class
- `ToolRegistry` with auto-discovery
- `DSPyToolAdapter` for ReAct integration
- **Expected:** 67% code reduction (600 → 200 lines)

### Phase 3: Multi-Agent (Weeks 3-5)
- Parallel subordinate execution
- Hierarchical memory
- **Expected:** 5-10x speedup

### Phase 4: Production (Weeks 5-6)
- 90%+ test coverage
- Monitoring/observability
- Performance benchmarks

---

## 💎 Core Principles (Non-Negotiable)

1. ✅ **Preserve DSPy** - All reasoning stays programmatic
2. ✅ **Preserve Pydantic** - Type safety throughout
3. ✅ **Minimize Breaking Changes** - Old code works during migration
4. ✅ **Incremental Rollout** - Ship weekly improvements
5. ✅ **Test Everything** - No untested production code

---

## 🔧 Key Code Patterns

### Pattern 1: Error Handling (Phase 1)
```python
from core.decorators import with_retry_logic
from core.exceptions import RepairableException, ErrorContext

@with_retry_logic(max_attempts=3, enable_llm_recovery=True)
async def my_method(self, data: MyData) -> MyResult:
    try:
        result = await self._process(data)
        return result
    except SpecificError as e:
        raise RepairableException(
            f"Processing failed: {str(e)}",
            context=ErrorContext(
                error_type="ProcessingError",
                agent_name=self.__class__.__name__,
                operation="my_method",
                recovery_hints=["Try different parameters"]
            )
        )
```

### Pattern 2: Dynamic Tools (Phase 2)
```python
from tools.base import BaseTool, ToolMetadata, ToolParameter, ToolResult
from tools.registry import ToolRegistry

# Create tool (auto-discovered)
class MyTool(BaseTool):
    metadata = ToolMetadata(
        name="my_tool",
        description="What it does",
        parameters=[...]
    )

    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult(success=True, result={...})

# Use in agent
tools = ToolRegistry.get_all()
dspy_tools = DSPyToolAdapter.adapt_all(tools)
```

### Pattern 3: Parallel Agents (Phase 3)
```python
from core.multi_agent import ParallelAgentExecutor, AgentTask

tasks = [
    AgentTask(agent_profile="researcher", task_description="..."),
    AgentTask(agent_profile="analyst", task_description="..."),
]

executor = ParallelAgentExecutor()
results = await executor.execute_parallel(tasks, self)
# 5-10x faster than sequential
```

---

## 📊 Expected Outcomes

| Metric | Current | After Implementation |
|--------|---------|---------------------|
| Unhandled Exceptions | High | 80% reduction |
| Code Size (ResearchAgent) | 600 lines | 200 lines (-67%) |
| Agent Execution Speed | 1x | 5-10x (parallel) |
| Tool Extensibility | Hardcoded | Plugin architecture |
| Test Coverage | Unknown | 90%+ |

---

## 🚀 Week 1 Quick Start

**Monday:**
1. Read `~/MASTER-IMPLEMENTATION-PLAN.md` (1 hour)
2. Fix `analyze_pipeline()` (3 hours)

**Tuesday:**
3. Fix `recommend_outbound_targets()` (4 hours)
4. Write tests for both fixes (2 hours)

**Wednesday:**
5. Deploy to staging
6. Test with real data
7. Start Phase 1 (error handling)

**Thursday-Friday:**
8. Create exception hierarchy (4 hours)
9. Create DSPy error recovery (4 hours)
10. Test error handling (2 hours)

**Ship by Friday:**
- ✅ Both bugs fixed
- ✅ Error handling working
- ✅ Zero regressions

---

## 🆘 If You Get Stuck

1. **Check the master plan:** `~/MASTER-IMPLEMENTATION-PLAN.md`
2. **Review specific design:** Check relevant analysis doc
3. **Look at code examples:** All docs have working code
4. **Test incrementally:** Don't change everything at once
5. **Rollback if needed:** Each phase has rollback plan

---

## 📝 Important Files to Commit

Before starting implementation:
```bash
cd ~/hume-dspy-agent
git add .
git commit -m "Checkpoint before hybrid architecture implementation"
git push
```

Save analysis documents:
```bash
mkdir -p ~/hume-dspy-agent/docs/architecture
cp ~/MASTER-IMPLEMENTATION-PLAN.md ~/hume-dspy-agent/docs/architecture/
cp ~/extensibility-integration-analysis.md ~/hume-dspy-agent/docs/architecture/
cp ~/hybrid-multiagent-architecture.md ~/hume-dspy-agent/docs/architecture/
cp ~/error-handling-integration.md ~/hume-dspy-agent/docs/architecture/
cp ~/pydantic-tool-system-design.md ~/hume-dspy-agent/docs/architecture/
```

---

## 🎯 Success Criteria (Overall)

- ✅ All tests passing (90%+ coverage)
- ✅ No breaking changes to existing functionality
- ✅ DSPy + Pydantic preserved
- ✅ Agent-zero patterns integrated
- ✅ Production-ready system
- ✅ 6-week timeline met

---

**Next Command:** `cd ~/hume-dspy-agent && git status`

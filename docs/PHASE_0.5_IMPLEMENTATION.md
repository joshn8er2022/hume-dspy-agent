# 🚀 Phase 0.5: Agent Zero Integration - Implementation Plan

**Start Date**: October 19, 2025, 3:52 PM PST  
**Timeline**: 1-2 weeks (condensed to 1 session for core features)  
**Status**: 🟢 IN PROGRESS

---

## **📋 Overview**

Phase 0.5 integrates powerful features from Agent Zero framework:
1. ✅ **MCP Client** - Already complete (200+ tools)
2. 🟢 **FAISS Vector Memory** - Semantic memory for agents
3. 🔴 **Instrument System** - Unlimited tools without prompt bloat

---

## **🧠 Part 1: FAISS Vector Memory**

### **Goal**
Enable agents to remember and learn from every interaction using semantic search.

### **Architecture**

```python
# memory/vector_memory.py

from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.docstore.in_memory import InMemoryDocstore
import faiss
from typing import List, Dict, Any
import json

class AgentMemory:
    """FAISS-backed semantic memory for agents"""
    
    def __init__(self, agent_name: str, embedding_dim: int = 1536):
        self.agent_name = agent_name
        self.embeddings = OpenAIEmbeddings()
        
        # Initialize FAISS index
        index = faiss.IndexFlatIP(embedding_dim)  # Inner product for cosine similarity
        
        # Create FAISS vector store
        self.vectorstore = FAISS(
            embedding_function=self.embeddings,
            index=index,
            docstore=InMemoryDocstore(),
            index_to_docstore_id={}
        )
    
    async def remember(
        self,
        content: str,
        memory_type: str,
        metadata: Dict[str, Any] = None
    ):
        """Store a memory with semantic embeddings"""
        doc_metadata = {
            "agent": self.agent_name,
            "type": memory_type,
            "timestamp": datetime.utcnow().isoformat(),
            **(metadata or {})
        }
        
        await self.vectorstore.aadd_texts(
            texts=[content],
            metadatas=[doc_metadata]
        )
    
    async def recall(
        self,
        query: str,
        k: int = 5,
        memory_type: str = None
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant memories via semantic search"""
        
        # Build filter
        filter_dict = {"agent": self.agent_name}
        if memory_type:
            filter_dict["type"] = memory_type
        
        # Semantic search
        results = await self.vectorstore.asimilarity_search_with_score(
            query=query,
            k=k,
            filter=filter_dict
        )
        
        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "relevance_score": float(score)
            }
            for doc, score in results
        ]
    
    def save_to_disk(self, path: str):
        """Persist memory to disk"""
        self.vectorstore.save_local(path)
    
    def load_from_disk(self, path: str):
        """Load memory from disk"""
        self.vectorstore = FAISS.load_local(
            path,
            embeddings=self.embeddings
        )
```

### **Memory Types**

```python
class MemoryType:
    SOLUTION = "solution"         # Problem → Solution pairs
    CONVERSATION = "conversation" # Past conversations
    RESEARCH = "research"         # Research findings
    INSIGHT = "insight"           # Strategic insights
    TOOL_RESULT = "tool_result"   # Tool execution results
    ERROR = "error"               # Errors and fixes
```

### **Integration with Agents**

```python
# agents/strategy_agent.py

class StrategyAgent(dspy.Module):
    def __init__(self):
        super().__init__()
        
        # Add memory
        self.memory = AgentMemory("strategy_agent")
        
        # ... existing code
    
    async def chat_with_josh(self, message: str, user_id: str = "default") -> str:
        # Recall relevant past conversations
        relevant_memories = await self.memory.recall(
            query=message,
            k=3,
            memory_type=MemoryType.CONVERSATION
        )
        
        # Include memories in context
        memory_context = "\n".join([
            f"Past memory ({m['relevance_score']:.2f}): {m['content']}"
            for m in relevant_memories
        ])
        
        # Generate response (with memory context)
        result = self.conversation_module(
            context=f"{system_context}\n\nRelevant memories:\n{memory_context}",
            user_message=message,
            conversation_history=history_text
        )
        
        # Remember this interaction
        await self.memory.remember(
            content=f"Q: {message}\nA: {result.response}",
            memory_type=MemoryType.CONVERSATION,
            metadata={"user_id": user_id}
        )
        
        return result.response
```

### **Use Cases**

1. **Learn from Solutions**: Agent remembers how it solved problems
2. **Recall Context**: Retrieve past conversations about similar topics
3. **Improve Over Time**: Semantic search finds best past approaches
4. **Knowledge Base**: Accumulated wisdom persists across sessions

---

## **🛠️ Part 2: Instrument System**

### **Goal**
Add unlimited tools without bloating system prompts by storing tool descriptions in vector DB.

### **Architecture**

```python
# instruments/instrument_manager.py

from memory.vector_memory import AgentMemory
from typing import List, Dict, Callable
import importlib.util
import inspect

class Instrument:
    """A tool/function that agents can invoke"""
    
    def __init__(
        self,
        name: str,
        description: str,
        function: Callable,
        category: str = "general"
    ):
        self.name = name
        self.description = description
        self.function = function
        self.category = category
        self.signature = inspect.signature(function)
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "parameters": str(self.signature)
        }


class InstrumentManager:
    """Manage tools using vector search instead of system prompt"""
    
    def __init__(self):
        # Use FAISS for instrument storage
        self.memory = AgentMemory("instruments")
        self.instruments: Dict[str, Instrument] = {}
    
    def register_instrument(
        self,
        name: str,
        description: str,
        function: Callable,
        category: str = "general"
    ):
        """Register a new instrument"""
        
        instrument = Instrument(name, description, function, category)
        self.instruments[name] = instrument
        
        # Store in vector DB for semantic search
        await self.memory.remember(
            content=f"{name}: {description}",
            memory_type="instrument",
            metadata={
                "name": name,
                "category": category,
                "signature": str(instrument.signature)
            }
        )
        
        logger.info(f"✅ Registered instrument: {name}")
    
    async def discover_instruments(
        self,
        query: str,
        k: int = 5
    ) -> List[Instrument]:
        """Find relevant instruments via semantic search"""
        
        results = await self.memory.recall(
            query=query,
            k=k,
            memory_type="instrument"
        )
        
        # Return actual instrument objects
        return [
            self.instruments[result["metadata"]["name"]]
            for result in results
            if result["metadata"]["name"] in self.instruments
        ]
    
    def load_instruments_from_directory(self, directory: str):
        """Auto-load instruments from Python files"""
        # Scan directory for .py files
        # Import and register functions marked with @instrument decorator
        pass


# Decorator for easy instrument creation
def instrument(description: str, category: str = "general"):
    """Decorator to mark a function as an instrument"""
    def decorator(func: Callable):
        func._instrument_description = description
        func._instrument_category = category
        return func
    return decorator
```

### **Usage with Agents**

```python
# agents/strategy_agent.py

class StrategyAgent(dspy.Module):
    def __init__(self):
        super().__init__()
        
        # Add instrument manager
        self.instruments = InstrumentManager()
        
        # Register built-in tools
        self._register_instruments()
    
    def _register_instruments(self):
        """Register all available instruments"""
        
        # Data tools
        self.instruments.register_instrument(
            name="audit_lead_flow",
            description="Audit lead flow with real Supabase and GMass data",
            function=self._audit_lead_flow_instrument,
            category="data"
        )
        
        self.instruments.register_instrument(
            name="query_supabase",
            description="Execute SQL query on Supabase database",
            function=self._query_supabase_instrument,
            category="data"
        )
        
        # Research tools
        self.instruments.register_instrument(
            name="research_company",
            description="Deep research on a company using multiple APIs",
            function=self._research_company_instrument,
            category="research"
        )
        
        # ... more instruments
    
    async def _execute_with_instruments(self, query: str) -> str:
        """Execute query using dynamically discovered instruments"""
        
        # Discover relevant instruments
        relevant_tools = await self.instruments.discover_instruments(
            query=query,
            k=3
        )
        
        # Create ReAct module with discovered tools
        react = dspy.ReAct(
            signature=StrategyConversation,
            tools=[tool.function for tool in relevant_tools]
        )
        
        # Execute with discovered tools only
        result = react(
            user_message=query,
            context=f"Available tools: {', '.join(t.name for t in relevant_tools)}"
        )
        
        return result.response
```

### **Benefits**

1. **Unlimited Tools**: Add thousands of tools without prompt bloat
2. **Semantic Discovery**: Agent finds right tools automatically
3. **Dynamic Loading**: Load tools on-demand
4. **Easy Extension**: Just add @instrument decorator
5. **Categorization**: Organize tools by category

---

## **📦 Implementation Order**

### **Session 1: FAISS Memory** (1-2 hours)
1. ✅ Create `memory/vector_memory.py`
2. ✅ Implement `AgentMemory` class
3. ✅ Add memory to StrategyAgent
4. ✅ Test remember/recall functionality

### **Session 2: Instrument System** (1-2 hours)
1. ✅ Create `instruments/instrument_manager.py`
2. ✅ Implement `InstrumentManager` class
3. ✅ Register existing tools as instruments
4. ✅ Test semantic tool discovery

### **Session 3: Integration** (1 hour)
1. ✅ Integrate memory with all agents
2. ✅ Integrate instruments with ReAct
3. ✅ Add persistence (save/load)
4. ✅ Update documentation

### **Session 4: Testing** (1 hour)
1. ✅ Test memory across sessions
2. ✅ Test instrument discovery
3. ✅ Verify performance
4. ✅ Deploy to production

---

## **🧪 Testing Plan**

### **Memory Tests**
```python
# Test 1: Remember and recall
agent.memory.remember("How to fix GMass auth: Refresh token before API calls")
results = agent.memory.recall("GMass authentication issues")
assert len(results) > 0
assert "token" in results[0]["content"].lower()

# Test 2: Relevance scoring
agent.memory.remember("Best time to send emails: 9 AM Tuesday")
agent.memory.remember("Coffee tastes best at 9 AM")
results = agent.memory.recall("email sending strategy", k=1)
assert "email" in results[0]["content"].lower()

# Test 3: Persistence
agent.memory.save_to_disk("./memory/strategy_agent")
new_agent = StrategyAgent()
new_agent.memory.load_from_disk("./memory/strategy_agent")
results = new_agent.memory.recall("email", k=1)
assert len(results) > 0
```

### **Instrument Tests**
```python
# Test 1: Register and discover
instruments.register_instrument(
    "calculate_roi",
    "Calculate ROI for marketing campaigns",
    calculate_roi_function
)
tools = instruments.discover_instruments("How's our marketing performing?", k=3)
assert any(t.name == "calculate_roi" for t in tools)

# Test 2: Semantic matching
tools = instruments.discover_instruments("audit database", k=5)
assert any("database" in t.description.lower() for t in tools)
```

---

## **📊 Success Criteria**

### **Memory**
- ✅ Agents can store memories
- ✅ Agents can retrieve relevant memories
- ✅ Memories persist across restarts
- ✅ Semantic search works accurately
- ✅ No performance degradation

### **Instruments**
- ✅ Can register new tools easily
- ✅ Semantic discovery works
- ✅ ReAct uses discovered tools
- ✅ System prompt stays small
- ✅ Tool execution works correctly

---

## **🎯 Expected Outcomes**

After Phase 0.5:
1. **Smarter Agents**: Learn from every interaction
2. **Scalable Tools**: Add unlimited instruments
3. **Better Responses**: Context from past experiences
4. **Self-Improvement**: Agents get better over time
5. **Foundation for Phase 1**: Ready for advanced features

---

**Let's build it!** 🚀

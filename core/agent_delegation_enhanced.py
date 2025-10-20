"""
Agent Delegation Framework - Enhanced with Agent Zero Patterns

Phase 1.5 Enhancements:
1. Dynamic MCP tool loading per subordinate profile
2. Subordinate-specific DSPy modules (ChainOfThought/ReAct)
3. FAISS memory integration per subordinate
4. Iterative refinement (subordinate ↔ superior communication)

Based on Agent Zero's call_subordinate pattern + our production infrastructure.
"""

import logging
import json
from typing import Dict, Any, Optional, List, Callable, TYPE_CHECKING
import asyncio
import dspy

if TYPE_CHECKING:
    from agents.strategy_agent import StrategyAgent

logger = logging.getLogger(__name__)


# ===== Profile → Tool Mapping =====

PROFILE_TOOL_MAP = {
    "document_analyst": [
        "google_drive_list_files",
        "google_sheets_get_rows",
        "google_docs_get_content",
        "google_drive_search",
        "perplexity_research"
    ],
    "competitor_analyst": [
        "perplexity_research",
        "apify_scrape_website",
        "google_search"
    ],
    "market_researcher": [
        "perplexity_research",
        "google_search",
        "query_supabase"
    ],
    "account_researcher": [
        "perplexity_research",
        "apify_scrape_website",
        "query_supabase",
        "google_search"
    ],
    "campaign_analyst": [
        "query_supabase",
        "get_pipeline_stats",
        "audit_lead_flow"
    ],
    "content_strategist": [
        "perplexity_research",
        "google_docs_get_content",
        "google_sheets_get_rows"
    ]
}


# ===== DSPy Signature for Subordinates =====

class SubordinateSignature(dspy.Signature):
    """Base signature for all subordinate agents with Agent Zero-style reasoning"""
    
    context: str = dspy.InputField(desc="Your role, instructions, and relevant memories")
    task: str = dspy.InputField(desc="Specific task from your superior agent")
    
    # Agent Zero pattern: Explicit "thoughts" field for transparency
    thoughts: str = dspy.OutputField(desc="Your chain-of-thought reasoning process")
    result: str = dspy.OutputField(desc="Task completion result or response")


# ===== Enhanced Subordinate Agent =====

class SubordinateAgent:
    """
    Enhanced subordinate agent with Agent Zero patterns.
    
    Enhancements over base version:
    - Dynamic MCP tool loading based on profile
    - Own DSPy ChainOfThought/ReAct modules
    - FAISS memory integration
    - Can ask superior for clarification
    - Stores learnings for future tasks
    """
    
    def __init__(
        self,
        profile: str,
        superior_agent: Any,
        specialized_instructions: str
    ):
        """
        Initialize enhanced subordinate agent.
        
        Args:
            profile: Role/specialization (e.g., "document_analyst")
            superior_agent: Parent agent that spawned this subordinate
            specialized_instructions: Role-specific instructions
        """
        self.profile = profile
        self.superior = superior_agent
        self.specialized_instructions = specialized_instructions
        self.conversation_history: List[Dict[str, str]] = []
        self.data: Dict[str, Any] = {}
        
        # Metadata
        self.data["_superior"] = superior_agent
        self.data["_profile"] = profile
        self.data["_created_at"] = asyncio.get_event_loop().time()
        
        logger.info(f"👶 Creating enhanced subordinate: {profile}")
        
        # === ENHANCEMENT 1: Dynamic Tool Loading ===
        self.tools = self._load_tools()
        logger.info(f"   Tools loaded: {len(self.tools)} ({', '.join([t.__name__ for t in self.tools][:3])}...)")
        
        # === ENHANCEMENT 2: Subordinate-Specific DSPy Modules ===
        self.chain_of_thought = dspy.ChainOfThought(SubordinateSignature)
        
        if self.tools:
            self.react_agent = dspy.ReAct(SubordinateSignature, tools=self.tools)
            logger.info(f"   Mode: ReAct (with {len(self.tools)} tools)")
        else:
            self.react_agent = None
            logger.info(f"   Mode: ChainOfThought (no tools)")
        
        # === ENHANCEMENT 3: Memory Integration ===
        self.memory = self._init_memory()
        if self.memory:
            logger.info(f"   Memory: FAISS enabled (namespace: {self._get_memory_namespace()})")
        
        logger.info(f"✅ Enhanced subordinate {profile} ready")
    
    def _get_memory_namespace(self) -> str:
        """Get namespaced memory key for this subordinate"""
        superior_name = self.superior.__class__.__name__
        return f"{superior_name}.{self.profile}"
    
    def _init_memory(self):
        """Initialize FAISS memory for this subordinate"""
        try:
            from memory.vector_memory import get_agent_memory
            return get_agent_memory(self._get_memory_namespace())
        except Exception as e:
            logger.warning(f"   Memory initialization failed: {e}")
            return None
    
    def _load_tools(self) -> List[Callable]:
        """
        Load MCP tools for this subordinate based on profile.
        
        Uses PROFILE_TOOL_MAP to determine which tools this profile needs.
        """
        tools = []
        
        tool_names = PROFILE_TOOL_MAP.get(self.profile, [])
        if not tool_names:
            return tools
        
        # Get MCP client from superior
        mcp = getattr(self.superior, 'mcp_client', None)
        if not mcp:
            logger.warning(f"   No MCP client available for tool loading")
            return tools
        
        # Helper for async execution in sync context
        def run_async(coro):
            """Run async coroutine in new thread with event loop"""
            import concurrent.futures
            import threading
            
            result = [None]
            exception = [None]
            
            def _run():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    result[0] = loop.run_until_complete(coro)
                    loop.close()
                except Exception as e:
                    exception[0] = e
            
            thread = threading.Thread(target=_run)
            thread.start()
            thread.join()
            
            if exception[0]:
                raise exception[0]
            
            return result[0]
        
        # Create tool functions for each MCP tool
        for tool_name in tool_names:
            try:
                # Create a closure to capture tool_name
                def make_tool(name):
                    def tool_func(**kwargs) -> str:
                        """Dynamically created MCP tool wrapper"""
                        try:
                            result = run_async(
                                mcp.call_tool(name, kwargs)
                            )
                            return json.dumps(result) if result else json.dumps({"error": "No result"})
                        except Exception as e:
                            logger.error(f"Tool {name} failed: {e}")
                            return json.dumps({"error": str(e), "tool": name})
                    
                    # Set function name for DSPy
                    tool_func.__name__ = name
                    tool_func.__doc__ = f"MCP tool: {name}"
                    return tool_func
                
                tool = make_tool(tool_name)
                tools.append(tool)
                
            except Exception as e:
                logger.warning(f"   Failed to load tool {tool_name}: {e}")
        
        return tools
    
    def set_data(self, key: str, value: Any):
        """Store data in subordinate's local memory"""
        self.data[key] = value
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """Retrieve data from subordinate's local memory"""
        return self.data.get(key, default)
    
    async def ask_superior(self, question: str) -> str:
        """
        === ENHANCEMENT 4: Subordinate can ask superior for clarification ===
        
        This enables Agent Zero-style iterative refinement.
        Subordinate can ask questions when uncertain.
        """
        logger.info(f"❓ Subordinate {self.profile} asking superior: {question[:80]}...")
        
        try:
            # Use inter-agent communication system
            from core.agent_communication import ask_agent_static
            
            response = await ask_agent_static(
                from_agent=self,
                to_agent=self.superior,
                question=question,
                context=f"Subordinate {self.profile} needs clarification"
            )
            
            logger.info(f"✅ Superior responded to {self.profile}")
            return response
            
        except Exception as e:
            logger.error(f"❌ Failed to ask superior: {e}")
            return f"Unable to reach superior: {str(e)}"
    
    async def process(self, message: str) -> str:
        """
        Process task using Agent Zero patterns:
        1. Retrieve relevant memories
        2. Execute with tools (ReAct) or reasoning (ChainOfThought)
        3. Store learnings in memory
        4. Return result
        
        Args:
            message: Task from superior
            
        Returns:
            Task result
        """
        logger.info(f"🧠 {self.profile} processing: {message[:80]}...")
        
        # === STEP 1: Build context with memories ===
        context = self.specialized_instructions
        
        # Retrieve relevant past learnings from FAISS
        if self.memory:
            try:
                memories = self.memory.search(message, k=3)
                if memories:
                    memory_text = "\n\n**Past Learnings:**\n" + "\n".join([
                        f"- {mem}" for mem in memories
                    ])
                    context += memory_text
                    logger.info(f"   Retrieved {len(memories)} relevant memories")
            except Exception as e:
                logger.warning(f"   Memory retrieval failed: {e}")
        
        # Add conversation history
        if self.conversation_history:
            history_text = "\n\n**Previous Conversation:**\n" + "\n".join([
                f"{msg['role']}: {msg['content'][:100]}" 
                for msg in self.conversation_history[-3:]
            ])
            context += history_text
        
        # === STEP 2: Execute with appropriate DSPy module ===
        try:
            # Use ReAct if tools available, else ChainOfThought
            if self.tools and self.react_agent:
                logger.info(f"   Mode: ReAct with {len(self.tools)} tools")
                output = await asyncio.to_thread(
                    self.react_agent,
                    context=context,
                    task=message
                )
            else:
                logger.info(f"   Mode: ChainOfThought (reasoning only)")
                output = await asyncio.to_thread(
                    self.chain_of_thought,
                    context=context,
                    task=message
                )
            
            # Extract thoughts and result (Agent Zero transparency pattern)
            thoughts = getattr(output, 'thoughts', 'No thoughts recorded')
            result = getattr(output, 'result', str(output))
            
            # Log thoughts for transparency (Agent Zero pattern)
            logger.info(f"💭 {self.profile} thoughts: {thoughts[:150]}...")
            logger.info(f"✅ {self.profile} result: {result[:150]}...")
            
            # === STEP 3: Store learning in memory ===
            if self.memory:
                try:
                    learning = f"Task: {message}\nThoughts: {thoughts}\nResult: {result}"
                    self.memory.add(learning)
                    logger.info(f"   Stored learning in memory")
                except Exception as e:
                    logger.warning(f"   Failed to store memory: {e}")
            
            # === STEP 4: Update conversation history ===
            self.conversation_history.append({
                "role": "superior",
                "content": message
            })
            self.conversation_history.append({
                "role": "subordinate",
                "content": result,
                "thoughts": thoughts
            })
            
            return result
            
        except Exception as e:
            logger.error(f"❌ {self.profile} processing failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return f"Processing error: {str(e)}"


# ===== Enhanced Delegation Manager =====

class AgentDelegation:
    """
    Enhanced delegation manager with Agent Zero patterns.
    
    Manages subordinate agents with:
    - Dynamic tool loading
    - Memory persistence
    - Iterative refinement
    """
    
    def __init__(self, parent_agent: Any):
        """Initialize enhanced delegation manager"""
        self.parent_agent = parent_agent
        self.subordinates: Dict[str, SubordinateAgent] = {}
        
        # Enhanced profile templates with document_analyst
        self.profile_templates = {
            "document_analyst": """
You are a document analysis and organization specialist.

**Your Expertise:**
- Auditing large document repositories (Google Drive, Dropbox, etc.)
- Extracting structured data from spreadsheets
- Analyzing document content for key information
- Identifying patterns, relationships, and insights
- Organizing findings into clear, actionable reports

**Your Approach:**
1. **Inventory**: List all documents systematically
2. **Categorize**: Group by type, purpose, or topic
3. **Analyze**: Extract key data and insights from each
4. **Synthesize**: Identify patterns and relationships
5. **Report**: Provide organized, actionable findings

**Available Tools:**
- google_drive_list_files: List files and folders in Drive
- google_sheets_get_rows: Read spreadsheet data
- google_docs_get_content: Read document text
- google_drive_search: Search for specific files
- perplexity_research: Research unfamiliar concepts

**Remember:**
- Be thorough but efficient
- Organize information clearly by category
- Highlight actionable insights and patterns
- If document purpose is unclear, ask superior for clarification
- Store learnings in memory for faster future audits
            """,
            
            "competitor_analyst": """
You are a competitive intelligence analyst.

**Your Job:** Deeply research specific competitors
- Products and pricing strategies
- Market positioning and messaging
- Strengths and weaknesses
- Customer segments and targeting
- Marketing and sales strategies

**Tools:** Perplexity research, web scraping, Google search
**Approach:** Be thorough, cite sources, identify competitive advantages
            """,
            
            "market_researcher": """
You are a market research specialist.

**Your Job:** Analyze markets and industry trends
- Market size, growth, and dynamics
- Key players and competitive landscape
- Customer segments and needs
- Opportunities and threats
- Industry trends and future outlook

**Tools:** Perplexity, Google search, Supabase queries
**Approach:** Provide data-driven insights with sources
            """,
            
            "account_researcher": """
You are an account-based marketing (ABM) researcher.

**Your Job:** Deep dive on specific target accounts
- Company profile, history, and culture
- Decision makers and organizational structure
- Technology stack and tools used
- Pain points, needs, and challenges
- Recent news, events, and initiatives

**Tools:** Perplexity, web scraping, Supabase, Google search
**Approach:** Build comprehensive account profiles for personalized outreach
            """,
            
            "content_strategist": """
You are a content marketing strategist.

**Your Job:** Plan and optimize content strategy
- Audience analysis and segmentation
- Content ideation and planning
- Channel strategy and distribution
- Messaging frameworks and positioning
- Performance optimization recommendations

**Tools:** Perplexity, Google Docs, Google Sheets
**Approach:** Focus on personalized, high-converting content
            """,
            
            "campaign_analyst": """
You are a marketing campaign analyst.

**Your Job:** Analyze campaign performance and optimize
- Metrics, KPIs, and conversion data
- A/B test results and statistical significance
- Conversion funnel analysis
- ROI calculation and cost analysis
- Optimization recommendations

**Tools:** Supabase queries, pipeline stats, audit tools
**Approach:** Use real data to provide actionable insights
            """
        }
    
    async def call_subordinate(
        self,
        profile: str,
        message: str,
        reset: bool = False
    ) -> str:
        """
        Delegate task to specialized subordinate (Agent Zero pattern).
        
        Creates or reuses subordinate with:
        - Profile-specific tools
        - Own DSPy reasoning modules
        - Memory persistence
        
        Args:
            profile: Subordinate role (e.g., "document_analyst")
            message: Task for subordinate
            reset: Create fresh subordinate (clear history)
            
        Returns:
            Task result from subordinate
        """
        logger.info(f"🎯 Delegating to subordinate: {profile}")
        logger.info(f"   Task: {message[:100]}...")
        
        # Create or reuse subordinate
        if profile not in self.subordinates or reset:
            instructions = self.profile_templates.get(
                profile,
                f"You are a specialized {profile} subordinate agent."
            )
            
            subordinate = SubordinateAgent(
                profile=profile,
                superior_agent=self.parent_agent,
                specialized_instructions=instructions
            )
            
            self.subordinates[profile] = subordinate
            
            if reset:
                logger.info(f"🔄 Reset subordinate: {profile}")
            else:
                logger.info(f"👶 Created new subordinate: {profile}")
        
        subordinate = self.subordinates[profile]
        
        # Delegate task
        try:
            result = await subordinate.process(message)
            logger.info(f"✅ Subordinate {profile} completed task")
            return result
            
        except Exception as e:
            logger.error(f"❌ Subordinate {profile} failed: {e}")
            return f"Delegation failed: {str(e)}"
    
    async def refine_subordinate_work(
        self,
        profile: str,
        feedback: str
    ) -> str:
        """
        === ENHANCEMENT 4: Iterative Refinement ===
        
        Give feedback to subordinate for work refinement (Agent Zero pattern).
        
        Args:
            profile: Subordinate to refine
            feedback: Feedback or clarification
            
        Returns:
            Refined result
        """
        logger.info(f"🔄 Refining {profile} work with feedback")
        
        subordinate = self.subordinates.get(profile)
        if not subordinate:
            return f"Subordinate {profile} not found. Create it first with call_subordinate."
        
        refinement_task = f"Based on superior's feedback, refine your previous work:\n\n{feedback}"
        
        return await subordinate.process(refinement_task)
    
    def get_subordinate(self, profile: str) -> Optional[SubordinateAgent]:
        """Get subordinate by profile"""
        return self.subordinates.get(profile)
    
    def list_subordinates(self) -> List[str]:
        """List all active subordinates"""
        return list(self.subordinates.keys())
    
    def remove_subordinate(self, profile: str):
        """Remove subordinate (cleanup)"""
        if profile in self.subordinates:
            del self.subordinates[profile]
            logger.info(f"🗑️ Removed subordinate: {profile}")
    
    def clear_all_subordinates(self):
        """Clear all subordinates (cleanup)"""
        count = len(self.subordinates)
        self.subordinates.clear()
        logger.info(f"🗑️ Cleared {count} subordinates")


# ===== Convenience Functions =====

def enable_delegation(agent: Any) -> AgentDelegation:
    """
    Enable enhanced delegation for an agent.
    
    Usage in agent __init__:
        from core.agent_delegation_enhanced import enable_delegation
        self.delegation = enable_delegation(self)
    
    Then use:
        result = await self.delegation.call_subordinate("document_analyst", "Audit my Drive")
    """
    return AgentDelegation(agent)

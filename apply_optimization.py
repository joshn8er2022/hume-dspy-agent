
import re
import sys

print("🔧 PHOENIX OPTIMIZATION SCRIPT")
print("="*80)

# Read backup file
with open('agents/strategy_agent.py.backup_pre_optimization', 'r') as f:
    content = f.read()

original_size = len(content)
print(f"📖 Read backup: {original_size} bytes\n")

# ============================================================================
# STEP 1: Add imports after complete import section
# ============================================================================

lines = content.split('\n')
import_end_idx = 0

for i, line in enumerate(lines):
    stripped = line.strip()
    if not stripped or stripped.startswith('#'):
        continue
    if (stripped.startswith('from ') or stripped.startswith('import ') or 
        stripped.endswith('(') or stripped.endswith(',') or stripped.startswith(')')):
        import_end_idx = i
    elif import_end_idx > 0:
        break

import_additions = """from core.model_selector import get_model_selector
from core.message_classifier import classify_message, needs_full_context, needs_pipeline_data
from core.context_builder import build_context"""

lines.insert(import_end_idx + 1, import_additions)
content = '\n'.join(lines)
print(f"✅ Step 1: Added imports after line {import_end_idx + 1}")

# ============================================================================
# STEP 2: Replace Sonnet configuration with dual-model
# ============================================================================

content = content.replace(
    '                strategy_lm = dspy.LM(',
    """                # Initialize model selector
                self.model_selector = get_model_selector()

                # Haiku for simple (12x cheaper)
                haiku_lm = dspy.LM(
                    model="openrouter/anthropic/claude-haiku-4.5",
                    api_key=openrouter_key,
                    max_tokens=2000,
                    temperature=0.7
                )

                # Sonnet for complex
                sonnet_lm = dspy.LM("""
)

content = content.replace(
    '                dspy.configure(lm=strategy_lm)',
    """                dspy.configure(lm=haiku_lm)
                self.haiku_lm = haiku_lm
                self.sonnet_lm = sonnet_lm"""
)

print("✅ Step 2: Dual-model configuration")

# ============================================================================
# STEP 3: Update module initialization
# ============================================================================

old_init = """                # Initialize DSPy modules with Sonnet 4.5
                # IMPORTANT: Use Predict for simple queries (fast), ChainOfThought for complex (reasoning)
                self.simple_conversation = dspy.Predict(StrategyConversation)  # No reasoning
                self.complex_conversation = dspy.ChainOfThought(StrategyConversation)  # With reasoning
                self.pipeline_analyzer = dspy.ChainOfThought(PipelineAnalysisSignature)
                self.recommendation_generator = dspy.ChainOfThought(GenerateRecommendations)
                self.quick_status = dspy.Predict(QuickPipelineStatus)  # Status check is simple

                # Initialize ReAct for tool calling (action queries)
                self.tools = self._init_tools()
                self.action_agent = dspy.ReAct(StrategyConversation, tools=self.tools)"""

new_init = """                # Initialize modules with appropriate models
                self.simple_conversation = dspy.Predict(StrategyConversation)
                self.quick_status = dspy.Predict(QuickPipelineStatus)
                self.tools = self._init_tools()

                with dspy.context(lm=sonnet_lm):
                    self.complex_conversation = dspy.ChainOfThought(StrategyConversation)
                    self.pipeline_analyzer = dspy.ChainOfThought(PipelineAnalysisSignature)
                    self.recommendation_generator = dspy.ChainOfThought(GenerateRecommendations)
                    self.action_agent = dspy.ReAct(StrategyConversation, tools=self.tools)"""

content = content.replace(old_init, new_init)
print("✅ Step 3: Module initialization")

# Save
with open('agents/strategy_agent.py', 'w') as f:
    f.write(content)

print(f"\n💾 Saved: {len(content)} bytes")
print(f"   Change: {len(content) - original_size:+d} bytes")
print("\n✅ OPTIMIZATION COMPLETE!")

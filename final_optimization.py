import re

print("🔧 FINAL PHOENIX OPTIMIZATION")
print("="*80 + "\n")

# Read backup
with open('agents/strategy_agent.py.backup_pre_optimization', 'r') as f:
    content = f.read()

original_size = len(content)
print(f"📖 Backup: {original_size} bytes\n")

# Step 1: Add imports (find the logger import and add after it)
import_marker = 'logger = logging.getLogger(__name__)'
if import_marker in content:
    pos = content.find(import_marker) + len(import_marker)
    imports = '''\n\n# Phoenix optimization imports
from core.model_selector import get_model_selector
from core.message_classifier import classify_message
from core.context_builder import build_context
'''
    content = content[:pos] + imports + content[pos:]
    print("✅ Step 1: Added imports")

# Step 2: Replace Sonnet config
content = content.replace(
    '                strategy_lm = dspy.LM(',
    '''                self.model_selector = get_model_selector()
                haiku_lm = dspy.LM(
                    model="openrouter/anthropic/claude-haiku-4.5",
                    api_key=openrouter_key,
                    max_tokens=2000,
                    temperature=0.7
                )
                sonnet_lm = dspy.LM('''
)

content = content.replace(
    '                dspy.configure(lm=strategy_lm)',
    '''                dspy.configure(lm=haiku_lm)
                self.haiku_lm = haiku_lm
                self.sonnet_lm = sonnet_lm'''
)

print("✅ Step 2: Dual-model config")

# Step 3: Add context manager for complex modules
content = content.replace(
    '''                self.tools = self._init_tools()
                self.action_agent = dspy.ReAct(StrategyConversation, tools=self.tools)''',
    '''                self.tools = self._init_tools()
                
                with dspy.context(lm=sonnet_lm):
                    self.action_agent = dspy.ReAct(StrategyConversation, tools=self.tools)'''
)

print("✅ Step 3: Added context manager")

# Save
with open('agents/strategy_agent.py', 'w') as f:
    f.write(content)

print(f"\n💾 Saved: {len(content)} bytes")
print(f"   Change: {len(content) - original_size:+d} bytes")
print("\n✅ DONE!")

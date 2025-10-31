#!/bin/bash
#
# Run Bug Fix Verification Tests
#
# This script runs the comprehensive test suite for Strategy Agent bug fixes:
# 1. analyze_pipeline returns REAL data (not mock)
# 2. recommend_targets returns REAL companies (not fake)
#

echo "========================================"
echo "Strategy Agent Bug Fix Verification"
echo "========================================"
echo ""

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo "Error: Must run from project root (hume-dspy-agent)"
    exit 1
fi

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "Installing pytest..."
    pip install pytest pytest-asyncio
fi

# Run the tests
echo "Running bug fix verification tests..."
echo ""

pytest tests/test_strategy_agent_fixes.py -v --tb=short

# Capture exit code
EXIT_CODE=$?

echo ""
echo "========================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ ALL TESTS PASSED"
    echo "Both bugs are fixed and verified!"
else
    echo "❌ TESTS FAILED"
    echo "One or more bugs may have regressed."
fi
echo "========================================"

exit $EXIT_CODE

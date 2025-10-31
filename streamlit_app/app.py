"""
Hume DSPy Agent - Internal Admin Dashboard

Streamlit-based admin interface for:
- Agent status monitoring
- Pipeline metrics
- Manual lead qualification
- Campaign management
- GEPA optimization controls
- Permission approval
"""

import streamlit as st
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(
    page_title="Hume DSPy Agent Admin",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sidebar navigation
st.sidebar.title("🧠 Hume DSPy Agent")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Dashboard",
        "📊 Pipeline Metrics",
        "👥 Lead Management",
        "📧 Campaign Management",
        "🔧 GEPA Optimization",
        "✅ Permission Approval",
        "🤖 Agent Status"
    ]
)

st.sidebar.markdown("---")
st.sidebar.markdown("### System Status")
st.sidebar.success("✅ All agents operational")
st.sidebar.info("📊 76% test pass rate")
st.sidebar.warning("⚠️ AccountOrchestrator needs refactor")

# Main content
if page == "🏠 Dashboard":
    st.title("🏠 Hume DSPy Agent Dashboard")
    st.markdown("### Welcome to the Internal Admin Interface")
    
    # Quick stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Leads", "68", "+5 today")
    
    with col2:
        st.metric("Qualification Rate", "8.3%", "-2.1%")
    
    with col3:
        st.metric("Active Campaigns", "12", "+3")
    
    with col4:
        st.metric("Agent Compliance", "66%", "+4%")
    
    st.markdown("---")
    
    # Recent activity
    st.subheader("📋 Recent Activity")
    st.info("✅ FollowUpAgent DSPy integration complete (90% compliance)")
    st.success("✅ PostgreSQL Supabase connection fixed")
    st.warning("⚠️ AccountOrchestrator needs refactor (40% compliance)")
    
    # Agent status
    st.markdown("---")
    st.subheader("🤖 Agent Status")
    
    agents = [
        {"name": "FollowUpAgent", "status": "✅ Operational", "compliance": 90},
        {"name": "StrategyAgent", "status": "✅ Operational", "compliance": 80},
        {"name": "ResearchAgent", "status": "✅ Operational", "compliance": 80},
        {"name": "InboundAgent", "status": "✅ Operational", "compliance": 70},
        {"name": "AuditAgent", "status": "✅ Operational", "compliance": 60},
        {"name": "Introspection", "status": "⚠️ Needs async", "compliance": 40},
        {"name": "AccountOrchestrator", "status": "⚠️ Needs refactor", "compliance": 40}
    ]
    
    for agent in agents:
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            st.write(f"**{agent['name']}**")
        with col2:
            st.write(agent['status'])
        with col3:
            st.progress(agent['compliance'] / 100)

elif page == "📊 Pipeline Metrics":
    st.title("📊 Pipeline Metrics")
    st.info("Pipeline metrics visualization coming soon...")

elif page == "👥 Lead Management":
    st.title("👥 Lead Management")
    st.info("Lead management interface coming soon...")

elif page == "📧 Campaign Management":
    st.title("📧 Campaign Management")
    st.info("Campaign management interface coming soon...")

elif page == "🔧 GEPA Optimization":
    st.title("🔧 GEPA Optimization Controls")
    st.info("GEPA optimization controls coming soon...")

elif page == "✅ Permission Approval":
    st.title("✅ Permission Approval")
    st.info("Permission approval interface coming soon...")

elif page == "🤖 Agent Status":
    st.title("🤖 Agent Status")
    st.info("Detailed agent status coming soon...")

st.sidebar.markdown("---")
st.sidebar.caption(f"Last updated: Oct 25, 2025, 3:40 AM MT")

-- Create agent_state table for tracking agent execution state
-- This table stores the internal state and results from each agent execution

CREATE TABLE IF NOT EXISTS agent_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name TEXT NOT NULL,
    lead_id TEXT NOT NULL,
    state_data JSONB DEFAULT '{}'::jsonb,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index on lead_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_agent_state_lead_id ON agent_state(lead_id);

-- Create index on agent_name for filtering by agent type
CREATE INDEX IF NOT EXISTS idx_agent_state_agent_name ON agent_state(agent_name);

-- Create index on created_at for time-based queries
CREATE INDEX IF NOT EXISTS idx_agent_state_created_at ON agent_state(created_at DESC);

-- Enable Row Level Security
ALTER TABLE agent_state ENABLE ROW LEVEL SECURITY;

-- Create policy to allow service role full access
CREATE POLICY "Service role can do everything" ON agent_state
    FOR ALL
    USING (true)
    WITH CHECK (true);

COMMENT ON TABLE agent_state IS 'Stores agent execution state and results for debugging and auditing';
COMMENT ON COLUMN agent_state.agent_name IS 'Name of the agent (InboundAgent, StrategyAgent, etc.)';
COMMENT ON COLUMN agent_state.lead_id IS 'ID of the lead this state is associated with';
COMMENT ON COLUMN agent_state.state_data IS 'JSON data containing agent-specific state (qualification results, reasoning, etc.)';
COMMENT ON COLUMN agent_state.status IS 'Status of the agent execution (pending, in_progress, completed, failed)';

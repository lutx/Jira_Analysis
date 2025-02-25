-- Add jira_id column if it doesn't exist
CREATE TABLE IF NOT EXISTS projects_new (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    jira_key VARCHAR(10) UNIQUE,
    jira_id VARCHAR(100) UNIQUE,
    status VARCHAR(20) DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_sync DATETIME,
    portfolio_id INTEGER REFERENCES portfolios(id)
);

-- Copy data from old table
INSERT INTO projects_new 
SELECT 
    id,
    name,
    description,
    jira_key,
    jira_id,
    status,
    created_at,
    updated_at,
    last_sync,
    portfolio_id
FROM projects;

-- Drop old table
DROP TABLE projects;

-- Rename new table
ALTER TABLE projects_new RENAME TO projects; 
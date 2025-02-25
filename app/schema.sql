DROP TABLE IF EXISTS user_roles;
DROP TABLE IF EXISTS leave_requests;
DROP TABLE IF EXISTS portfolio_projects;
DROP TABLE IF EXISTS project_assignments;
DROP TABLE IF EXISTS user_availability;
DROP TABLE IF EXISTS worklogs;
DROP TABLE IF EXISTS portfolios;
DROP TABLE IF EXISTS roles;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS sync_history;
DROP TABLE IF EXISTS projects;
DROP TABLE IF EXISTS settings;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_name TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    display_name TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    permissions TEXT,
    is_system BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_roles (
    user_name TEXT NOT NULL,
    role_id INTEGER NOT NULL,
    assigned_by TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_name) REFERENCES users (user_name),
    FOREIGN KEY (role_id) REFERENCES roles (id),
    PRIMARY KEY (user_name, role_id)
);

CREATE TABLE IF NOT EXISTS portfolios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    client_name TEXT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    FOREIGN KEY (created_by) REFERENCES users(user_name)
);

CREATE TABLE IF NOT EXISTS portfolio_projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id INTEGER NOT NULL,
    project_key TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assigned_by TEXT NOT NULL,
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id),
    FOREIGN KEY (assigned_by) REFERENCES users(user_name),
    UNIQUE(portfolio_id, project_key)
);

CREATE TABLE worklogs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_name TEXT NOT NULL,
    project_key TEXT NOT NULL,
    issue_key TEXT NOT NULL,
    time_spent REAL NOT NULL,
    work_date DATE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_name) REFERENCES users (user_name)
);

CREATE TABLE IF NOT EXISTS project_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_name TEXT NOT NULL,
    project_key TEXT NOT NULL,
    role_id INTEGER,
    planned_hours REAL NOT NULL,
    month_year TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_name) REFERENCES users (user_name),
    FOREIGN KEY (project_key) REFERENCES portfolio_projects (project_key),
    FOREIGN KEY (role_id) REFERENCES roles (id)
);

CREATE TABLE IF NOT EXISTS leave_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    leave_type TEXT NOT NULL CHECK(leave_type IN ('vacation', 'sick', 'other')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected')),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_by INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (approved_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS user_availability (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_name TEXT NOT NULL,
    month_year TEXT NOT NULL,
    working_days INTEGER NOT NULL,
    holidays INTEGER NOT NULL,
    leave_days INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_name) REFERENCES users (user_name),
    UNIQUE(user_name, month_year)
);

CREATE TABLE IF NOT EXISTS sync_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_type TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('success', 'error', 'in_progress')),
    details TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TABLE projects (
    key TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_worklogs_user_name ON worklogs(user_name);
CREATE INDEX IF NOT EXISTS idx_worklogs_project_key ON worklogs(project_key);
CREATE INDEX IF NOT EXISTS idx_worklogs_work_date ON worklogs(work_date);
CREATE INDEX IF NOT EXISTS idx_portfolio_projects_project_key ON portfolio_projects(project_key);
CREATE INDEX IF NOT EXISTS idx_leave_requests_user_id ON leave_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_leave_requests_status ON leave_requests(status);
CREATE INDEX IF NOT EXISTS idx_user_roles_role_id ON user_roles(role_id);
CREATE INDEX IF NOT EXISTS idx_project_assignments_user_name ON project_assignments(user_name);
CREATE INDEX IF NOT EXISTS idx_project_assignments_project_key ON project_assignments(project_key);
CREATE INDEX IF NOT EXISTS idx_user_availability_user_name ON user_availability(user_name);

CREATE TRIGGER users_updated_at 
AFTER UPDATE ON users
BEGIN
    UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER roles_updated_at 
AFTER UPDATE ON roles
BEGIN
    UPDATE roles SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER portfolios_updated_at 
AFTER UPDATE ON portfolios
BEGIN
    UPDATE portfolios SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER leave_requests_updated_at 
AFTER UPDATE ON leave_requests
BEGIN
    UPDATE leave_requests SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER user_availability_updated_at 
AFTER UPDATE ON user_availability
BEGIN
    UPDATE user_availability SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER worklogs_updated_at 
AFTER UPDATE ON worklogs
BEGIN
    UPDATE worklogs SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER projects_updated_at 
AFTER UPDATE ON projects
BEGIN
    UPDATE projects SET updated_at = CURRENT_TIMESTAMP WHERE key = NEW.key;
END;

INSERT INTO roles (name, description, permissions, is_system) VALUES 
('superadmin', 'Super Administrator', '["all"]', 1),
('admin', 'Administrator', '["admin"]', 1),
('user', 'Regular user', '["read"]', 1);

INSERT OR IGNORE INTO users (user_name, email, password_hash, display_name, is_active) 
VALUES (
    'luszynski@lbpro.pl',
    'luszynski@lbpro.pl',
    'pbkdf2:sha256:600000$s4Vaop4JR5zmj0Gs$3892f4311419218124bf5b09bfcc4a1873e72392c6e5ec729de1cb874b60d4e4',
    'Super Administrator',
    1
);

INSERT OR IGNORE INTO user_roles (user_name, role_id, assigned_by)
SELECT 
    'luszynski@lbpro.pl',
    (SELECT id FROM roles WHERE name = 'superadmin'),
    'system';

UPDATE portfolios SET is_active = 1 WHERE is_active IS NULL;

CREATE TABLE IF NOT EXISTS portfolio_projects (
    portfolio_id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (portfolio_id, project_id),
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
); 
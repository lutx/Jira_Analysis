# **Product Requirements Document (PRD)**

## **Jira Analysis Application**

### **1. Overview**
The Jira Analysis Application is a comprehensive tool designed to analyze and manage worklog data from Jira, incorporating portfolio management, user role assignments, and advanced analytics. The application enables tracking worklogs per role, planned vs. actual work analysis, and managing project allocations for clients.

### **2. Objectives**
- Provide detailed insights into worklogs recorded in Jira.
- Enable role-based and project-based analysis of user activity.
- Allow creation and management of client portfolios, mapping existing Jira projects to a portfolio.
- Enable monthly assignment planning of users to projects within a client portfolio.
- Support tracking and comparison of planned vs. actual logged hours per user and project.
- Offer exportable reports for stakeholders.
- Facilitate easy management and tracking of changes via a superadmin panel.

---

### **3. Functional Requirements**

#### **3.1 Backend Functionality**
- **API Integration**
  - Pull worklog data from Jira, including task IDs and timestamps.
  - Fetch project and user details from Jira.
  - Manual import of Jira users by the superadmin/admin before they can be assigned a role in the application.

- **Database Schema (SQLite)**
  - `worklogs`: Store user worklog data (user, project, task, time logged, date).
  - `users`: Store user details (name, email, role, active/inactive status).
  - `portfolios`: Store client portfolio information, grouping multiple Jira projects.
  - `projects`: Store project details fetched from Jira.
  - `portfolio_projects`: Map Jira projects to a client portfolio.
  - `project_assignments`: Map users to projects, tracking planned hours per month.
  - `user_availability`: Track user availability, including planned work capacity and holidays.
  - `change_history`: Log changes in roles and assignments for auditing.
  - `role_distribution`: Store distribution of logged hours per role within projects.

- **Role Management**
  - Define user roles: Developer, QA, PM, BA, IT, and more as needed.
  - Allow superadmin (`luszynski@lbpro.pl`) full access.
  - Enable CRUD operations for user roles and assignments.

- **Portfolio Management**
  - Create client portfolios and assign multiple Jira projects to them.
  - Enable tracking of worklogs within a portfolio.
  - Allow role-based breakdown of logged work within a portfolio.
  - Compare planned vs. actual logged time for each user in a portfolio.

- **Assignment Planning & Worklog Tracking**
  - Assign users to multiple projects within a portfolio.
  - Define planned hours per user per project per month.
  - Track actual logged hours vs. planned hours per project per month.
  - Identify discrepancies where users worked in unassigned projects (Shadow Work Analysis).
  - Enable reassignment and modifications to planned allocations.

- **Reports and Analytics**
  - Daily, weekly, and monthly activity reports.
  - Shadow work analysis (work logged outside assigned projects).
  - Planned vs. actual hours analysis.
  - Overload analysis and heatmaps for activity distribution.
  - Breakdown of logged hours per role in each project.

- **Export Capabilities**
  - Reports in PDF and CSV formats.

- **Scheduler**
  - Automatically fetch and update worklog data from Jira at regular intervals.

---

#### **3.2 Frontend Functionality**
- **Dashboard**
  - Overview of user activity trends.
  - Heatmaps for logged work hours.
  - Alerts for missing worklogs.
  - Overview of planned vs. actual hours at portfolio and project levels.

- **Admin Panel**
  - Manage user roles and project assignments.
  - Manage client portfolios and associated projects.
  - Review history of changes to roles, assignments, and worklog trends.

- **Role Assignment & Portfolio Management**
  - Assign users to multiple projects within a portfolio.
  - Allow percentage-based workload allocation per project.
  - Display user availability based on planned hours and holidays.
  - Enable editing and tracking of user assignments across months.

- **Reports UI**
  - View portfolio-based reports for planned vs. actual hours.
  - Role-based breakdown of logged work within projects.
  - Generate and download reports in PDF/CSV format.

---

### **4. Technical Requirements**

#### **4.1 Backend Stack**
- **Language**: Python
- **Framework**: Flask
- **Database**: SQLite
- **Scheduler**: Flask-APScheduler or Cron

#### **4.2 Frontend Stack**
- **HTML/CSS**: Bootstrap for styling.
- **JavaScript**: Chart.js for visualizations, DataTables.js for tabular data.

#### **4.3 Deployment**
- **Containerization**: Docker for easy deployment.
- **Configuration**: `.env` file for Jira credentials.

---

### **5. Key Screens**

#### **5.1 Dashboard**
- Visual trends of user activity.
- Heatmap of worklogs by hour.
- Alerts for missing worklogs.
- Overview of planned vs. actual hours in portfolios and projects.

#### **5.2 Worklogs**
- Detailed table of worklogs with user, project, task, hours, and date.
- Filterable and sortable view.

#### **5.3 Assignments**
- Interface to assign users to projects and portfolios.
- Visualize planned vs. actual hours per user.
- Track role-based distribution of work in projects.

#### **5.4 Roles Management**
- Manage roles and permissions for users.
- Superadmin-only interface for role edits.

#### **5.5 Reports**
- Generate and download PDF/CSV reports for projects, portfolios, users, and roles.

---

### **6. User Roles**
- **Developer**: Log hours, view personal reports.
- **QA**: Analyze logged hours, submit worklogs.
- **PM**: Manage assignments and generate team reports.
- **Superadmin**: Full access to manage users, roles, assignments, and portfolios.

---

### **7. Milestones and Deliverables**
- **Phase 1**: Backend APIs and database setup.
- **Phase 2**: Frontend implementation of dashboard and reports.
- **Phase 3**: Role and assignment management.
- **Phase 4**: Integration with Jira and automated data fetching.
- **Phase 5**: Portfolio management and advanced reporting.
- **Phase 6**: Final testing, Docker deployment, and documentation.

---

### **8. Success Metrics**
- High adoption rate among team members.
- Accurate data syncing and reporting from Jira.
- Reduced time spent manually analyzing worklogs.
- Positive feedback on usability and performance.

---

### **9. Risks and Mitigations**
- **Risk**: Incomplete data from Jira API.  
  **Mitigation**: Validate data during fetch and log errors.
- **Risk**: Performance issues with large datasets.  
  **Mitigation**: Optimize database queries and implement caching.

---

### **10. Future Enhancements**
- Integration with Power BI or Google Data Studio for advanced analytics.
- Email notifications for weekly/monthly reports.
- AI-based suggestions for workload balancing.
- Support for multiple Jira instances.


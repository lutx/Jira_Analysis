# Product Requirements Document (PRD)

## **Jira Analysis Application**

### **1. Overview**
The Jira Analysis Application is a comprehensive tool designed to analyze and manage worklog data from Jira. It includes features for role-based reporting, project assignments, and activity tracking. The application offers both a modern user interface and robust backend functionalities to assist teams in analyzing and planning their work effectively.

### **2. Objectives**
- Provide detailed insights into worklogs recorded in Jira.
- Allow role-based and project-based analysis of user activity.
- Enable assignment and management of users to projects and portfolios.
- Offer exportable reports for stakeholders.
- Facilitate easy management and tracking of changes via a superadmin panel.

---

### **3. Functional Requirements**

#### **3.1 Backend Functionality**
- **API Integration**
  - Pull worklog data from Jira, including task IDs and timestamps.
  - Fetch project and user details from Jira.
  
- **Database Schema (SQLite)**
  - `worklogs`: Store user worklog data (user, project, task, time logged, date).
  - `users`: Store user details (name, email, role).
  - `portfolios`: Store client portfolio information.
  - `project_assignments`: Map users to projects and track planned hours.
  - `user_availability`: Track user availability and holidays.
  - `change_history`: Log changes in roles and assignments for auditing.

- **Role Management**
  - Define user roles: Developer, QA, PM (Project Manager).
  - Superadmin (`luszynski@lbpro.pl`) with full access.

- **Reports and Analytics**
  - Daily, weekly, and monthly activity reports.
  - Shadow work analysis (work logged outside assigned projects).
  - Planned vs. actual hours analysis.
  - Overload analysis and heatmaps for activity distribution.

- **Export Capabilities**
  - Reports in PDF and CSV formats.

- **Scheduler**
  - Automatically fetch and update worklog data from Jira at regular intervals.

---

#### **3.2 Frontend Functionality**
- **Dashboard**
  - Overview of user activity trends.
  - Heatmaps for logged work hours.
  - Alerts for users missing worklogs.

- **Admin Panel**
  - Manage user roles and project assignments.
  - Review history of changes to roles and assignments.

- **Role Assignment**
  - Assign users to multiple projects with percentage-based workload allocation.
  - Display user availability based on holidays and planned hours.

- **Reports UI**
  - View project-based reports for planned vs. actual hours.
  - Role-based breakdown of logged work.

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

#### **5.2 Worklogs**
- Detailed table of worklogs with user, project, task, hours, and date.
- Filterable and sortable view.

#### **5.3 Assignments**
- Interface to assign users to projects and portfolios.
- Visualize planned vs. actual hours.

#### **5.4 Roles Management**
- Manage roles and permissions for users.
- Superadmin-only interface for role edits.

#### **5.5 Reports**
- Generate and download PDF/CSV reports for projects, users, and roles.

---

### **6. User Roles**
- **Developer**: Log hours, view personal reports.
- **QA**: Analyze logged hours, submit worklogs.
- **PM**: Manage assignments and generate team reports.
- **Superadmin**: Full access to manage users, roles, and configurations.

---

### **7. Milestones and Deliverables**
- **Phase 1**: Backend APIs and database setup.
- **Phase 2**: Frontend implementation of dashboard and reports.
- **Phase 3**: Role and assignment management.
- **Phase 4**: Integration with Jira and automated data fetching.
- **Phase 5**: Final testing, Docker deployment, and documentation.

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


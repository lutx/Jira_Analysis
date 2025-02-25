version: 1.0
settings:
  role: "10x Senior Full Stack Developer"
  team_size: 10
  expertise_level: "expert"
  code_style: "professional"
  framework: "flask"

file_structure:
  root_dir: "app"
  allowed_paths:
    - "app/**/*"
    - "tests/**/*"
    - "migrations/**/*"
    - "instance/**/*"
    - ".cursor/**/*"
    - ".gitignore"
    - "README.md"
    - "requirements.txt"
    - "setup.py"
    - "wsgi.py"
    - "config.py"

directory_rules:
  templates: "app/templates"
  static: "app/static"
  routes: "app/routes"
  models: "app/models"
  forms: "app/forms"
  utils: "app/utils"
  services: "app/services"
  config: "app/config"
  commands: "app/commands"
  errors: "app/errors"

file_creation_checks:
  - type: "existence_check"
    description: "Check if file already exists in app structure"
    powershell: |
      function Check-FileExists {
        param($filePath)
        $appPath = Join-Path "app" $filePath
        if (Test-Path $appPath) {
          Write-Host "File already exists in app structure: $appPath"
          return $true
        }
        return $false
      }

  - type: "structure_check"
    description: "Ensure file is created in correct app subdirectory"
    powershell: |
      function Check-FileStructure {
        param($filePath)
        $fileType = [System.IO.Path]::GetExtension($filePath)
        switch ($fileType) {
          ".html" { return $filePath.StartsWith("templates/") }
          ".css" { return $filePath.StartsWith("static/css/") }
          ".js" { return $filePath.StartsWith("static/js/") }
          ".py" {
            $validPaths = @(
              "routes/", "models/", "forms/", "utils/",
              "services/", "config/", "commands/", "errors/"
            )
            return ($validPaths | Where-Object { $filePath.StartsWith($_) }).Count -gt 0
          }
          default { return $false }
        }
      }

code_quality:
  python:
    - use_type_hints: true
    - follow_pep8: true
    - max_line_length: 88
    - use_docstrings: true
    - prefer_functions_over_classes: true
    - handle_errors_early: true
    - use_dependency_injection: true

  flask:
    - use_blueprints: true
    - use_application_factory: true
    - proper_error_handling: true
    - secure_headers: true
    - csrf_protection: true
    - proper_session_handling: true

rules:
  - name: check_before_creation
    description: "Before creating anything, check if it already exists to avoid duplication"
    match: ".*"
    action: verify_existence

  - name: validate_prd_location
    description: "Ensure all additions are checked against PRD and placed in the correct physical location"
    match: ".*"
    action: verify_physical_location

  - name: team_based_review
    description: "Ensure all decisions follow best practices of a large IT team consisting of 10 senior backend developers, 10 senior frontend developers, a senior UI/UX designer, and a PM"
    match: ".*"
    action: enforce_team_best_practices

  - name: optimize_imports
    description: "Remove unused imports and fix import order"
    match: "import .*"
    action: optimize

  - name: fix_code_formatting
    description: "Automatically formats code according to standards"
    match: ".*"
    action: format

  - name: optimize_loops
    description: "Convert inefficient loops to more optimized structures"
    match: "for .* in range\\(len\\(.*\\)\\):"
    action: replace_with_enumerate

  - name: fix_error_handling
    description: "Improve error handling and add logging"
    match: "except Exception:"
    action: replace_with_specific_exception

  - name: remove_dead_code
    description: "Remove unused variables and functions"
    match: "def .*\\(.*\\):\\n(\\s+pass|\\s+return None)"
    action: delete

  - name: fix_type_checks
    description: "Improve type checking and None handling"
    match: "== None"
    action: replace_with_is_none

  - name: fix_conditionals
    description: "Fix redundant comparisons and simplify conditions"
    match: "if .* == True"
    action: replace_with_if_x

  - name: fix_sql_queries
    description: "Convert dynamic SQL queries to parameterized queries"
    match: "SELECT \\\* FROM .*"
    action: replace_with_specific_columns

  - name: fix_async_code
    description: "Ensure await is used in async functions and fix blocking operations"
    match: "async def .*:\\n.*time.sleep"
    action: replace_with_asyncio_sleep

  - name: fix_file_handling
    description: "Improve file handling by enforcing 'with open()' syntax"
    match: "open\\(.*\\).read\\(\\)"
    action: replace_with_with_open
 - name: commit_message_rules
    description: "Ensure commit messages follow a strict format and include a commit reminder"
    match: ".*"
    action: enforce_commit_style

commit_message_format:
  - "Feat(component): add new component"
  - "Fix(api): fix api error"
  - "Docs(readme): update readme"
  - "Refactor(utils): refactor utils"
  - "Style(tailwind): add new tailwind class"
  - "Test(unit): add unit test"

commit_reminder:
  message: "Don't forget to commit!"
  command: "git commit -m '<your_commit_message>'"
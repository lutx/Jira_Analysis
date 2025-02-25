# Must be run as Administrator
$ErrorActionPreference = "Stop"

try {
    # Get the current directory
    $projectPath = (Get-Location).Path
    Write-Host "Setting permissions for: $projectPath"

    # Get current user
    $currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    Write-Host "Current user: $currentUser"

    # Create instance directory if it doesn't exist
    $instancePath = Join-Path $projectPath "instance"
    if (-not (Test-Path $instancePath)) {
        New-Item -ItemType Directory -Force -Path $instancePath | Out-Null
        Write-Host "Created instance directory"
    }

    # Set permissions for instance directory
    $acl = Get-Acl $instancePath
    $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        $currentUser,
        "FullControl",
        "ContainerInherit,ObjectInherit",
        "None",
        "Allow"
    )
    
    # Remove existing rules for the current user
    $acl.Access | Where-Object { $_.IdentityReference.Value -eq $currentUser } | ForEach-Object {
        $acl.RemoveAccessRule($_) | Out-Null
    }
    
    # Add new rule
    $acl.AddAccessRule($rule)
    
    # Apply the new ACL
    Set-Acl -Path $instancePath -AclObject $acl
    Write-Host "Set permissions for instance directory"

    # Create and set permissions for database file
    $dbPath = Join-Path $instancePath "app.db"
    if (Test-Path $dbPath) {
        Remove-Item $dbPath -Force
        Write-Host "Removed existing database file"
    }
    
    # Create empty file
    New-Item -ItemType File -Path $dbPath -Force | Out-Null
    Write-Host "Created new database file"
    
    # Set permissions for database file
    $acl = Get-Acl $dbPath
    $acl.SetAccessRule($rule)
    Set-Acl -Path $dbPath -AclObject $acl
    Write-Host "Set permissions for database file"

    Write-Host "`nPermissions set successfully!"
    
} catch {
    Write-Host "Error: $_"
    exit 1
} 
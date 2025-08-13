# GetFolderAudit.ps1
# Purpose: Retrieves ACL and Audit rules for a given path

param (
    [Parameter(Mandatory = $true)]
    [string]$Path
)

# Check if path exists
if (-not (Test-Path $Path)) {
    Write-Error "The path '$Path' does not exist."
    exit
}

# Retrieve ACL with Audit info (requires running as Administrator)
try {
    Get-Acl $Path -Audit | Format-List
} catch {
    Write-Error "Failed to retrieve audit information. Try running PowerShell as Administrator."
}

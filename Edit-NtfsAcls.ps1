<# 
.SYNOPSIS
  Edit and modify NTFS ACL permissions on files and folders (Windows).

.DESCRIPTION
  Safely grants/denies/removes ACEs, toggles inheritance, changes owner,
  and supports backup/restore via SDDL. Uses -WhatIf for dry-runs.

.EXAMPLES
  # Grant Modify to a group (recursive)
  .\Edit-NtfsAcls.ps1 -Path 'C:\Data' -Identity 'CONTOSO\DataTeam' -Rights Modify -Recurse -WhatIf

  # Replace explicit ACEs for a user with ReadAndExecute
  .\Edit-NtfsAcls.ps1 -Path 'C:\Data\Reports' -Identity 'jdoe' -Rights ReadAndExecute -Replace

  # Disable inheritance but preserve inherited rules as explicit
  .\Edit-NtfsAcls.ps1 -Path 'C:\Shares\HR' -DisableInheritance -PreserveInherited

  # Backup and restore
  .\Edit-NtfsAcls.ps1 -Path 'C:\Data' -BackupTo '.\acl_backup.csv'
  .\Edit-NtfsAcls.ps1 -RestoreFrom '.\acl_backup.csv'

#>
[CmdletBinding(SupportsShouldProcess=$true, ConfirmImpact='Medium', DefaultParameterSetName='edit')]
param(
  [Parameter(ParameterSetName='edit', Position=0, ValueFromPipeline=$true, ValueFromPipelineByPropertyName=$true)]
  [string[]] $Path,

  [Parameter(ParameterSetName='edit')]
  [string] $Identity,

  [Parameter(ParameterSetName='edit')]
  [ValidateSet(
    'ReadData','WriteData','AppendData','ReadExtendedAttributes','WriteExtendedAttributes','ExecuteFile','DeleteSubdirectoriesAndFiles',
    'ReadAttributes','WriteAttributes','Delete','ReadPermissions','ChangePermissions','TakeOwnership','Synchronize',
    'FullControl','Modify','ReadAndExecute','ListDirectory','Read','Write'
  )]
  [string[]] $Rights,

  [Parameter(ParameterSetName='edit')]
  [ValidateSet('Allow','Deny')]
  [string] $Access = 'Allow',

  [Parameter(ParameterSetName='edit')]
  [switch] $Remove,

  [Parameter(ParameterSetName='edit')]
  [switch] $Replace,

  [Parameter(ParameterSetName='edit')]
  [switch] $Clear,

  [Parameter(ParameterSetName='edit')]
  [switch] $KeepInherited = $true,

  [Parameter(ParameterSetName='edit')]
  [switch] $EnableInheritance,

  [Parameter(ParameterSetName='edit')]
  [switch] $DisableInheritance,

  [Parameter(ParameterSetName='edit')]
  [switch] $PreserveInherited,

  [Parameter(ParameterSetName='edit')]
  [string] $Owner,

  [Parameter(ParameterSetName='edit')]
  [switch] $Recurse,

  [Parameter(ParameterSetName='edit')]
  [switch] $DirectoryOnly,

  [Parameter(ParameterSetName='edit')]
  [switch] $FileOnly,

  [Parameter(ParameterSetName='backup')]
  [string] $BackupTo,

  [Parameter(ParameterSetName='restore')]
  [string] $RestoreFrom
)

begin {
  function Convert-ToRightsEnum {
    param([string[]]$Names)
    $acc = [System.Security.AccessControl.FileSystemRights]::None
    foreach ($n in $Names) { $acc = $acc -bor ([System.Security.AccessControl.FileSystemRights]::$n) }
    return $acc
  }

  function New-AccessRule {
    param([string] $Identity, [System.Security.AccessControl.FileSystemRights] $Rights, [bool] $IsDirectory, [string]$Access)
    $inherit = if ($IsDirectory) {
      [System.Security.AccessControl.InheritanceFlags]::ContainerInherit -bor `
      [System.Security.AccessControl.InheritanceFlags]::ObjectInherit
    } else { [System.Security.AccessControl.InheritanceFlags]::None }
    $prop = [System.Security.AccessControl.PropagationFlags]::None
    $type = if ($Access -eq 'Deny') { [System.Security.AccessControl.AccessControlType]::Deny } else { [System.Security.AccessControl.AccessControlType]::Allow }
    New-Object System.Security.AccessControl.FileSystemAccessRule($Identity, $Rights, $inherit, $prop, $type)
  }

  function Get-TargetItems {
    param([string[]]$Path, [switch]$Recurse, [switch]$DirectoryOnly, [switch]$FileOnly)
    $items = @()
    foreach ($p in $Path) {
      if (Test-Path -LiteralPath $p) { $items += Get-Item -LiteralPath $p } else { Write-Warning "Path not found: $p" }
    }
    if ($Recurse) {
      foreach ($root in $items.Clone()) {
        $children = Get-ChildItem -LiteralPath $root.FullName -Recurse -Force -ErrorAction SilentlyContinue
        if ($DirectoryOnly) { $children = $children | Where-Object { $_.PSIsContainer } }
        elseif ($FileOnly) { $children = $children | Where-Object { -not $_.PSIsContainer } }
        $items += $children
      }
    }
    $seen=@{}; $result=@()
    foreach ($i in $items) { if (-not $seen.ContainsKey($i.FullName)) { $result += $i; $seen[$i.FullName]=$true } }
    return $result
  }

  function Backup-Acls { param([string[]]$Paths,[string]$OutCsv)
    $rows = foreach ($p in $Paths) {
      if (Test-Path -LiteralPath $p) { $acl = Get-Acl -LiteralPath $p; [pscustomobject]@{ Path=$p; Sddl=$acl.Sddl } }
    }
    $rows | Export-Csv -LiteralPath $OutCsv -NoTypeInformation -Encoding UTF8
  }

  function Restore-Acls { param([string]$Csv)
    $rows = Import-Csv -LiteralPath $Csv
    foreach ($row in $rows) {
      $p=$row.Path; $sddl=$row.Sddl
      if (-not (Test-Path -LiteralPath $p)) { Write-Warning "Missing: $p"; continue }
      $item = Get-Item -LiteralPath $p
      $sec = if ($item.PSIsContainer) { New-Object System.Security.AccessControl.DirectorySecurity } else { New-Object System.Security.AccessControl.FileSecurity }
      try { $sec.SetSecurityDescriptorSddlForm($sddl); if ($PSCmdlet.ShouldProcess($p,"Restore ACL")) { Set-Acl -LiteralPath $p -AclObject $sec } }
      catch { Write-Warning "Restore failed for $p : $_" }
    }
  }
}

process {
  if ($PSCmdlet.ParameterSetName -eq 'backup' -and $BackupTo) { if (-not $Path) { throw "-Path required" }; Backup-Acls -Paths $Path -OutCsv $BackupTo; return }
  if ($PSCmdlet.ParameterSetName -eq 'restore' -and $RestoreFrom) { Restore-Acls -Csv $RestoreFrom; return }
  if (-not $Path) { throw "Specify -Path." }

  $targets = Get-TargetItems -Path $Path -Recurse:$Recurse -DirectoryOnly:$DirectoryOnly -FileOnly:$FileOnly
  if (-not $targets) { Write-Warning "No targets found."; return }
  $rightsEnum = if ($Rights) { Convert-ToRightsEnum -Names $Rights } else { $null }

  foreach ($t in $targets) {
    $p=$t.FullName; $isDir=$t.PSIsContainer; $acl=Get-Acl -LiteralPath $p

    if ($Owner) {
      try { if ($PSCmdlet.ShouldProcess($p,"Set owner to $Owner")) { $acl.SetOwner([System.Security.Principal.NTAccount]$Owner); Set-Acl -LiteralPath $p -AclObject $acl } }
      catch { Write-Warning "Owner set failed on $p : $_" }
      $acl = Get-Acl -LiteralPath $p
    }

    if ($EnableInheritance -and $DisableInheritance) { Write-Error "Choose only one of -EnableInheritance or -DisableInheritance."; continue }
    if ($EnableInheritance) { if ($PSCmdlet.ShouldProcess($p,"Enable inheritance")) { $acl.SetAccessRuleProtection($false,$true); Set-Acl -LiteralPath $p -AclObject $acl } ; $acl=Get-Acl -LiteralPath $p }
    if ($DisableInheritance) { if ($PSCmdlet.ShouldProcess($p,"Disable inheritance (PreserveInherited=$PreserveInherited)")) { $acl.SetAccessRuleProtection($true,[bool]$PreserveInherited); Set-Acl -LiteralPath $p -AclObject $acl } ; $acl=Get-Acl -LiteralPath $p }

    if ($Clear) {
      if ($PSCmdlet.ShouldProcess($p,"Clear explicit ACEs (KeepInherited=$KeepInherited)")) {
        $newAcl = if ($isDir) { New-Object System.Security.AccessControl.DirectorySecurity } else { New-Object System.Security.AccessControl.FileSecurity }
        if ($KeepInherited) { foreach ($rule in $acl.Access) { if ($rule.IsInherited) { [void]$newAcl.AddAccessRule($rule) } } }
        $newAcl.SetOwner($acl.Owner); $newAcl.SetGroup($acl.Group)
        Set-Acl -LiteralPath $p -AclObject $newAcl
      }
      $acl = Get-Acl -LiteralPath $p
    }

    if ($Identity) {
      if ($Remove -or $Replace) {
        $toRemove = $acl.Access | Where-Object { -not $_.IsInherited -and $_.IdentityReference.Value -ieq $Identity }
        if ($rightsEnum) { $toRemove = $toRemove | Where-Object { $_.FileSystemRights -band $rightsEnum } }
        foreach ($r in $toRemove) {
          if ($PSCmdlet.ShouldProcess($p,"Remove ACE ($($r.IdentityReference) : $($r.FileSystemRights) : $($r.AccessControlType))")) { [void]$acl.RemoveAccessRuleSpecific($r) }
        }
      }

      if ($Rights -and (-not $Remove)) {
        $rule = New-AccessRule -Identity $Identity -Rights $rightsEnum -IsDirectory:$isDir -Access $Access
        $exists = $false
        foreach ($r in $acl.Access) {
          if (-not $r.IsInherited -and $r.IdentityReference.Value -ieq $Identity -and ($r.FileSystemRights -band $rightsEnum) -and $r.AccessControlType.ToString() -ieq $Access) { $exists = $true; break }
        }
        if (-not $exists) { if ($PSCmdlet.ShouldProcess($p,"Add ACE ($Identity : $Rights : $Access)")) { [void]$acl.AddAccessRule($rule) } } else { Write-Verbose "ACE already present on $p" }
      }

      if ($PSCmdlet.ShouldProcess($p,"Apply ACL changes")) {
        try { Set-Acl -LiteralPath $p -AclObject $acl } catch { Write-Warning "Set-Acl failed on $p : $_" }
      }
    }
  }
}
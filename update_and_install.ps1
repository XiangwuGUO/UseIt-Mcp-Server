# ============================================================================
# Git Update and Dependency Installation Script
# Description: Updates the repository and installs MCP server dependencies
# Version: 1.0
# ============================================================================

[CmdletBinding()]
param(
    [Parameter(Position=0)]
    [ValidateSet('all', 'update', 'install', 'help')]
    [string]$Command = 'all'
)

# --- Script Configuration ---
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectDir = $ScriptDir
$McpServerDir = Join-Path -Path $ProjectDir -ChildPath "mcp-server"
$RequirementsFile = Join-Path -Path $McpServerDir -ChildPath "requirements.txt"

# --- Helper Functions ---

function Show-Header {
    param([string]$Message)
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host $Message -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
}

function Update-Repository {
    Show-Header "Updating Git Repository"

    # Check if git is available
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        Write-Host "ERROR: Git not found. Please ensure Git is installed and in your system's PATH." -ForegroundColor Red
        return $false
    }

    # Check if current directory is a git repository
    $gitDir = Join-Path -Path $ProjectDir -ChildPath ".git"
    if (-not (Test-Path $gitDir)) {
        Write-Host "ERROR: Not a git repository: $ProjectDir" -ForegroundColor Red
        return $false
    }

    try {
        Write-Host "INFO: Current directory: $ProjectDir" -ForegroundColor Cyan

        # Check current branch
        $currentBranch = & git -C $ProjectDir rev-parse --abbrev-ref HEAD 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "ERROR: Failed to get current branch" -ForegroundColor Red
            return $false
        }
        Write-Host "INFO: Current branch: $currentBranch" -ForegroundColor Green

        # Check for uncommitted changes
        $status = & git -C $ProjectDir status --porcelain 2>&1
        if ($status) {
            Write-Host "WARN: You have uncommitted changes:" -ForegroundColor Yellow
            Write-Host $status -ForegroundColor Gray
            Write-Host ""
            $response = Read-Host "Do you want to continue with git pull? (y/n)"
            if ($response -ne 'y' -and $response -ne 'Y') {
                Write-Host "INFO: Update cancelled by user" -ForegroundColor Yellow
                return $false
            }
        }

        # Fetch latest changes
        Write-Host "INFO: Fetching latest changes..." -ForegroundColor Cyan
        & git -C $ProjectDir fetch origin 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "ERROR: Failed to fetch from remote repository" -ForegroundColor Red
            return $false
        }

        # Pull changes
        Write-Host "INFO: Pulling latest changes from origin/$currentBranch..." -ForegroundColor Cyan
        $pullOutput = & git -C $ProjectDir pull origin $currentBranch 2>&1
        Write-Host $pullOutput -ForegroundColor Gray

        if ($LASTEXITCODE -eq 0) {
            Write-Host "SUCCESS: Repository updated successfully!" -ForegroundColor Green

            # Show latest commit
            $latestCommit = & git -C $ProjectDir log -1 --oneline 2>&1
            Write-Host "INFO: Latest commit: $latestCommit" -ForegroundColor Cyan
            return $true
        } else {
            Write-Host "ERROR: Failed to pull changes" -ForegroundColor Red
            return $false
        }

    } catch {
        Write-Host "ERROR: Git operation failed: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

function Install-Dependencies {
    Show-Header "Installing MCP Server Dependencies"

    # Check if Python is available
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Write-Host "ERROR: Python not found. Please ensure Python is installed and in your system's PATH." -ForegroundColor Red
        return $false
    }

    # Check Python version
    $pythonVersion = & python --version 2>&1
    Write-Host "INFO: Python version: $pythonVersion" -ForegroundColor Cyan

    # Check if requirements file exists
    if (-not (Test-Path $RequirementsFile)) {
        Write-Host "ERROR: Requirements file not found: $RequirementsFile" -ForegroundColor Red
        return $false
    }

    Write-Host "INFO: Requirements file: $RequirementsFile" -ForegroundColor Cyan

    try {
        # Upgrade pip first
        Write-Host "INFO: Upgrading pip..." -ForegroundColor Cyan
        & python -m pip install --upgrade pip 2>&1 | Out-Null

        if ($LASTEXITCODE -eq 0) {
            Write-Host "SUCCESS: pip upgraded successfully" -ForegroundColor Green
        } else {
            Write-Host "WARN: pip upgrade failed, continuing anyway..." -ForegroundColor Yellow
        }

        # Install dependencies
        Write-Host "INFO: Installing dependencies from requirements.txt..." -ForegroundColor Cyan
        Write-Host "INFO: This may take a few minutes..." -ForegroundColor Yellow

        $installOutput = & python -m pip install -r $RequirementsFile 2>&1
        Write-Host $installOutput -ForegroundColor Gray

        if ($LASTEXITCODE -eq 0) {
            Write-Host "SUCCESS: All dependencies installed successfully!" -ForegroundColor Green

            # Show installed packages count
            Write-Host ""
            Write-Host "INFO: Verifying key packages..." -ForegroundColor Cyan
            $keyPackages = @('mcp', 'PyYAML', 'librosa', 'fastapi', 'flask')
            foreach ($package in $keyPackages) {
                $checkResult = & python -m pip show $package 2>&1
                if ($LASTEXITCODE -eq 0) {
                    $version = ($checkResult | Select-String "Version:").ToString().Split(":")[1].Trim()
                    Write-Host "  OK $package ($version)" -ForegroundColor Green
                } else {
                    Write-Host "  !! $package (not found)" -ForegroundColor Red
                }
            }
            return $true
        } else {
            Write-Host "ERROR: Failed to install some dependencies" -ForegroundColor Red
            Write-Host "INFO: Please check the error messages above" -ForegroundColor Yellow
            return $false
        }

    } catch {
        Write-Host "ERROR: Installation failed: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# --- Main Logic ---

switch ($Command) {
    "all" {
        $updateSuccess = Update-Repository
        Write-Host ""
        $installSuccess = Install-Dependencies

        Write-Host ""
        Show-Header "Summary"
        Write-Host "Repository Update: $(if ($updateSuccess) { 'SUCCESS' } else { 'FAILED' })" -ForegroundColor $(if ($updateSuccess) { 'Green' } else { 'Red' })
        Write-Host "Dependencies Install: $(if ($installSuccess) { 'SUCCESS' } else { 'FAILED' })" -ForegroundColor $(if ($installSuccess) { 'Green' } else { 'Red' })

        if ($updateSuccess -and $installSuccess) {
            Write-Host ""
            Write-Host "SUCCESS: All operations completed successfully!" -ForegroundColor Green
            Write-Host "INFO: You can now start the MCP servers using: .\start_mcp_server.ps1 start" -ForegroundColor Cyan
        } else {
            Write-Host ""
            Write-Host "WARN: Some operations failed. Please check the messages above." -ForegroundColor Yellow
        }
    }
    "update" {
        $success = Update-Repository
        if ($success) {
            Write-Host ""
            Write-Host "SUCCESS: Repository updated successfully!" -ForegroundColor Green
        }
    }
    "install" {
        $success = Install-Dependencies
        if ($success) {
            Write-Host ""
            Write-Host "SUCCESS: Dependencies installed successfully!" -ForegroundColor Green
        }
    }
    "help" {
        Write-Host "Git Update and Dependency Installation Script" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Usage: .\update_and_install.ps1 [command]" -ForegroundColor White
        Write-Host ""
        Write-Host "Commands:" -ForegroundColor Yellow
        Write-Host "  all       Update repository and install dependencies (default)" -ForegroundColor White
        Write-Host "  update    Only update the git repository (git pull)" -ForegroundColor White
        Write-Host "  install   Only install dependencies from requirements.txt" -ForegroundColor White
        Write-Host "  help      Show this help message" -ForegroundColor White
        Write-Host ""
        Write-Host "Examples:" -ForegroundColor Yellow
        Write-Host "  .\update_and_install.ps1              # Run both update and install" -ForegroundColor Gray
        Write-Host "  .\update_and_install.ps1 all          # Same as above" -ForegroundColor Gray
        Write-Host "  .\update_and_install.ps1 update       # Only git pull" -ForegroundColor Gray
        Write-Host "  .\update_and_install.ps1 install      # Only install dependencies" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Notes:" -ForegroundColor Yellow
        Write-Host "  - Repository path: $ProjectDir" -ForegroundColor Gray
        Write-Host "  - Requirements file: $RequirementsFile" -ForegroundColor Gray
        Write-Host "  - Make sure you have Git and Python installed and in your PATH" -ForegroundColor Gray
    }
    default {
        Write-Host "ERROR: Unknown command: $Command" -ForegroundColor Red
        Write-Host "INFO: Use 'help' to see available commands." -ForegroundColor Yellow
        exit 1
    }
}

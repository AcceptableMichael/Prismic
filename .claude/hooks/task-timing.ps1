<#
.SYNOPSIS
    Appends a wall-clock start/stop timestamp to task-timing.log.

.DESCRIPTION
    Called from both the UserPromptSubmit and Stop hooks with -Event
    start/stop respectively. Each user prompt -> Claude-finishes-responding
    cycle is one "task"; the two log lines share a session_id (read from the
    hook's JSON payload on stdin) so they can be paired up later for
    duration analysis -- e.g. comparing average task length before/after a
    refactor of this codebase.

    Log format (tab-separated, one line per event):
        <ISO-8601 UTC timestamp>	<start|stop>	<session_id>

    Deliberately append-only and dumb: no in-script pairing or duration
    math, so a missed event (a crashed session, a skipped Stop) never
    corrupts state that later events depend on. Compute durations by
    joining start/stop rows on session_id when analyzing the log.
#>
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('start', 'stop')]
    [string]$Event
)

$ErrorActionPreference = 'Stop'

$payload = [Console]::In.ReadToEnd()
$sessionId = 'unknown'
if ($payload) {
    try {
        $sessionId = (ConvertFrom-Json -InputObject $payload).session_id
    } catch {
        # Malformed/empty stdin shouldn't block the hook -- fall back to
        # 'unknown' rather than throwing away the timestamp entirely.
    }
}
if (-not $sessionId) { $sessionId = 'unknown' }

$timestamp = (Get-Date).ToUniversalTime().ToString('o')
$logPath = Join-Path $PSScriptRoot '..\task-timing.log'
$line = "{0}`t{1}`t{2}" -f $timestamp, $Event, $sessionId

$file = New-Object System.IO.FileInfo($logPath)
if (-not $file.Directory.Exists) { $file.Directory.Create() }
# ASCII, not utf8 -- session ids and our own fields are always plain ASCII,
# and Add-Content's utf8 encoding writes a BOM on first creation, which
# would land on the very first log line and complicate later parsing.
[System.IO.File]::AppendAllText($logPath, $line + "`r`n", [System.Text.Encoding]::ASCII)

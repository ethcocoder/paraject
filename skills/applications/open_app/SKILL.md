# Open Application

## Name
open_app

## Purpose
Return an intent to launch an explicitly allowlisted application.

## Preconditions
The application command is present in the desktop allowlist.

## Inputs
`command`: an allowlisted application identifier.

## Output
A validated application-open intent.

## Safety
No arbitrary command or shell text is executed. Launching requires a later OS adapter.

## Tool
open_app

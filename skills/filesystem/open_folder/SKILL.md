# Open Folder

## Name
open_folder

## Purpose
Validate a permitted folder and return an intent for the desktop adapter to open it.

## Preconditions
The path exists, is a directory, and is inside a configured permitted root.

## Inputs
`path`: absolute or user-resolved folder path.

## Output
A validated folder-open intent containing the canonical path.

## Safety
The path is sandbox-checked. This skill does not execute arbitrary shell text.

## Tool
open_folder

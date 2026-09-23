# List Folder

## Name
list_folder

## Purpose
List immediate entries in a permitted folder.

## Preconditions
The path exists, is a directory, and is inside a configured permitted root.

## Inputs
`path`: folder path.

## Output
A bounded list of entries with names and file/folder types.

## Safety
Read-only operation; path traversal outside permitted roots is rejected.

## Tool
list_folder

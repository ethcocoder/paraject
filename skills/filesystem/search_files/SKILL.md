# Search Files

## Name
search_files

## Purpose
Find files and folders by name within a permitted root.

## Preconditions
The root path is permitted and is a directory.

## Inputs
`path`: search root; `query`: case-insensitive name fragment.

## Output
At most 100 matching paths.

## Safety
Read-only and restricted to permitted roots.

## Tool
search_files

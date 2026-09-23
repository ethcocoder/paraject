# Copy File

## Name
copy_file

## Purpose
Copy one file inside permitted filesystem roots.

## Preconditions
The source exists as a file and the destination does not exist.

## Inputs
`source`: existing file; `destination`: new path.

## Output
A structured copy result.

## Safety
Both paths are sandbox-checked and existing destinations are never overwritten.

## Tool
copy_file

# Delete File

## Name
delete_file

## Purpose
Delete one file only after explicit user confirmation.

## Preconditions
The source exists as a file and the user has confirmed the exact path.

## Inputs
`path`: file to delete; `confirmed`: explicit confirmation boolean.

## Output
A structured deletion result.

## Safety
The tool rejects every request without `confirmed=true`, and the path remains sandbox-checked.

## Tool
delete_file

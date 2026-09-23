# Create Folder

## Name
create_folder

## Purpose
Create one new folder inside a permitted root.

## Preconditions
The parent path is permitted and the destination does not already exist.

## Inputs
`path`: destination folder path.

## Output
A created-folder result with canonical path.

## Safety
The path is sandbox-checked and no overwrite is performed.

## Tool
create_folder

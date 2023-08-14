# TextNoteCleanUp
This script parses through all text notes in the Revit model and cleans up duplicate text types (based on settings config of text type) and renames the type based on the settings config of the type. I have come up with a solution for replacing text instances in a group and also keeps original location of group after recreating it if origin was set.

The Groups file contains the function for finding and updating groups that contain text note instances of duplicate text types that need to be replaced

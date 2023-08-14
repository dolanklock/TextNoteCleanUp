# TextNoteCleanUp
This script parses through all text notes in the Revit model and cleans up duplicate text types (matches duplicates based on settings config of text type) and renames the type based on the settings config of the type (this can be customized). I have come up with a solution for replacing text instances in a group and also keeping the original location of the group after recreating it if the origin was set.

The Groups.py file contains the function for finding and updating groups that contain text note instances of duplicate text types that need to be replaced. The script.py file contains the rest of the computation.

import clr

clr.AddReferenceByPartialName('PresentationCore')
clr.AddReferenceByPartialName('AdWindows')
clr.AddReferenceByPartialName("PresentationFramework")
clr.AddReferenceByPartialName('System')
clr.AddReferenceByPartialName('System.Windows.Forms')

uiapp = __revit__
uidoc = uiapp.ActiveUIDocument
doc = uiapp.ActiveUIDocument.Document

from GetSetParameters import *
from pyrevit import forms, revit, DB, script
from GetSetParameters import *
import Selection
import math
import itertools
from rpw import db
import Groups
import projectfunctions

# CODE BELOW HERE #


# TODO: add for text, set text type props (leader/border offset etc,...)

# create a script that updates all text types to the correct name based off of type properties
# example, it would set first font, size, color, opaque or transparent, then the rest would be based off
# if the properties are true or not, if bold then add to name "(bold)" if underlines then add to the name
# "(underlined)"


# ------------------------------ TEXT TYPES --------------------------------#


# ------ INFO ------- #
# main naming scheme text types
# 2.5mm Arial Narrow Blue_CENTRUS
# if has other attributes checked (bold, underlined,)
# 2.5mm Arial Narrow (Opaque-Filled Dot-Bold-Italic-Black)
# [text size] [font] ([background]-[leader arrowhead]-[bold]-[italic]-[underlined]-[color])

# text note type parameters
# (Graphics) Color, Line Weight, Background, Show Border, Leader/Border Offset, Leader Arrowhead
# (Text) Text Font, Text Size, Tab Size, Bold, Italic, Underline, Width Factor
# ------ INFO ------- #

# ---------- STEPS ---------- #

# get each text type, check name is correct based of type settings config, check if another type with the same settings
# already exists (might need to create a dict with text type and correct name and then check the dict for same value
# of name and then find replace...),

# --------- Group logic ------------- #

# script is getting group members and chaning the incorrect text types the group instances and then regrouping those items
# as a group then it is renaming the old group with suffix OLD and then changing all of the old types out with the new group 
# and then deleting the old group type from the model

# ------------------------ Variables ------------------------- #

WIDTH_FACTOR = 0.8
LEADER_BORDER_OFFSET = 0.025

all_text_types = DB.FilteredElementCollector(doc).OfClass(DB.TextNoteType)


# ------------------------ Functions --------------------------- #


class TextNoteType:
    """A class that is used to get type parameter values of the TextNoteType passed into methods argument

    Returns:
        _type_: _description_
    """
    TEXT_NOTE_SUFFIX = "_CENTRUS"

    @staticmethod
    def font(text_type):
        """Gets TextNoteType font parameter value

        Args:
            text_type (TextNoteType):

        Returns:
            String: returns the TextNoteType font value as string
        """
        return GetParameter.get_instance_parameter_by_name(text_type, "Text Font")

    @staticmethod
    def color(text_type):
        return GetParameter.get_instance_parameter_by_name(text_type, "Color")

    @staticmethod
    def is_bold(text_type):
        return GetParameter.get_instance_parameter_by_name(text_type, "Bold")

    @staticmethod
    def is_underlined(text_type):
        return GetParameter.get_instance_parameter_by_name(text_type, "Underline")

    @staticmethod
    def is_italic(text_type):
        return GetParameter.get_instance_parameter_by_name(text_type, "Italic")

    @staticmethod
    def background(text_type):
        return text_type.LookupParameter("Background").AsValueString()

    @staticmethod
    def text_size(text_type):
        text_size = GetParameter.get_instance_parameter_by_name(text_type, "Text Size")
        text_size = float(text_size) * 304.8
        return math.ceil(text_size)

    @staticmethod
    def leader_border_offset(text_type):
        return GetParameter.get_instance_parameter_by_name(text_type, "Leader/Border Offset")

    @staticmethod
    def line_weight(text_type):
        """returns the TextNoteType line weight parameter value

        Args:
            text_type (TextNoteType): _description_

        Returns:
            _type_: _description_
        """
        return GetParameter.get_instance_parameter_by_name(text_type, "Line Weight")

    @staticmethod
    def is_show_border(text_type):
        return GetParameter.get_instance_parameter_by_name(text_type, "Show Border")

    @staticmethod
    def leader_arrowhead(text_type):
        return text_type.LookupParameter("Leader Arrowhead").AsValueString()

    @staticmethod
    def tab_size(text_type):
        return GetParameter.get_instance_parameter_by_name(text_type, "Tab Size")

    @staticmethod
    def text_type_name(text_type):
        """Gets the correct type name for the TextNoteType based on the configuration of its type parameters

        Args:
            text_type (TextNoteType):

        Returns:
            String: returns the TextNoteType correct name based on type parameters
        """
        font = TextNoteType.font(text_type)
        text_size = TextNoteType.text_size(text_type)
        color = TextNoteType.color(text_type)
        # print("color - {} - {}".format(color, GetParameter.get_type_name(text_type)))
        background = TextNoteType.background(text_type)
        bold = TextNoteType.is_bold(text_type)
        italic = TextNoteType.is_italic(text_type)
        underline = TextNoteType.is_underlined(text_type)
        show_border = TextNoteType.is_show_border(text_type)
        text_note_name_start = "{}mm {} {}".format(str(text_size), str(font), str(color))
        attr_lst = []
        attr_lst.append(str(background))
        attr_lst.append(TextNoteType.leader_arrowhead(text_type))
        if bold:
            attr_lst.append("Bold")
        if italic:
            attr_lst.append("Italic")
        if underline:
            attr_lst.append("Underlined")
        if show_border:
            attr_lst.append("Show Border")
        text_note_name_middle = " ({})".format("-".join(attr_lst))
        text_note_name = text_note_name_start + text_note_name_middle + TextNoteType.TEXT_NOTE_SUFFIX
        return text_note_name

class TextType:
    def __init__(self, text_type):
        """_summary_

        Args:
            text_type (DB.TextNoteType): _description_
        """
        self.text_type = text_type
        self.purge = False
        self.updated_text_type = None

    def text_type_id(self):
        return self.text_type.Id
    
def get_all_instances_of_type(type):
    """
    Gets all instances of text notes in the project of the given type
    Args:
        type: (TextNoteType)

    Returns: (TextNote[]) List of all instances of text notes

    """
    all_instances_of_text = Selection.GetElementsFromDoc.all_text(doc, elements_only=True)
    all_instances_of_type = [t for t in all_instances_of_text if t.GetTypeId() == type.Id]
    return all_instances_of_type

def check_group_type_exists(search_list, group_id):
    """
    Check to see if the group type exists in the given search list
    Args:
        search_list: (GroupId) List of group ids
        group_id: (GroupId) the group id to search for

    Returns: (Bool) returns True if type exists inside the search list, else False

    """
    for i in search_list:
        if str(i.GroupId) == str(group_id):
            return True
        return False

def main():
    # configure static parameters
    for text_type in all_text_types:
        SetParameter.set_instance_parameter_value(text_type, parameter_name="Width Factor",
                                                  parameter_value=WIDTH_FACTOR)
        SetParameter.set_instance_parameter_value(text_type, parameter_name="Leader/Border Offset",
                                                  parameter_value=LEADER_BORDER_OFFSET)

    # checking for duplicate types
    text_type_data = []
    for text_type in all_text_types:
        all_attr = (TextNoteType.font(text_type),
                    TextNoteType.is_bold(text_type),
                    TextNoteType.is_italic(text_type),
                    TextNoteType.is_underlined(text_type),
                    TextNoteType.is_show_border(text_type),
                    TextNoteType.text_size(text_type),
                    TextNoteType.leader_arrowhead(text_type),
                    TextNoteType.leader_border_offset(text_type),
                    TextNoteType.background(text_type),
                    TextNoteType.line_weight(text_type),
                    TextNoteType.tab_size(text_type),
                    TextNoteType.color(text_type))

        all_attr = (str(i) for i in all_attr)
        key_val = "-".join(all_attr)
        text_type_data.append((text_type, key_val))

    # grouping all duplicate types
    # data at this point looks like this - {2.5mm Arial Narrow ***: [texttype1, texttype2, texttype3]}
    data_dict = {}
    for row in text_type_data:
        text_type, key_name = row
        if key_name not in data_dict:
            data_dict[key_name] = [text_type]
        else:
            data_dict[key_name].append(text_type)

    # creating class TextType and TextNoteInstance objects and putting into list
    text_types_keep = []
    text_types_delete = []
    for _, val in data_dict.items():
        if len(val) <= 1:  # if len of val is less than or equal to 1 then there are no duplicate types and nothing needs to be replaced or touched so we skip it
            continue
        for idx, text_type in enumerate(val):
            if idx == 0:  # we are keep texttype at index 0 of every dict
                text_type_var = projectfunctions.create_var_from_string(GetParameter.get_type_name(text_type), TextType, text_type)
                # text_types.append(text_type_var)
                text_types_keep.append(text_type_var)
                text_type_keep = text_type
            else:
                text_type_var = projectfunctions.create_var_from_string(GetParameter.get_type_name(text_type), TextType, text_type)
                text_type_var.purge = True
                text_type_var.updated_text_type = text_type_keep
                text_types_delete.append(text_type_var)

    all_groups_placed = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_IOSDetailGroups).WhereElementIsNotElementType()

    # getting one group instance per group type
    group_instances_filtered = {}
    for group in all_groups_placed:
        if group.GroupType.Id in group_instances_filtered:
            pass
        group_instances_filtered[group.GroupType.Id] = group
    for group in list(group_instances_filtered.values()):
        Groups.group_find_replace_type(group, text_types_delete)

    # get all text instances not in group and change there types to correct one
    # check if there type is in text_types_delete and if so change there type to replacement one
    all_text_type_id_delete = [tt.text_type_id() for tt in text_types_delete]
    all_text_instances = Selection.GetElementsFromDoc.all_text(doc, elements_only=True)
    all_text_instances_no_group = [t for t in all_text_instances if str(t.GroupId) == "-1"]
    for t_instance in all_text_instances_no_group:
        if t_instance.TextNoteType.Id in all_text_type_id_delete:
            t_type = text_types_delete[all_text_type_id_delete.index(t_instance.TextNoteType.Id)]
            Groups.change_elements_type(t_instance, t_type.updated_text_type.Id)

    # deleting duplicate text types
    for text_type in text_types_delete:
        with db.Transaction("Delete text type"):
            doc.Delete(text_type.text_type_id())

    # renaming text types
    all_text_types_updated = DB.FilteredElementCollector(doc).OfClass(DB.TextNoteType)
    for text_type in all_text_types_updated:
        correct_text_type_name = TextNoteType.text_type_name(text_type)
        with db.Transaction("Set text type name"):
            text_type.Name = correct_text_type_name

if __name__ == "__main__":
    main()

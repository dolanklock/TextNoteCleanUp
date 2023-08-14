import clr
clr.AddReferenceByPartialName('PresentationCore')
clr.AddReferenceByPartialName('AdWindows')
clr.AddReferenceByPartialName("PresentationFramework")
clr.AddReferenceByPartialName('System')
clr.AddReferenceByPartialName('System.Windows.Forms')

from Autodesk.Revit import DB
from Autodesk.Revit import UI
import Autodesk
import Autodesk.Windows as aw
from pyrevit import forms
from rpw import db
from GetSetParameters import *
from System.Collections.Generic import List

uiapp = __revit__
uidoc = uiapp.ActiveUIDocument
doc = uiapp.ActiveUIDocument.Document


# CODE BELOW HERE #


def change_elements_type(element, type_id):
    """

    Args:
        element:
        type: (ElementId) the id of the type

    Returns: (ElementId) changed elements element id

    """
    with db.Transaction("change text type in group"):
        element_id = element.ChangeTypeId(type_id)
    return element_id


def get_group_member_ids(group):
    """

    Args:
        group:

    Returns:

    """
    member_ids = group.GetMemberIds()
    return member_ids


def create_group(element_ids):
    """

    Args:
        element_ids: (ElementId) list of element ids of elements to group

    Returns: (Group) the new group

    """
    e_list = List[DB.ElementId]()
    for e_id in element_ids:
        e_list.Add(e_id)
    with db.Transaction("Creating new group"):
        new_group = doc.Create.NewGroup(e_list)
    return new_group


def get_group_instances_of_type(group_type_id):
    """

    Args:
        group_type_id:

    Returns:

    """
    all_groups_collector = DB.FilteredElementCollector(doc).OfClass(DB.Group)
    all_groups_of_type = [g for g in all_groups_collector if g.GetTypeId() == group_type_id]
    return all_groups_of_type


def point_delta(point_1, point_2):
    """_summary_

    Args:
        point_1 (tuple[str]): _description_
        point_2 (tuple[str]): _description_

    Returns:
        XYZ: delta of two points given as DB.XYZ object
    """
    point_delta_x = point_1.X - point_2.X
    point_delta_y = point_1.Y - point_2.Y
    point_delta_z = point_1.Z - point_2.Z
    return DB.XYZ(point_delta_x, point_delta_y, point_delta_z)


def group_find_replace_type(group, text_types):
    """
    Replaces element type of specified type to be changed with new type specified. Will ungroup the group instance of
    the group provided, collect all of the members that were in that group and then find and replace the types. Then
    it will create a new group and rename the old group and give the new group the old group name and find and switch
    all old group instances type to the new group type and then delete the old group
    Args:
        group: (DB.Group) the group to seach and replace text types in
        text_types: (TextType object (class in main script))

    Returns:

    """
    member_ids = get_group_member_ids(group)
  
    elements = []
    for id in member_ids:
        elements.append(doc.GetElement(id))

    # checking if groups contain text notes
    group_contains_text_notes = False
    for element in elements:
        if isinstance(element, DB.TextNote):
            group_contains_text_notes = True

    if group_contains_text_notes:
        # ungroup the group instance
        old_group_type = group.GroupType
        with db.Transaction("ungroup group"):
            group.UngroupMembers()

        # iterate through the elements list and find and change type for elements
        # for text_type in text_types:
        for idx, element in enumerate(elements):
            for text_type in text_types:
                if element is not None:
                    if element.GetTypeId() == text_type.text_type_id():
                        element_id = change_elements_type(element, text_type.updated_text_type.Id)
                        elements[idx] = doc.GetElement(element_id)  # replacing old element in list with new one

        # rename the old group
        old_group_name = GetParameter.get_type_name(old_group_type)
        with db.Transaction("Set group name"):
            old_group_type.Name = "{}-OLD".format(old_group_name)

        # create new group with updated members with same name as old one
        new_group = create_group(member_ids)
        new_group_type = new_group.GroupType

        # change new group type name
        with db.Transaction("Change group name"):
            new_group_type.Name = old_group_name

        # change the old group instances to new group type
        all_old_group_instances = get_group_instances_of_type(old_group_type.Id)
    
        for idx, group in enumerate(all_old_group_instances):
            if idx == 0:
                # going through groups members and getting text note and recording its location
                # so i know how much to move by for all instances of that group type
                member_ids_group = get_group_member_ids(group)
                for i in member_ids_group:
                    if isinstance(doc.GetElement(i), DB.TextNote):
                        text = doc.GetElement(i).Text
                        member_location_original = doc.GetElement(i).Coord
                        break
                # changing old groups type to new group type
                change_elements_type(group, new_group_type.Id)
                
                member_ids_group_updated = get_group_member_ids(group)

                # getting the same groups members after group type change so that i can get the same
                # textnote location i recorded above and get the difference in location of
                # old group position to new position
                for i in member_ids_group_updated:
                    if isinstance(doc.GetElement(i), DB.TextNote):
                        text_new = doc.GetElement(i).Text
                        if text_new == text:
                            member_location_new = doc.GetElement(i).Coord
                            break
            else:
                change_elements_type(group, new_group_type.Id)
            
            # getting delta of the two locations of textnote in the group before type change and after
            delta = point_delta(member_location_original, member_location_new)
        
            # changing position of group instance back from distance moved from origin change
            xyz = DB.XYZ(delta[0], delta[1], delta[2])
            with db.Transaction("Move group"):
                group.Location.Move(xyz)
      
        # deleting old group type
        with db.Transaction("Delete group"):
            doc.Delete(old_group_type.Id)

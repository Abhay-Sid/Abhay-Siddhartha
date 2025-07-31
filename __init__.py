import bpy
import json
import os
from collections import OrderedDict
from bpy.types import Operator, Panel, Menu
from bpy.props import StringProperty, BoolProperty

# _________________________ META DATA __________________________
bl_info = {
    "name": "Abhay's Toolkit",
    "author": "Abhay Siddhartha",
    "description": "Custom nodes in both Add menu and UI Panel",
    "blender": (4, 2, 8),
    "version": (0, 9, 22),
    "location": "Geometry Nodes Editor > Add & UI",
    "warning": "Restart Blender after disabling",
    "category": "Node"
}

#____________________ global variables
global is_nodes_dict_empty, empty_dict_warnning, NODES_DICT, NODE_NAMES, NODES_DESC

#___________variables for nodes dictionary
NODES_DICT = OrderedDict()  # entire nodes data with node names and descriptions, will be imported from json file
NODE_NAMES = OrderedDict()                       # a dicttionary of node categories and nodes of each categories, categorie names are keys and lists of node names are values.
NODE_DESC = OrderedDict()             # a dicttionary of node categories and nodes descriptions of each categories, categorie names are keys and lists of node descriptions are values.
is_nodes_dict_empty = False      # a boolean variable to check if nodes dictionary is empty or not
empty_dict_warnning = "Nodes Dictionary is empty or not readable!"                      # a warning message to be printed if nodes dictionary is empty or not readable

dir_path = os.path.dirname(__file__)

# _________________________ CORE OPERATOR __________________________
class NODE_OT_ADD_CUSTOM_GROUP(Operator):
    """Operator to append and add node group"""
    bl_idname = "node.add_abhay_group"
    bl_label = "Add Custom Node Group"
    bl_options = {'REGISTER', 'UNDO'}
    
    group_name: StringProperty(name="Group Name")               # type:ignore
    display_name: StringProperty(name="Display Name")           # type: ignore
    description: StringProperty(name="Description")                    # type: ignore

    @classmethod
    def description(cls, context, props):
        return props.description if props.description else "No description available"
    
    def invoke(self, context, event):
        
        # region = context.region
        # rv3d = context.region_data
        # space = context.space_data
        
        # #  calculate node editor position from mouse position
        # if hasattr(space, 'region_to_view'):
        #     self.cursor_pos = space.region_to_view(event.mouse_region_x, event.mouse_region_y)
        # else:
        #     # Fallback for older Blender versions
        #     self.cursor_pos = context.space_data.cursor_location.copy()
        
        area = next((a for a in context.window.screen.areas if a.type == 'NODE_EDITOR'), None)
        if not area:
            return self.execute(context)
        
        region = next((r for r in area.regions if r.type == 'WINDOW'), None)
        if not region:
            return self.execute(context)
            
        space = area.spaces.active   #space node editor
        
        # convert global mouse to region local
        mouse_x = event.mouse_x - region.x
        mouse_y = event.mouse_y - region.y
        
        #convert region-local mouse to node editor manulally
        v2d = region.view2d
        self.cursor_pos = (
            v2d.region_to_view(mouse_x, mouse_y)
        )
        
        return self.execute(context)

    def execute(self, context):
        blend_file = next((f for f in os.listdir(dir_path) if f.endswith(".blend")), None)
        if not blend_file:
            self.report({'ERROR'}, "No .blend file found")
            return {'CANCELLED'}
            
        blend_path = os.path.join(dir_path, blend_file)
        
        try:
            # Append node group if needed
            if self.group_name not in bpy.data.node_groups:
                with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
                    if self.group_name in data_from.node_groups:
                        data_to.node_groups = [self.group_name]
                    else:
                        self.report({'ERROR'}, f"Node group '{self.group_name}' not found")
                        return {'CANCELLED'}

            # Add node at cursor position
            bpy.ops.node.add_node(type='GeometryNodeGroup')
            node = context.selected_nodes[-1]
            #use calculated position
            node.location = self.cursor_pos
            node.node_tree = bpy.data.node_groups[self.group_name]
            node.label = self.display_name
            node.use_custom_color = True
            node.color = (0.6, 0.6, 0.6)
            
            # Start transform from stored position
            bpy.ops.transform.translate('INVOKE_DEFAULT')
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Error: {str(e)}")
            return {'CANCELLED'}

# _________________________ PANEL UI __________________________
class NODE_PT_ABHAY_TOOLKIT_PANEL(Panel):
    bl_label = "Abhay's Toolkit"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Abhay's Toolkit"

    @classmethod
    def poll(cls, context):
        return context.space_data.tree_type == 'GeometryNodeTree'

    def draw(self, context):
        layout = self.layout
        for category, nodes in NODE_NAMES.items():
            if not nodes:
                continue
                
            box = layout.box()
            row = box.row()
            prop_name = f"show_{category.lower().replace(' ', '_')}_nodes"
            show_state = getattr(context.scene, prop_name, False)
            
            row.prop(context.scene, prop_name, 
                    text=category, 
                    icon='DISCLOSURE_TRI_DOWN' if show_state else 'DISCLOSURE_TRI_RIGHT',
                    emboss=False)
            
            if show_state:
                col = box.column(align=True)
                for node_name, node_desc in zip(nodes, NODE_DESC[category]):
                    op = col.operator(NODE_OT_ADD_CUSTOM_GROUP.bl_idname, text=node_name, icon='NODE')
                    op.group_name = node_name
                    op.display_name = node_name
                    op.description = node_desc
                box.separator()

# _________________________ ADD MENU INTEGRATION __________________________
def add_menu_draw(self, context):
    if NODE_NAMES:
        layout = self.layout
        layout.separator()
        layout.menu('NODE_MT_ABHAY_MAIN_MENU', text="Abhay's Toolkit", icon='NODETREE')

class NODE_MT_ABHAY_MAIN_MENU(Menu):
    bl_label = "Abhay's Toolkit"
    bl_idname = 'NODE_MT_ABHAY_MAIN_MENU'

    def draw(self, context):
        # Maintain JSON order for categories
        for category in NODE_NAMES.keys():
            self.layout.menu(f"NODE_MT_ABHAY_{category.replace(' ', '_')}", text=category)

def create_category_menus():
    for category, nodes in NODE_NAMES.items():
        # Factory function to capture current category
        def make_draw_func(current_category):
            def draw_func(self, context):
                layout = self.layout
                for node_name, node_desc in zip(NODE_NAMES[current_category], NODE_DESC[current_category]):
                    op = layout.operator(NODE_OT_ADD_CUSTOM_GROUP.bl_idname, text=node_name, icon = 'NODE')
                    op.group_name = node_name
                    op.display_name = node_name
                    op.description = node_desc.strip()
            return draw_func

        menu_class = type(
            f"NODE_MT_ABHAY_{category.replace(' ', '_')}",
            (Menu,),
            {
                "bl_label": category,
                "bl_idname": f"NODE_MT_ABHAY_{category.replace(' ', '_')}",
                "draw": make_draw_func(category)
            }
        )
        bpy.utils.register_class(menu_class)

# _________________________ UTILITIES __________________________

#____________________ function to import nodes dictionary from json file
def imp_nodes_dictionary():
    global NODES_DICT, is_nodes_dict_empty , empty_dict_warnning

    dir_path = os.path.dirname(__file__)

    with open(os.path.join(dir_path, "nodes_dictionary.json"), 'r') as f:
        
        try:                                       #____ a fallsafe if nodes dictionary is not found or empty, but if nodes dictional have even a empty dictionary ({}), it will be considered as not empty
            NODES_DICT = json.loads(f.read())
            check_nodes_dict_empty()                 # and thats why i created this secondary fallsafe to check if nodes dictionary has a empty dictionary or not 
            if is_nodes_dict_empty == True:           # if yes then raise an error
                print(empty_dict_warnning)                                      
            return  NODES_DICT                        # if not then rerturn the nodes dictionary
            
        except ValueError:
            print(empty_dict_warnning)
            is_path_dict_empty = True
            
            return  is_path_dict_empty 

# _______________________ new function to load node data with new nodes_dictionary json file
def load_node_data():   
    global NODES_DICT, is_nodes_dict_empty, empty_dict_warnning, NODE_NAMES, NODE_DESC
    
    imp_nodes_dictionary()   # im import the entire nodes dictionary from json file as 'nodes_dictionary' here
    
    category_names = list(NODES_DICT.keys())   # list of categories for easy access to its length
    NODE_NAMES = OrderedDict()   # emptying the node_names dictionary
    NODE_DESC = OrderedDict()       # emptying the node_descriptions dictionary
    
    for i in range(len(category_names)):       #    iterating through the categories and creating filling the dictionaries of node names and descriptions.
        NODE_NAMES[category_names[i]] = list(NODES_DICT[category_names[i]].keys())
        NODE_DESC[category_names[i]] = list(NODES_DICT[category_names[i]].values())
    
    # print(NODE_NAMES, "\n \n", NODE_DESC)  # printing the node names and descriptions for debugging purposes
    
    return NODE_DESC, NODE_NAMES, NODES_DICT, is_nodes_dict_empty


# __________________________________ dictional secondary fallsafe to prevent empty nodes dictionary
def check_nodes_dict_empty():
    
    global is_nodes_dict_empty
    
    with open(os.path.join(os.path.dirname(__file__), "nodes_dictionary.json"), 'r') as f:
        
        try:
            temp = json.loads(f.read())
            
            if temp == {} or temp == None or temp == "":
                is_nodes_dict_empty = True
            else:
                is_nodes_dict_empty = False
            return 
            
        except ValueError:   
            is_nodes_dict_empty = True
        
        return is_nodes_dict_empty
    pass



# _________________________ REGISTRATION __________________________
def register():
    load_node_data()
    
    bpy.utils.register_class(NODE_OT_ADD_CUSTOM_GROUP)
    bpy.utils.register_class(NODE_PT_ABHAY_TOOLKIT_PANEL)
    bpy.utils.register_class(NODE_MT_ABHAY_MAIN_MENU)
    
    create_category_menus()
    bpy.types.NODE_MT_add.append(add_menu_draw)
    
    for category in NODE_NAMES.keys():
        prop_name = f"show_{category.lower().replace(' ', '_')}_nodes"
        if not hasattr(bpy.types.Scene, prop_name):
            setattr(bpy.types.Scene, prop_name, bpy.props.BoolProperty(default=False))

def unregister():
    bpy.types.NODE_MT_add.remove(add_menu_draw)
    bpy.utils.unregister_class(NODE_OT_ADD_CUSTOM_GROUP)
    bpy.utils.unregister_class(NODE_PT_ABHAY_TOOLKIT_PANEL)
    bpy.utils.unregister_class(NODE_MT_ABHAY_MAIN_MENU)
    
    for category in NODE_NAMES.keys():
        menu_class = getattr(bpy.types, f"NODE_MT_ABHAY_{category.replace(' ', '_')}", None)
        if menu_class:
            bpy.utils.unregister_class(menu_class)
    
    for category in NODE_NAMES.keys():
        prop_name = f"show_{category.lower().replace(' ', '_')}_nodes"
        if hasattr(bpy.types.Scene, prop_name):
            delattr(bpy.types.Scene, prop_name)

if __name__ == "__main__":
    register()
import bpy, bmesh, os
from bpy.types import Operator
from .definitions import SelectObject, FocusObject, ActivateObject, DuplicateObject, DuplicateObjects, DeleteObject, MoveObject, MoveObjects, CheckSuffix, CheckPrefix, CheckForTags, RemoveTags
from mathutils import Vector

class GT_Export_Assets(Operator):
    """Updates the origin point based on the option selected, for all selected objects"""

    bl_idname = "scene.gx_export"
    bl_label = "Export"

    def ExportFBX(self, filePath, applyModifiers, meshSmooth, objectTypes, useAnim, useAnimAction, useAnimOptimise):

        print("Exporting", "*"*70)
        bpy.ops.export_scene.fbx(check_existing=False,
        filepath=filePath,
        filter_glob="*.fbx",
        version='BIN7400',
        use_selection=True,
        global_scale=self.globalScale,
        axis_forward=self.axisForward,
        axis_up=self.axisUp,
        bake_space_transform=self.bakeSpaceTransform,
        object_types=objectTypes,
        use_mesh_modifiers=applyModifiers,
        mesh_smooth_type=meshSmooth,
        use_mesh_edges=False,
        use_tspace=False,
        use_armature_deform_only=True,
        add_leaf_bones=False,
        bake_anim=useAnim,
        bake_anim_use_all_bones=useAnim,
        bake_anim_use_nla_strips=False,
        bake_anim_use_all_actions=useAnimAction,
        use_anim=useAnim,
        use_anim_action_all=useAnimAction,
        use_default_take=False,
        use_anim_optimize=useAnimOptimise,
        anim_optimize_precision=6.0,
        path_mode='AUTO',
        embed_textures=False,
        batch_mode='OFF',
        use_batch_own_dir=False,
        use_metadata=False)

    def PrepareExportIndividual(self, context, targets, path, suffix, applyModifiers, meshSmooth, exportTypes, exportAnim):
        print(">>> Individual Pass <<<")
        for item in targets:
            print("-"*70)
            print("Exporting...... ", item.name)
            individualFilePath = path + item.name + suffix + ".fbx"

            # For the time being, manually move the object back and forth to
            # the world origin point.
            tempLoc = Vector((0.0, 0.0, 0.0))
            tempLoc[0] = item.location[0]
            tempLoc[1] = item.location[1]
            tempLoc[2] = item.location[2]
            print("Moving location to centre...")
            MoveObject(item, context, (0.0, 0.0, 0.0))

            bpy.ops.object.select_all(action='DESELECT')
            FocusObject(item)

            self.ExportFBX(individualFilePath, applyModifiers, meshSmooth, exportTypes, True, True, True)

            print("Moving location back to root-orientated centre...")
            MoveObject(item, context, tempLoc)
            print("Location..........", item.location)

        if exportAnim is True:
            print("Exporting separate animation files...")

    def PrepareExportCombined(self, targets, path, exportName, suffix, applyModifiers, meshSmooth, exportTypes, exportAnim):
        print(">>> Exporting Combined Pass <<<")
        print("Checking export preferences...")

        bpy.ops.object.select_all(action='DESELECT')

        for item in targets:
            print("Exporting: ", item.name)
            print(item.name, "has export set to", item.GXObj.enable_export)
            SelectObject(item)

        objectFilePath = path + exportName + suffix + ".fbx"

        export_anim = False
        export_anim_actions = False
        export_anim_optimise = False

        if exportAnim is True:
            print("Exporting animations...")
            export_anim = True
            export_anim_actions = True
            export_anim_optimise = True

            #if expLP is False and expHP is False and expCG is False and expCX is False:
                #if expAR is True:
                    #exportTypes = {'ARMATURE'}

        self.ExportFBX(objectFilePath, applyModifiers, meshSmooth, exportTypes, export_anim, export_anim_actions, export_anim_optimise)

    def AddTriangulate(self, object):

        modType = {'TRIANGULATE'}

        for modifier in object.modifiers:
            print("Looking for modifier...")
            if modifier.type in modType:
                print("Already found triangulation.")
                return True

        FocusObject(object)
        bpy.ops.object.modifier_add(type='TRIANGULATE')

        for modifier in object.modifiers:
            if modifier.type in modType:
                print("Triangulation Found")
                modifier.quad_method = 'FIXED_ALTERNATE'
                modifier.ngon_method = 'CLIP'
                return False

        print("No modifier found, triangulation failed.")

    def RemoveTriangulate(self, object):

        modType = {'TRIANGULATE'}
        FocusObject(object)

        for modifier in object.modifiers:
            if modifier.type in modType:
                bpy.ops.object.modifier_remove(modifier=modifier.name)


    def GetFilePath(self, context, locationEnum, fileName):
        # Get the file extension.  If the index is incorrect (as in, the user didnt set the fucking path)
        scn = context.scene.GXScn
        enumIndex = int(locationEnum)
        filePath = ""

        enumIndex -= 1
        defaultFilePath = scn.location_defaults[enumIndex].path
        print("Obtained location default: ", scn.location_defaults[enumIndex].path)

        if defaultFilePath == "":
            return {'2'}

        if defaultFilePath.find('//') != -1:
            return {'3'}

        filePath = defaultFilePath

        return filePath


    def CalculateFilePath(self, context, locationDefault, objectName, sub_directory, useObjectDirectory):

        # Does the proper calculation and error handling for the file path, in conjunction with GetFilePath()
        print("Obtaining File...")
        print("File Enumerator = ", locationDefault)
        path = self.GetFilePath(context, locationDefault, objectName)

        if path == "":
            self.report({'WARNING'}, "Welp, something went wrong.  Contact Crocadillian! D:.")
            return {'CANCELLED'}

        if path == {'1'}:
            self.report({'WARNING'}, 'One of the objects has no set file path default.  Set it plzplzplz.')
            return {'CANCELLED'}

        if path == {'2'}:
            self.report({'WARNING'}, 'One of the objects file path default has no file path.  A file path is required to export.')
            return {'CANCELLED'}

        if path == {'3'}:
            self.report({'WARNING'}, 'One of the objects file path default is using a relative file path name, please tick off the Relative Path option when choosing the file path.')
            return {'CANCELLED'}

        print("Current Path: ", path)

        # //////////// - FILE DIRECTORY - ///////////////////////////////////////////
        # Need to extract the information from the pass name to see
        # if a sub-directory needs creating in the location default
        if sub_directory != "" or useObjectDirectory is True:

            if useObjectDirectory is True:
                newPath = path + objectName + "/"

            if sub_directory != "":
                newPath = newPath + sub_directory + "/"

            print(">>> Sub-Directory found, appending...")

            if not os.path.exists(newPath):
                os.makedirs(newPath)

            print("Old Path: ", path)
            path = newPath
            print("New Path: ", path)

        return path

    def IdentifyTag(self, context, target):

        rootType = 0

        if CheckSuffix(target.name, self.addon_prefs.lp_tag) is True:
            rootType = 1
        elif CheckSuffix(target.name, self.addon_prefs.hp_tag) is True:
            rootType = 2
        elif CheckSuffix(target.name, self.addon_prefs.cg_tag) is True:
            rootType = 3
        elif CheckSuffix(target.name, self.addon_prefs.cx_tag) is True:
            rootType = 4

        return rootType

    def GetNormals(self, enum):

        if enum == '1':
            return 'EDGE'
        if enum == '2':
            return 'FACE'
        if enum == '3':
            return 'OFF'


    def execute(self, context):
        print("Self = ")
        print(self)

        scn = context.scene.GXScn
        user_preferences = context.user_preferences
        self.addon_prefs = user_preferences.addons[__package__].preferences

        exportedObjects = 0
        exportedGroups = 0
        exportedPasses = 0

        # Keep a record of the selected and active objects to restore later
        active = None
        selected = []
        for sel in context.selected_objects:
            if sel.name != context.active_object.name:
                selected.append(sel)
        active = context.active_object


        # Generate export details based on the export type selected
        self.axisForward = "-Z"
        self.axisUp = "Y"
        self.globalScale = 1.0
        self.bakeSpaceTransform = False


        # //////////// - ENGINE PROPERTIES - ////////////////////////////////////////////////////////
        # Assign custom properties based on the export target
        if int(scn.engine_select) is 1:
            print("UE4 selected")
            self.axisForward = "-Z"
            self.axisUp = "Y"
            self.globalScale = 1.0

        elif int(scn.engine_select) is 2:
            print("Unity selected")
            self.axisForward = "-Z"
            self.axisUp = "Y"
            self.globalScale = 1
            self.bakeSpaceTransform = True


        bpy.ops.object.mode_set(mode='OBJECT')

        # OBJECT CYCLE
        ###############################################################
        ###############################################################
        # Cycle through the available objects
        for object in context.scene.objects:
            if object.type == 'MESH':
                print("Object", object.name, "found.")

                if object.GXObj.enable_export is True:

                    print("-"*109)
                    print("NEW JOB", "-"*100)
                    print("-"*109)

                    #Get the export default for the object
                    expKey = int(object.GXObj.export_default) - 1

                    if expKey == -1:
                        statement = "The selected object " + object.name + " has no export default selected.  Please define!"
                        FocusObject(object)
                        self.report({'WARNING'}, statement)
                        return {'FINISHED'}


                    exportDefault = self.addon_prefs.export_defaults[expKey]
                    useObjectDirectory = exportDefault.use_sub_directory

                    rootObject = object
                    rootType = self.IdentifyTag(context, rootObject)


                    print("Root Type is...", rootType)

                    rootObjectLocation = Vector((0.0, 0.0, 0.0))
                    rootObjectLocation[0] = object.location[0]
                    rootObjectLocation[1] = object.location[1]
                    rootObjectLocation[2] = object.location[2]

                    # Collect hidden defaults to restore afterwards.
                    hiddenList = []
                    selectList = []
                    hiddenObjectList = []
                    objectName = RemoveTags(context, rootObject.name)

                    # ////////  FINDING ARMATURE ////////
                    armatureTarget = None
                    modType = {'ARMATURE'}

                    # If the root object is the low-poly object, we can export the armature with it.
                    if rootType == 1:
                        armatureTarget = rootObject

                    elif CheckForTags(context, rootObject.name) is False and rootType == 0:
                        armatureTarget = rootObject

                    print(">>> Armature Target is..")
                    print(armatureTarget)

                    if armatureTarget is not None:
                        FocusObject(armatureTarget)

                        for modifier in armatureTarget.modifiers:
                            if modifier.type in modType:
                                print(">>> Armature found...")
                                armature = modifier.object

                    for objPass in exportDefault.passes:

                        print("-"*109)
                        print("NEW PASS", "-"*100)
                        print("-"*109)
                        print("Export pass", objPass.name, "being used on object", object.name)

                        lowPoly = None
                        highPoly = None
                        cage = None
                        collision = []
                        animation = None
                        armature = None

                        collisionNames = []

                        # Obtain some object-specific preferences
                        applyModifiers = objPass.apply_modifiers
                        useTriangulate = objPass.triangulate
                        exportIndividual = objPass.export_individual
                        hasTriangulation = False
                        meshSmooth = self.GetNormals(rootObject.GXObj.normals)
                        exportTypes = {'MESH', 'ARMATURE'}

                        # Obtain Object Component Information
                        expLP = objPass.export_lp
                        expHP = objPass.export_hp
                        expCG = objPass.export_cg
                        expCX = objPass.export_cx
                        expAR = objPass.export_ar
                        expAM = objPass.export_am
                        expRoot = False

                        export_anim = False
                        export_anim_actions = False
                        export_anim_optimise = False

                        # Also set file path name
                        path = ""                                # Path given from the location default
                        fileName = ""                            # File name for the object (without tag suffixes)
                        suffix = objPass.file_suffix             # Additional file name suffix
                        sub_directory = objPass.sub_directory    # Whether a sub-directory needs to be created
                        objectName = ""                          # The object name, duh

                        # Lets see if the root object can be exported...
                        if rootType == 0:
                            expRoot = True
                        elif expLP is True and rootType == 1:
                            expRoot = True
                        elif expHP is True and rootType == 2:
                            expRoot = True
                        elif expCG is True and rootType == 3:
                            expRoot = True
                        elif expCX is True and rootType == 4:
                            expRoot = True



                        #/////////////////// - FILE NAME - /////////////////////////////////////////////////
                        objectName = RemoveTags(context, rootObject.name)
                        print("objectName =", objectName)
                        path = self.CalculateFilePath(context, rootObject.GXObj.location_default, objectName, sub_directory, useObjectDirectory)


                        #/////////////////// - FIND OBJECTS - /////////////////////////////////////////////////
                        # First we have to find all objects in the group that are of type MESHHH
                        # If auto-assignment is on, use the names to filter into lists, otherwise forget it.

                        print(">>>> Collecting Objects <<<<")

                        # If the root type is 0, no associating objects should be searchable
                        if rootType != 0:
                            print(">>>> Tags On, searching... <<<")
                            if bpy.data.objects.find(objectName + self.addon_prefs.lp_tag) != -1 and expLP is True:
                                item = bpy.data.objects[objectName + self.addon_prefs.lp_tag]

                                if item.type == 'MESH':
                                    if item != rootObject or rootType != 1:
                                        print("LP Found...", item.name)
                                        lowPoly = item
                                        hiddenObjectList.append(item)
                                        isHidden = item.hide
                                        hiddenList.append(isHidden)
                                        isSelectable = item.hide_select
                                        selectList.append(isSelectable)


                            if bpy.data.objects.find(objectName + self.addon_prefs.hp_tag) != -1 and expHP is True:
                                item = bpy.data.objects[objectName + self.addon_prefs.hp_tag]

                                if item.type == 'MESH':
                                    if item != rootObject or rootType != 2:
                                        print("HP Found...", item.name)
                                        highPoly = item
                                        hiddenObjectList.append(item)
                                        isHidden = item.hide
                                        hiddenList.append(isHidden)
                                        isSelectable = item.hide_select
                                        selectList.append(isSelectable)

                            if bpy.data.objects.find(objectName + self.addon_prefs.cg_tag) != -1 and expCG is True:
                                item = bpy.data.objects[objectName + self.addon_prefs.cg_tag]

                                if item.type == 'MESH':
                                    if item != rootObject or rootType != 3:
                                        print("CG Found...", item.name)
                                        cage = item
                                        hiddenObjectList.append(item)
                                        isHidden = item.hide
                                        hiddenList.append(isHidden)
                                        isSelectable = item.hide_select
                                        selectList.append(isSelectable)

                            # As there can be multiple collision objects, a full search has to be conducted.
                            for item in bpy.data.objects:
                                if item.type == 'MESH':
                                    if item != rootObject:
                                        if CheckPrefix(item.name, objectName + self.addon_prefs.cx_tag) is True and expCX is True:
                                            print("Cage has correct tags...")

                                            print("CX Found...", item.name)
                                            collision.append(item)
                                            hiddenObjectList.append(item)
                                            isHidden = item.hide
                                            hiddenList.append(isHidden)
                                            isSelectable = item.hide_select
                                            selectList.append(isSelectable)


                        # We have to collect the armature from the modifier stack
                        # This is the only component that can be searched for if the rootType has no tags
                        modType = {'ARMATURE'}

                        if expAR is True:
                            item = None

                            if rootType == 1 or rootType == 0:
                                item = rootObject

                            elif lowPoly is not None:
                                item = lowPoly

                            if item is not None:
                                FocusObject(item)

                                for modifier in item.modifiers:
                                    if modifier.type in modType:
                                        armature = modifier.object

                                        hiddenObjectList.append(item)
                                        isHidden = armature.hide
                                        hiddenList.append(isHidden)
                                        isSelectable = armature.hide_select
                                        selectList.append(isSelectable)


                                        # Ensure all armatures are in Object Mode for following code
                                        bpy.ops.object.select_all(action='DESELECT')
                                        FocusObject(armature)
                                        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
                                        bpy.ops.object.select_all(action='DESELECT')


                        # Debug check for found objects
                        print("Checking found objects...")
                        if expLP is True:
                            print("LP...", rootObject)
                        if expHP is True:
                            print("HP...", highPoly)
                        if expCG is True:
                            print("CG...", cage)
                        if expCX is True:
                            print("CX...", collision)
                        if expAR is True:
                            print("AR...", armature)


                        # //////////// - COLLISION SETUP - /////////////////////////////////////
                        # ////////////////////////////////////////////////////////////
                        # //////////////////////////////////////////////////////////////////////
                        # Now we know what objects are up for export, we just need to prepare them
                        # If UE4 is used and we have collision, bundle the collision with the export
                        if expCX is True and int(scn.engine_select) is 1:
                            print("UE4 being used, preparing collision...")
                            if len(collision) != 0:

                                print("Still here?")
                                i = 1

                                for item in collision:

                                    p = "_"
                                    if i < 10:
                                        p = "_0"

                                    collisionNames.append(item.name)
                                    item.name = "UCX_" + rootObject.name + p + str(i)
                                    i += 1

                                    print("Collision name...", item.name)


                        # /////////// - OBJECT MOVEMENT - ///////////////////////////////////////////////////
                        # ///////////////////////////////////////////////////////////////////////////////////
                        print(">>> Collecting Found Objects <<<")
                        exportList = []

                        if rootType != 0:
                            print("Auto Assign on, searching...")

                            if expLP is True and lowPoly is not None and rootType != 1:
                                print("Appending LP")
                                exportList.append(lowPoly)

                            if expHP is True and highPoly is not None and rootType != 2:
                                print("Appending HP")
                                exportList.append(highPoly)

                            if expCG is True and cage is not None and rootType != 3:
                                print("Appending CG")
                                exportList.append(cage)

                            if expCX is True and collision is not None and rootType != 4:
                                print("Appending CX")
                                exportList += collision

                            if expAR is True and armature is not None:
                                print("Appending AR")
                                exportList.append(armature)

                            MoveObjects(rootObject, exportList, context, (0.0, 0.0, 0.0))

                        else:
                            MoveObject(rootObject, context, (0.0, 0.0, 0.0))

                        print(">>> Asset List Count...", len(exportList))


                        # /////////// - MODIFIERS - ///////////////////////////////////////////////////
                        # ////////////////////////////////////////////////////////////////////////////
                        print(">>> Triangulating Objects <<<")
                        triangulateList = []
                        triangulateList += exportList

                        if expLP is True:
                            triangulateList.append(rootObject)

                        if useTriangulate is True and applyModifiers is True:
                            for item in triangulateList:
                                if item.type == 'MESH':
                                    print("Triangulating Mesh...", item.name)
                                    stm = item.GXStm
                                    hasTriangulation = False
                                    hasTriangulation = self.AddTriangulate(item)
                                    stm.has_triangulate = hasTriangulation


                        # //////////// - EXPORT PROCESS - ///////////////////////////////////////////
                        # A separate FBX export function call for every corner case isnt actually necessary
                        finalExportList = []
                        finalExportList += exportList

                        if expRoot is True:
                            finalExportList.append(rootObject)

                        if exportIndividual is True:
                            self.PrepareExportIndividual(context, finalExportList, path, suffix, applyModifiers, meshSmooth, exportTypes, expAM)

                        else:
                            nameTagless = RemoveTags(context, objectName)

                            self.PrepareExportCombined(finalExportList, path, suffix, nameTagless, applyModifiers, meshSmooth, exportTypes, expAM)


                        # /////////// - DELETE/RESTORE - ///////////////////////////////////////////////////
                        # ///////////////////////////////////////////////////////////////////////////////////
                        if expCX is True and scn.engine_select is '1':
                            if len(collision) is not 0:
                                i = 0
                                for item in collision:
                                    item.name = collisionNames[i]
                                    i += 1

                        # Remove any triangulation modifiers
                        if useTriangulate is True and applyModifiers is True:
                            for item in triangulateList:
                                if item.type == 'MESH':
                                    if item.GXStm.has_triangulate is False:
                                        print("Object has created triangulation, remove it.")
                                        self.RemoveTriangulate(item)

                        # Reset and move objects
                        for item in exportList:
                            print("Checking ", item.name)
                            print("Checking object position... ", item.location)

                        if rootType != 0:
                            MoveObjects(rootObject, exportList, context, rootObjectLocation)

                        else:
                            MoveObject(rootObject, context, rootObjectLocation)

                        exportedPasses += 1
                        print(">>> Pass Complete <<<")


                    # Restore visibility defaults
                    i = 0

                    print("hiddenList...", len(hiddenList))
                    print("selectList...", len(selectList))

                    for item in hiddenObjectList:
                        item.hide = hiddenList[i]
                        item.hide_select = selectList[i]
                        i += 1

                    # Count up exported objects
                    exportedObjects += 1
                    print(">>> Object Export Complete <<<")





        # Now hold up, its group time!
        for group in bpy.data.groups:
            if group.GXGrp.export_group is True:

                print("-"*79)
                print("NEW JOB", "-"*70)
                print("-"*79)

                # Before we do anything, check that a root object exists
                hasRootObject = False
                rootObject = None
                rootType = 0

                if group.GXGrp.root_object == "":
                    statement = "No name has been given to the " + group.name + " group object, please give it a name."
                    self.report({'WARNING'}, statement)
                    return {'FINISHED'}

                for object in group.objects:
                    if object.name == group.GXGrp.root_object:
                        hasRootObject = True
                        rootObject = object

                if rootObject == None:
                    hasRootObject = False

                if rootObject == None:
                    statement = "The group object " + group.name + " has no valid root object.  Ensure the root object exists in the group."
                    self.report({'WARNING'}, statement)
                    return {'FINISHED'}


                #Get the export default for the object
                expKey = int(group.GXGrp.export_default) - 1

                if expKey == -1:
                    statement = "The group object " + group.name + " has no export default selected.  Please define!"
                    self.report({'WARNING'}, statement)
                    return {'FINISHED'}

                exportDefault = self.addon_prefs.export_defaults[expKey]
                useObjectDirectory = exportDefault.use_sub_directory
                print("Using Export Default...", exportDefault.name, ".  Export Key", expKey)


                # Identify what tag the root object has
                rootType = self.IdentifyTag(context, rootObject)
                print("Root type is...", rootType)


                rootObjectLocation = Vector((0.0, 0.0, 0.0))
                rootObjectLocation[0] = rootObject.location[0]
                rootObjectLocation[1] = rootObject.location[1]
                rootObjectLocation[2] = rootObject.location[2]


                # Collect hidden defaults to restore afterwards.
                hiddenList = []
                selectList = []
                for item in group.objects:
                    isHidden = item.hide
                    hiddenList.append(isHidden)

                    isSelectable = item.hide_select
                    selectList.append(isSelectable)

                for objPass in exportDefault.passes:

                    print("-"*59)
                    print("NEW PASS", "-"*50)
                    print("-"*59)
                    print("Export pass", objPass.name, "being used on the group", group.name)
                    print("Root object.....", rootObject.name)

                    completeList = []
                    lowPolyList = []
                    highPolyList = []
                    cageList = []
                    collisionList = []
                    animationList = []
                    armatureList = []

                    collisionNames = []

                    # Obtain some object-specific preferences
                    applyModifiers = objPass.apply_modifiers
                    useTriangulate = objPass.triangulate
                    exportIndividual = objPass.export_individual
                    hasTriangulation = False
                    meshSmooth = self.GetNormals(rootObject.GXObj.normals)
                    exportTypes = {'MESH', 'ARMATURE'}

                    # Obtain Object Component Information
                    expLP = objPass.export_lp
                    expHP = objPass.export_hp
                    expCG = objPass.export_cg
                    expCX = objPass.export_cx
                    expAR = objPass.export_ar
                    expAM = objPass.export_am
                    expRoot = False

                    export_anim = False
                    export_anim_actions = False
                    export_anim_optimise = False

                    # Also set file path name
                    path = ""
                    filePath = ""
                    objectFilePath = ""
                    suffix = objPass.file_suffix
                    sub_directory = objPass.sub_directory

                    # Lets see if the root object can be exported...
                    if expLP is True and rootType == 1:
                        expRoot = True
                    if expHP is True and rootType == 2:
                        expRoot = True
                    if expCG is True and rootType == 3:
                        expRoot = True
                    if expCX is True and rootType == 4:
                        expRoot = True
                    if rootType == 0:
                        expRoot = True

                    # If its a collision object...
                    if expCG is True and rootType == 3:
                        collisionName = rootObject.name
                        collisionName = collisionName.replace(self.addon_prefs.cx_tag, "")
                        foundMatch = False

                        for item in group.objects:
                            if item.name == collisionName + self.addon_prefs.lp_tag:
                                foundMatch = True

                        if foundMatch is False:
                            self.report({'WARNING'}, "Collision object used as root does not have a corresponding low-poly object, abort!")
                            FocusObject(rootObject)
                            return {'CANCELLED'}



                    #/////////////////// - FILE NAME - /////////////////////////////////////////////////
                    objectName = group.name
                    path = self.CalculateFilePath(context, group.GXGrp.location_default, objectName, sub_directory, useObjectDirectory)




                    #/////////////////// - FIND OBJECTS - /////////////////////////////////////////////////
                    # First we have to find all objects in the group that are of type MESHHH
                    # If auto-assignment is on, use the names to filter into lists, otherwise forget it.

                    print(">>>> Collecting Objects <<<<")

                    if rootType == 0:
                        print("Auto Assign off, collecting all group objects....")
                        for item in group.objects:
                            if item.name != rootObject.name:
                                if item.type == 'MESH' or item.type == 'ARMATURE':
                                    print("Collected", item.name, "...")
                                    completeList.append(item)

                        print("Collected", len(completeList), "objects.")

                    else:
                        print("Auto Assign on, collecting group objects....")
                        for item in group.objects:
                            print("Group Object...", item.name)
                            if item != rootObject:
                                if item.type == 'MESH':

                                    # Sorts based on name suffix
                                    if CheckSuffix(item.name, self.addon_prefs.lp_tag) is True and expLP is True:
                                        if item.name != rootObject.name or rootType != 1:
                                            print("LP Found...", item.name)
                                            lowPolyList.append(item)

                                    elif CheckSuffix(item.name, self.addon_prefs.hp_tag) is True and expHP is True:
                                        if item.name != rootObject.name or rootType != 2:
                                            print("HP Found...", item.name)
                                            highPolyList.append(item)

                                    elif CheckSuffix(item.name, self.addon_prefs.cg_tag) is True and expCG is True:
                                        if item.name != rootObject.name or rootType != 3:
                                            print("CG Found...", item.name)
                                            cageList.append(item)

                                elif item.type == 'ARMATURE' and expAR is True:
                                    print("Collected armature,", item.name, "...")
                                    armatureList.append(item)

                        # Collision objects are only added if it can find a name match with a static mesh
                        if expCX is True:
                            i = 1

                            for target in lowPolyList:
                                if target.type == 'MESH':
                                    searchName = RemoveTags(context, target.name)

                                    for item in group.objects:
                                        if item.name != target.name:
                                            if item.type == 'MESH':
                                                if CheckPrefix(item.name, searchName + self.addon_prefs.cx_tag) is True:
                                                    print("CX found...", item.name)
                                                    collisionList.append(item)

                                                    if int(scn.engine_select) is 1:
                                                        p = "_"
                                                        if i < 10:
                                                            p = "_0"

                                                        collisionNames.append(item.name)
                                                        print("item name.......,", item.name)
                                                        tempName = RemoveTags(context, item.name)
                                                        print("tempName.........", tempName)
                                                        item.name = "UCX_" + target.name + p + str(i)
                                                        i += 1

                                                        print("Collision name...", item.name)


                            if rootType == 1:
                                searchName = RemoveTags(context, rootObject.name)

                                for item in group.objects:
                                    if item.name != rootObject.name:
                                        if item.type == 'MESH':
                                            if CheckPrefix(item.name, searchName + self.addon_prefs.cx_tag) is True:
                                                print("CX found...", item.name)
                                                collisionList.append(item)

                                                # Names have to be processed here so the object names that the collision is
                                                # associated with can be matched.
                                                if int(scn.engine_select) is 1:
                                                    p = "_"
                                                    if i < 10:
                                                        p = "_0"

                                                    collisionNames.append(item.name)
                                                    print("item name.......,", item.name)
                                                    tempName = RemoveTags(context, item.name)
                                                    print("tempName.........", tempName)
                                                    item.name = "UCX_" + rootObject.name + p + str(i)
                                                    i += 1

                                                    print("Collision name...", item.name)



                    print("Total low_poly....", len(lowPolyList))
                    print("Total high_poly...", len(highPolyList))
                    print("Total cage........", len(cageList))
                    print("Total collision...", len(collisionList))
                    print("Total armatures...", len(armatureList))



                    # /////////// - OBJECT MOVEMENT - ///////////////////////////////////////////////////
                    # ///////////////////////////////////////////////////////////////////////////////////
                    print(">>> Appending Found Objects <<<")

                    exportList = []
                    if rootType != 0:
                        if expLP is True:
                            print("Appending LP...")
                            exportList += lowPolyList

                        if expHP is True:
                            print("Appending HP...")
                            exportList += highPolyList

                        if expCG is True:
                            print("Appending CG...")
                            exportList += cageList

                        if expCX is True:
                            print("Appending CX...")
                            exportList += collisionList

                        if expAR is True:
                            print("Appending AM...")
                            exportList += armatureList

                    else:
                        exportList += completeList

                    print("ExportList.....", exportList)

                    MoveObjects(rootObject, exportList, context, (0.0, 0.0, 0.0))

                    # /////////// - MODIFIERS - ///////////////////////////////////////////////////
                    # ////////////////////////////////////////////////////////////////////////////
                    print(">>> Triangulating Objects <<<")
                    triangulateList = []
                    triangulateList += exportList

                    if expLP is True or rootType == 0:
                        triangulateList.append(rootObject)

                    if useTriangulate is True and applyModifiers is True:
                        for item in triangulateList:
                            if item.type == 'MESH':
                                print("Triangulating Mesh...", item.name)
                                stm = item.GXStm
                                hasTriangulation = False
                                hasTriangulation = self.AddTriangulate(item)
                                stm.has_triangulate = hasTriangulation


                    # /////////// - EXPORT - ///////////////////////////////////////////////////
                    # ///////////////////////////////////////////////////////////////////////////////////
                    print(">>>> Exporting Objects <<<<")
                    bpy.ops.object.select_all(action='DESELECT')

                    canExport = True
                    print("Root Location...", rootObject.location)

                    if len(exportList) == 0 and expRoot is False:
                        print("No objects found in pass, stopping export...")
                        canExport = False


                    elif canExport is True:
                        finalExportList = []
                        finalExportList += exportList

                        if expRoot is True:
                            finalExportList.append(rootObject)

                        if exportIndividual is True:
                            self.PrepareExportIndividual(context, finalExportList, path, suffix, applyModifiers, meshSmooth, exportTypes, expAM)

                        else:
                            self.PrepareExportCombined(finalExportList, path, suffix, group.name, applyModifiers, meshSmooth, exportTypes, expAM)


                    # /////////// - DELETE/RESTORE - ///////////////////////////////////////////////////
                    # ///////////////////////////////////////////////////////////////////////////////////
                    if expCX is True and scn.engine_select is '1':
                        if len(collisionList) is not 0:
                            i = 0
                            for item in collisionList:
                                item.name = collisionNames[i]
                                i += 1

                    # Remove any triangulation modifiers
                    if useTriangulate is True and applyModifiers is True:
                        for object in triangulateList:
                            if object.type == 'MESH':
                                if object.GXStm.has_triangulate is False:
                                    print("Object has created triangulation, remove it.")
                                    self.RemoveTriangulate(object)

                    print("Checking", object.name, "'s position... ",rootObject.location)
                    for object in exportList:
                        print("Checking", object.name, "'s position... ", object.location)



                    MoveObjects(rootObject, exportList, context, rootObjectLocation)

                    exportedPasses += 1
                    print(">>> Pass Complete <<<")

                # Restore visibility defaults
                i = 0
                for item in group.objects:
                    item.hide = hiddenList[i]
                    item.hide_select = selectList[i]
                    i += 1

                i = 0

                exportedGroups += 1
                print(">>> Group Export Complete <<<")


        # Re-select the objects previously selected
        if active is not None:
            FocusObject(active)

        for sel in selected:
            SelectObject(sel)

        textGroupSingle = " group"
        textGroupMultiple = " groups"
        dot = "."

        output = "Finished exporting "

        if exportedObjects > 1:
            output += str(exportedObjects) + " objects"
        elif exportedObjects == 1:
            output += str(exportedObjects) + " object"

        if exportedObjects > 0 and exportedGroups > 0:
            output += " and "

        if exportedGroups > 1:
            output += str(exportedGroups) + " groups"
        elif exportedGroups == 1:
            output += str(exportedGroups) + " group"

        output += ".  "

        output += "Total of "

        if exportedPasses > 1:
            output += str(exportedPasses) + " passes."
        elif exportedPasses == 1:
            output += str(exportedPasses) + " pass."

        # Output a nice report
        if exportedObjects == 0 and exportedGroups == 0:
            self.report({'WARNING'}, 'No objects were exported.  Ensure any objects tagged for exporting are enabled.')

        else:
            self.report({'INFO'}, output)


        return {'FINISHED'}

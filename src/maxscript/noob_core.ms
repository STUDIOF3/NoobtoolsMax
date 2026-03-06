struct NoobToolsCore (
    fn getSupportedMapClasses = 
    (
        local types = #(
            #(BitmapTexture, "filename"),
            #(VRayBitmap, "HDRIMapName"),
            #(VRayBitmap, "filename"),
            #(CoronaBitmap, "filename"),
            #(ai_Image, "filename"),
            #(OSLMap, "filename"),
            #(PhysicalMaterial, "base_color"),
            #(Redshift_Bitmap, "filename"),
            #(FStormBitmap, "filename"),
            #(FStormTexture, "filename")
        )
        return types
    ),

    fn guessRenderer filepath = (
        local ext = getFilenameType filepath
        if (toLower ext) != ".max" do return "N/A"
        
        local isVRay = false
        local isCorona = false
        local isFStorm = false
        local isArnold = false
        
        try (
            local meta = getMAXFileAssetMetadata filepath
            if meta != undefined do (
                for m in meta do (
                    try (
                        local cName = m.className as string
                        if matchPattern cName pattern:"*VRay*" do isVRay = true
                        if matchPattern cName pattern:"*Corona*" do isCorona = true
                        if matchPattern cName pattern:"*FStorm*" do isFStorm = true
                        if matchPattern cName pattern:"*Arnold*" do isArnold = true
                    ) catch()
                )
            )
        ) catch()
        
        local lowPath = toLower filepath
        if not isVRay and (matchPattern lowPath pattern:"*vray*" or matchPattern lowPath pattern:"*v-ray*") do isVRay = true
        if not isCorona and (matchPattern lowPath pattern:"*corona*") do isCorona = true
        if not isFStorm and (matchPattern lowPath pattern:"*fstorm*") do isFStorm = true
        
        if isVRay and isCorona do return "V-Ray & Corona"
        if isVRay do return "V-Ray"
        if isCorona do return "Corona Render"
        if isFStorm do return "FStorm"
        if isArnold do return "Arnold"
        return "Unknown"
    ),

    fn selectObjectsFromMissing pathString = 
    (
        if pathString == undefined or pathString == "" do return false
        local foundMats = #()
        local types = getSupportedMapClasses()
        for t in types do (
            try (
                local instances = getClassInstances t[1]
                for m in instances do (
                    if isProperty m t[2] do (
                        local val = getProperty m t[2]
                        if val == pathString do appendIfUnique foundMats m
                    )
                )
            ) catch()
        )
        local finalObjs = #()
        for m in foundMats do (
            local deps = refs.dependents m
            for d in deps do (
                if isValidNode d and not isDeleted d do appendIfUnique finalObjs d
            )
        )
        if finalObjs.count > 0 then (
            clearSelection()
            select finalObjs
            redrawViews()
            return finalObjs.count
        ) else (
            return 0
        )
    ),

    fn convertToUNC = 
    (
        local count = 0
        local types = getSupportedMapClasses()
        for t in types do (
            try (
                local instances = getClassInstances t[1]
                for m in instances do (
                    if isProperty m t[2] do (
                        local val = getProperty m t[2]
                        if val != undefined and val != "" and (matchPattern val pattern:"*:") do (
                            local unc = pathConfig.convertPathToUnc val
                            if unc != undefined and unc != val do (
                                setProperty m t[2] unc
                                count += 1
                            )
                        )
                    )
                )
            ) catch()
        )
        return count
    ),

    fn stripMissingPaths missingList = 
    (
        local count = 0
        local types = getSupportedMapClasses()
        for t in types do (
            try (
                local maps = getClassInstances t[1]
                for m in maps do (
                    if isProperty m t[2] do (
                        local val = getProperty m t[2]
                        if (findItem missingList val) > 0 and (not doesFileExist val) do (
                            setProperty m t[2] ""
                            count += 1
                        )
                    )
                )
            ) catch()
        )
        return count
    ),

    fn getMissingAssets =
    (
        local mList = #()
        if (classOf ATSOps) != undefined do (
            try (
                ATSOps.Refresh()
                local allAssets = #()
                ATSOps.GetFiles &allAssets
                for f in allAssets do (
                    if f != undefined and f != "" do (
                        local statusArray = ATSOps.GetFileSystemStatus f
                        local isMissing = false
                        if statusArray != undefined do (
                            for s in statusArray do if s == #missing do isMissing = true
                        )
                        if not isMissing and not (doesFileExist f) do isMissing = true
                        if isMissing do appendIfUnique mList f
                    )
                )
            ) catch()
        )
        return mList
    ),
    fn cleanScene = (
        local stats = #(0, 0, 0) -- layers, materials, groups
        -- 1. Layers vazios
        for i = LayerManager.count - 1 to 1 by -1 do (
            local lay = LayerManager.getLayer i
            local nodes = #()
            lay.nodes &nodes
            if nodes.count == 0 do (
                LayerManager.deleteLayerByName lay.name
                stats[1] += 1
            )
        )
        -- 2. Groups Vazios
        local emptyGroups = for o in helpers where isGroupHead o and o.children.count == 0 collect o
        for g in emptyGroups do ( delete g; stats[3] += 1 )
        stats
    ),

    fn checkSceneScale = (
        local unitsType = units.SystemType as string
        local scaleFactor = units.SystemScale
        #(unitsType, scaleFactor)
    ),

    fn rescaleSelection factor = (
        if selection.count > 0 do (
            scale selection [factor, factor, factor]
            true
        )
    ),

    fn collectFiles targetDir = (
        local count = 0
        local types = getSupportedMapClasses()
        if not (doesDirectoryExist targetDir) do makeDir targetDir
        
        local allMaps = #()
        for t in types do (
            local instances = getClassInstances t[1]
            for m in instances do (
                if isProperty m t[2] do (
                    local p = getProperty m t[2]
                    if p != undefined and p != "" and (doesFileExist p) do appendIfUnique allMaps #(m, t[2], p)
                )
            )
        )
        
        for mData in allMaps do (
            local oldP = mData[3]
            local fName = filenameFromPath oldP
            local newP = targetDir + "\\" + fName
            if not (doesFileExist newP) then (
                if (copyFile oldP newP) do (
                    setProperty mData[1] mData[2] newP
                    count += 1
                )
            ) else (
                setProperty mData[1] mData[2] newP
                count += 1
            )
        )
        count
    ),

    fn forcePivotToBottom o = (
        if isValidNode o do (
            local bb = nodeGetBoundingBox o (matrix3 1)
            local bmin = bb[1]; local bmax = bb[2]
            o.pivot = [(bmin.x + bmax.x) / 2.0, (bmin.y + bmax.y) / 2.0, bmin.z]
        )
    ),

    fn addSelectionToLayer layerName = (
        local layerObj = LayerManager.getLayerFromName layerName
        if layerObj == undefined do layerObj = LayerManager.newLayerFromName layerName
        layerObj.addNodes selection
        OK
    ),

    fn renameSelection prefix suffix = (
        for o in selection do o.name = prefix + o.name + suffix
        OK
    ),

    fn renderMaterialPreview matPath matName outputFile = (
        try (
            local matLib = loadTempMaterialLibrary matPath
            if matLib == undefined or matLib.count == 0 do return false
            local mat = matLib[matName]
            if mat == undefined do mat = matLib[1]
            if mat == undefined do return false
            
            -- DETECT COMPATIBILITY
            local matClass = classOf mat as string
            local isThirdParty = matchPattern matClass pattern:"*Corona*" or \
                                 matchPattern matClass pattern:"*VRay*" or \
                                 matchPattern matClass pattern:"*FStorm*" or \
                                 matchPattern matClass pattern:"*Arnold*"
            
            local oldRenderer = renderers.current
            local changedRenderer = false
            
            if not isThirdParty then (
                renderers.current = Default_Scanline_Renderer()
                changedRenderer = true
            ) else (
                -- Se for 3rd party, tentamos garantir que o renderizador atual é compatível
                -- Se o usuário está usando Corona, mas o mat é VRay, vai dar erro.
                -- Por enquanto, apenas usamos o atual e tentamos baixar a qualidade.
                try (
                    if matchPattern (classOf renderers.current as string) pattern:"*Corona*" do (
                        renderers.current.progressive_maxPasses = 5 -- Muito rápido
                        renderers.current.progressive_maxTime = 2
                    )
                    if matchPattern (classOf renderers.current as string) pattern:"*VRay*" do (
                        renderers.current.output_on = false -- Preview mode se existir
                    )
                ) catch()
            )
            
            local s = sphere radius:25 pos:[0,0,0] segments:64
            s.material = mat
            local l1 = omniLight pos:[120,-120,150] intensity:1.0 rgb:white
            local l2 = omniLight pos:[-150,80,50] intensity:0.4 rgb:(color 200 220 255)
            
            local tempCam = Freecamera pos:[0,-95,30] name:"TempPreviewCam"
            tempCam.target = s
            
            -- Render settings
            local oldVFB = renderSceneDialog.isOpen()
            if oldVFB do renderSceneDialog.close()
            
            render camera:tempCam outputfile:outputFile width:160 height:140 vfb:off quiet:true
            
            delete s
            delete l1
            delete l2
            delete tempCam
            
            if changedRenderer do renderers.current = oldRenderer
            true
        ) catch (
            false
        )
    )
)

global NoobToolsCoreInst = NoobToolsCore()

(	
	clearListener()
	format "--- Iniciando Instalacao NoobTools Modular ---\n"
	
	local tempFolder = ( getDir #temp )+ "\\NoobTools_Install_Temp"
	local userScripts = getDir #userScripts
	local installDir = userScripts + "\\NoobViz"
	
	if not( doesDirectoryExist installDir ) do makeDir installDir
	
	-- Copiar a pasta src inteira
	local sourceSrcFolder = tempFolder + "\\src"
	local destSrcFolder = installDir + "\\src"
	
	local xcopyCmd = "xcopy /E /Y /I /Q \"" + sourceSrcFolder + "\" \"" + destSrcFolder + "\""
	HiddenDOSCommand xcopyCmd
	
	local destFile = installDir + "\\src\\main.py"
	
	if( doesFileExist destFile ) then
	(
		format "Script copiado com sucesso para: %\n" destFile
		
		-- GERAR ICONE
		local iconDir = getDir #userIcons
		local iconFile = iconDir + "\\NoobViz_24i.bmp"
		if( doesFileExist iconFile ) do deleteFile iconFile
		
		local bmp = bitmap 24 24 filename:iconFile color:( color 35 35 35 )
		local cBlue = ( color 0 122 204 )
		for x = 0 to 23 do ( setPixels bmp[0, x] #( cBlue ); setPixels bmp[x, 0] #( cBlue ); setPixels bmp[23, x] #( cBlue ); setPixels bmp[x, 23] #( cBlue ) )
		for y = 5 to 18 do ( for x = 5 to 18 do setPixels bmp[x, y] #( cBlue ) )
		save bmp; close bmp
		
		-- REGISTRAR MACRO
		local macroContent = ""
		macroContent += "macroScript NoobTools\n"
		macroContent += "category:\"NoobViz\"\n"
		macroContent += "tooltip:\"NoobTools Suite\"\n"
		macroContent += "icon:#(\"NoobViz\", 1)\n"
		macroContent += "(\n"
		macroContent += "    on execute do (\n"
		macroContent += "        local f = @\"" + destFile + "\"\n"
		macroContent += "        if doesFileExist f then (\n"
		macroContent += "            local pluginPath = getFileNamePath f\n"
		macroContent += "            local srcRoot = substring pluginPath 1 (pluginPath.count - 5)\n"
		macroContent += "            -- Convertendo barras para formato seguro do Python\n"
		macroContent += "            srcRoot = substituteString srcRoot \"\\\\\" \"/\"\n"
		macroContent += "            local pyCmd = \"import sys\\n\"\n"
		macroContent += "            pyCmd += \"if '\" + srcRoot + \"' not in sys.path:\\n\"\n"
		macroContent += "            pyCmd += \"    sys.path.insert(0, '\" + srcRoot + \"')\"\n"
		macroContent += "            python.Execute pyCmd\n"
		macroContent += "            python.ExecuteFile f\n"
		macroContent += "        ) else messageBox \"Arquivo principal nao encontrado! Reinstale.\" title:\"Erro\"\n"
		macroContent += "    )\n"
		macroContent += ")"
		try (			
			execute macroContent
			messageBox "Instalacao Concluida!\n\n1. Va em Customize > Customize User Interface\n2. Toolbars > Category: NoobViz\n3. Arraste o botao para a barra." title: "Sucesso"
		) catch ( messageBox( "Erro ao criar botao: " + getCurrentException() ) )
	)
	else
	(		
		local msg = "ERRO: Nao foi possivel encontrar os arquivos extraidos.\n"
		messageBox msg title: "Falha na Instalacao"
	)
)
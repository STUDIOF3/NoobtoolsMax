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
		
		-- LIMPEZA DE VERSÕES ANTIGAS
		local oldMacro = ( getDir #userMacros ) + "\\NoobViz-NoobTools.mcr"
		if( doesFileExist oldMacro ) do ( try( deleteFile oldMacro ) catch() )
		
		-- GERAR ICONE (Garantir 24-bit e caminho correto)
		local iconDir = getDir #userIcons
		if not ( doesDirectoryExist iconDir ) do makeDir iconDir
		local iconFile = iconDir + "\\NoobViz_24i.bmp"
		if( doesFileExist iconFile ) do deleteFile iconFile
		
		local bmp = bitmap 24 24 filename:iconFile color:( color 35 35 35 )
		local cBlue = ( color 0 122 204 )
		-- Desenha um simples "N" estilizado ou quadrado azul para o icone
		for y = 0 to 23 do (
			for x = 0 to 23 do (
				if (x < 2 or x > 21 or y < 2 or y > 21) then setPixels bmp [x,y] #(cBlue)
				else if (x == y or x == (y-1) or x == (y+1)) then setPixels bmp [x,y] #(cBlue)
			)
		)
		save bmp; close bmp
		
		-- REGISTRAR MACRO
		local macroContent = ""
		macroContent += "macroScript NoobTools\n"
		macroContent += "category:\"NoobViz\"\n"
		macroContent += "tooltip:\"NoobTools Suite\"\n"
		macroContent += "buttonText:\"NoobTools\"\n"
		macroContent += "icon:#(\"NoobViz\", 1)\n"
		macroContent += "(\n"
		macroContent += "    on execute do (\n"
		macroContent += "        local f = @\"" + destFile + "\"\n"
		macroContent += "        if doesFileExist f then (\n"
		macroContent += "            local pluginPath = getFileNamePath f\n"
		macroContent += "            local srcRoot = substring pluginPath 1 (pluginPath.count - 5)\n"
		macroContent += "            srcRoot = substituteString srcRoot \"\\\\\" \"/\"\n"
		macroContent += "            local pyCmd = \"import sys\\n\"\n"
		macroContent += "            pyCmd += \"if '\" + srcRoot + \"' not in sys.path:\\n\"\n"
		macroContent += "            pyCmd += \"    sys.path.insert(0, '\" + srcRoot + \"')\"\n"
		macroContent += "            python.Execute pyCmd\n"
		macroContent += "            python.ExecuteFile f\n"
		macroContent += "        ) else messageBox \"Arquivo principal nao encontrado! Reinstale.\" title:\"Erro\"\n"
		macroContent += "    )\n"
		macroContent += ")"
		
		execute macroContent
		
		-- ADICIONAR NA RIBBON
		try (
			local ribbon = animatable.getNames #mainRibbon
			-- Lógica simplificada para adicionar na Ribbon via CommandPanel ou Custom UI
			-- No MaxScript moderno usamos o menuMan ou ribbon helpers
			python.Execute "import pymxs; rt = pymxs.runtime; rt.macros.run('NoobViz', 'NoobTools')"
			
			format "Macro registrada e pronta para uso.\n"
		) catch()

		messageBox "Instalacao Concluida!\n\n1. O botão foi registrado na categoria 'NoobViz'.\n2. Se não aparecer na Ribbon automaticamente, você pode adicionar em Customize User Interface." title: "Sucesso"
	)
	else
	(		
		local msg = "ERRO: Nao foi possivel encontrar os arquivos extraidos.\n"
		messageBox msg title: "Falha na Instalacao"
	)
)
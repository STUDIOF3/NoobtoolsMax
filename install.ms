(	
	clearListener()
	format "--- Iniciando Instalação NoobTools v3 ---\n"
	-- 1. DEFINIR A ORIGEM 
	local tempFolder = ( getDir #temp )+ "\\NoobTools_Install_Temp"
	local scriptName = "NoobTools_Main.py"
	local sourceFile = tempFolder + "\\" + scriptName
	-- 2. DEFINIR O DESTINO
	local userScripts = getDir #userScripts
	local installDir = userScripts + "\\NoobViz"
	local destFile = installDir + "\\" + scriptName
	-- 3. VERIFICAR E INSTALAR
	if( doesFileExist sourceFile ) then
	(		
		-- Criar pasta
		if not( doesDirectoryExist installDir ) do
			makeDir installDir
		-- Remover versão antiga
		if doesFileExist destFile do
			deleteFile destFile
		-- Copiar o arquivo
		copyFile sourceFile destFile
		format "Script copiado com sucesso para: %\n" destFile
		-- 4. GERAR ÍCONE (CORRIGIDO: filename inserido na criação)
		local iconDir = getDir #userIcons
		local iconFile = iconDir + "\\NoobViz_24i.bmp"
		-- Deletar ícone antigo se existir
		if( doesFileExist iconFile ) do
			deleteFile iconFile
		-- AQUI ESTAVA O ERRO: Adicionei "filename:iconFile"
		local bmp = bitmap 24 24 filename: iconFile color:( color 35 35 35 )
		local cBlue = ( color 0 122 204 )
		-- Desenha bordas
		for x = 0 to 23 do
		(			
			setPixels bmp[0, x] #( cBlue )
			setPixels bmp[x, 0] #( cBlue )
			setPixels bmp[23, x] #( cBlue )
			setPixels bmp[x, 23] #( cBlue )
		)
		-- Preenche o centro
		for y = 5 to 18 do
		(			
			for x = 5 to 18 do
				setPixels bmp[x, y] #( cBlue )
		)
		save bmp -- Agora ele sabe onde salvar!
		close bmp
		format "Ícone criado em: %\n" iconFile
		-- 5. REGISTRAR MACRO
		local macroContent = ""
		macroContent += "macroScript NoobTools\n"
		macroContent += "category:\"NoobViz\"\n"
		macroContent += "tooltip:\"NoobTools Suite v3\"\n"
		macroContent += "icon:#(\"NoobViz\", 1)\n"
		macroContent += "(\n"
		macroContent += "    on execute do (\n"
		macroContent += "        local f = @\"" + destFile + "\"\n"
		macroContent += "        if doesFileExist f then python.ExecuteFile f\n"
		macroContent += "        else messageBox \"Arquivo principal deletado!\" title:\"Erro\"\n"
		macroContent += "    )\n"
		macroContent += ")"
		try
		(			
			execute macroContent
			messageBox "Instalação Concluída!\n\n1. Vá em Customize > Customize User Interface\n2. Toolbars > Category: NoobViz\n3. Arraste o botão para a barra." title: "Sucesso"
		)
		catch
		(			
			messageBox( "Erro ao criar botão: " + getCurrentException() )
		)
	)
	else
	(		
		local msg = "ERRO: Não foi possível encontrar o arquivo de origem.\n"
		msg += "O instalador esperava encontrar o arquivo em:\n" + sourceFile
		messageBox msg title: "Falha na Instalação"
	)
)
extends SceneTree
var failures: int = 0
var checks: int = 0

func check(condition: bool, message: String) -> void:
	checks += 1
	if not condition:
		failures += 1
		push_error(message)

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	print("Vérification : initialisation")
	root.size = Vector2i(1440, 900)
	root.content_scale_size = Vector2i(1440, 900)
	var desktop: Control = load("res://scenes/desktop.tscn").instantiate()
	root.add_child(desktop)
	for i: int in range(3): await process_frame
	check(desktop.apps.size() == 13, "Treize applications du bureau avec le lecteur audio")
	check(desktop.workspace_buttons.size() == 4, "Quatre espaces de travail")
	for app_name: String in desktop.apps:
		check(desktop.apps[app_name].min_size.x >= 380, "Taille minimale : " + app_name)
	desktop.session.handle = "TestOperator"
	desktop.session.contracts = [{"contract_id": "test", "title": "Contrat de test", "body": "Description", "forum": "breachboard", "client": {"handle": "client", "forum_rep": 50, "account_age_days": 412}, "reward": 300, "tier": 0, "unlocked": true}]
	desktop._render_board()
	print("Vérification : fenêtres et espaces de travail")
	desktop._open("Terminal")
	check(desktop.apps.Terminal.visible, "Ouverture du terminal")
	check(desktop.tasks.has("Terminal"), "Tâche visible dans le panneau Xfce")
	var frame: Control = desktop.apps.Terminal
	var original: Rect2 = Rect2(frame.position, frame.size)
	frame.toggle_maximize()
	check(frame.maximized, "Maximisation")
	check(frame.position.y == 32, "Le panneau supérieur reste dégagé")
	check(frame.size.x == desktop.size.x, "Largeur maximisée")
	frame.toggle_maximize()
	check(frame.position == original.position and frame.size == original.size, "Restauration de la géométrie")
	frame.minimize_window()
	check(not frame.visible and frame.opened and frame.minimized_state, "Réduction sans fermeture")
	check(desktop.tasks.has("Terminal"), "Une fenêtre réduite conserve sa tâche")
	desktop._open("Terminal")
	check(frame.visible and not frame.minimized_state, "Restauration depuis la barre des tâches")
	desktop._switch_workspace(1)
	check(not frame.visible, "Les fenêtres du premier bureau sont masquées")
	desktop._open("Chordly")
	check(desktop.apps.Chordly.workspace == 1, "Nouvelle fenêtre sur le bureau courant")
	desktop._switch_workspace(0)
	check(frame.visible and not desktop.apps.Chordly.visible, "Retour au premier bureau")
	desktop._toggle_desktop()
	check(not frame.visible, "Afficher le bureau")
	desktop._toggle_desktop()
	check(frame.visible, "Restaurer les fenêtres du bureau")
	desktop._show_menu()
	check(desktop._applications.visible, "Menu d'applications")
	desktop._application_search.text = "messagerie"
	desktop._render_applications()
	check(desktop._application_list.get_child_count() == 2, "Recherche Telegrid / Sessyon")
	desktop._applications.hide()
	desktop._update_state({"tick": 1, "max_ticks": 40, "discovered": ["h1"], "scanned": [], "hosts": [{"id": "h1", "hostname": "H1", "ip": "10.0.0.1", "status": "HEALTHY", "services": []}], "messages": [{"sender": "client", "channel": "chordly", "tick": 1, "text": "Message de test"}], "loot": [], "history": [], "alerts": [], "contract": {"client": "client"}, "available_abilities": {"red": []}})
	check(desktop.messengers.chordly.message_text().contains("Message de test"), "Messages affichés")
	check(desktop.network.get_root().get_child_count() == 1, "Réseau découvert")
	check(desktop.route_label.text.contains("tick 1/40"), "État de la route dans le centre d'opération")
	print("Vérification : messageries")
	var messenger: Control = desktop.messengers.telegrid
	messenger.set_identity("TestOperator")
	var message: Dictionary = {"id": "m1", "sender": "relay", "peer": "relay", "text": "Message Telegrid", "time": "12:00"}
	messenger.add_message(message)
	messenger.add_message(message)
	check(messenger.messages.size() == 1, "Déduplication des messages")
	check(messenger.unread == 1, "Compteur non lu")
	check(not desktop.messengers.chordly.message_text().contains("Message Telegrid"), "Conversations séparées par service")
	messenger._select_peer("relay")
	check(messenger._header_avatar.get_child(0).text == "R", "Avatar du contact sélectionné")
	check(messenger._identity_avatar.get_child(0).text == "T", "Avatar du joueur")
	check(messenger.unread == 0, "Lecture des messages")
	var sent: Array = []
	messenger.send_message.disconnect(desktop._send_message)
	messenger.send_message.connect(func(channel: String, text: String) -> void: sent.append([channel, text]))
	messenger.composer.text = "Bien reçu."
	messenger._send()
	check(sent == [["telegrid", "Bien reçu."]], "Envoi depuis le compositeur")
	messenger.acknowledge(true)
	check(messenger.composer.text.is_empty(), "Compositeur vidé après confirmation")
	print("Vérification : forums")
	var forum: Control = desktop.forum_view
	forum.navigate("exployt")
	check(not forum.lock_reason().is_empty(), "Forum avancé verrouillé")
	forum.profile = {"tier": 2, "route": "tor"}
	forum.render()
	check(forum.lock_reason().is_empty(), "Forum accessible par Tor au bon palier")
	forum.navigate("breachboard", "test", "Contrats")
	check(forum._reply != null and is_instance_valid(forum._reply), "Page de sujet et réponse rapide")
	var replies: Array = []
	forum.reply_requested.connect(func(id: String, text: String) -> void: replies.append([id, text]))
	forum._reply.text = "Intéressé."
	forum._submit_reply()
	check(replies == [["test", "Intéressé."]], "Publication depuis un sujet")
	forum.set_replies("test", [{"author": "TestOperator", "reputation": 10, "text": "Intéressé."}])
	check(forum.replies.test.size() == 1, "Réponses affichées dans le sujet")
	forum.navigate("breachboard", "", "Discussion")
	forum._browse_history(-1)
	check(forum.selected_thread == "test", "Navigation arrière du navigateur")
	print("Vérification : fichiers et terminal")
	desktop.files.navigate("/home/operator")
	check(desktop.files._items.item_count == 4, "Dossiers du gestionnaire de fichiers")
	desktop.files.set_loot([{"username": "user", "type": "NTLM_HASH", "value": "123456", "valid": true}])
	desktop.files.navigate("/home/operator/loot")
	check(desktop.files._items.item_count == 1, "Fichiers du butin")
	desktop.files._select(0)
	check(desktop.files._preview.text.contains("123456"), "Lecture d'un fichier virtuel")
	desktop.files.back()
	check(desktop.files.path == "/home/operator", "Historique du gestionnaire")
	desktop.terminal_views.main.history.assign(["whoami", "ip addr"])
	desktop.terminal_views.main.history_index = 2
	var up: InputEventKey = InputEventKey.new()
	up.keycode = KEY_UP
	up.pressed = true
	desktop._terminal_key(up)
	check(desktop.terminal_input.text == "ip addr", "Historique du terminal")
	desktop._new_terminal()
	var second: String = "term-%s" % desktop.console_counter
	check(desktop.terminal_views.size() == 2, "Deux consoles simultanées")
	desktop._console_output(second, ["sortie deuxième console"])
	check(desktop.terminal_views[second].output.get_parsed_text().contains("sortie deuxième console"), "Sortie ciblée")
	check(not desktop.terminal.get_parsed_text().contains("sortie deuxième console"), "Sorties isolées")
	desktop._console_context(second, {"user": "remote", "cwd": "/srv", "hostname": "server", "password_prompt": true})
	check(desktop.terminal_views[second].input.secret and not desktop.terminal_input.secret, "Invite secrète propre à chaque console")
	check(desktop.terminal_views[second].history.is_empty(), "Historique indépendant")
	desktop._create_gophish()
	var g: Control = desktop.gophish_view
	g.apply_data({"resources": {"campaigns": [], "groups": [{"id": 1, "name": "Briefing"}], "templates": [{"id": 1, "name": "Briefing"}], "pages": [{"id": 1, "name": "Briefing"}], "smtp": [{"id": 1, "name": "Lab"}]}, "api_key": "test"})
	g.section = "Campaigns"
	g.render()
	g._campaign_form()
	check(g._form_fields.has("template") and g._form_fields.has("smtp"), "Formulaire propre à GoPhish")
	g._form_fields.name.text = "Campagne test"
	var campaigns: Array = []
	g.api_requested.connect(func(method: String, endpoint: String, payload: Dictionary) -> void: campaigns.append([method, endpoint, payload]))
	g._launch_campaign()
	check(campaigns.size() == 1 and campaigns[0][1] == "campaigns", "Campagne GUI via la même API")
	var shortcut: InputEventKey = InputEventKey.new()
	shortcut.keycode = KEY_RIGHT
	shortcut.ctrl_pressed = true
	shortcut.alt_pressed = true
	shortcut.pressed = true
	desktop._input(shortcut)
	check(desktop.workspace == 1, "Raccourci global des espaces de travail")
	desktop._switch_workspace(0)
	frame.close_window()
	check(not frame.opened and not desktop.tasks.has("Terminal"), "Fermeture et retrait de la barre des tâches")
	print("Interface native : %s contrôles, %s échec(s)" % [checks, failures])
	desktop.queue_free()
	for i: int in range(3): await process_frame
	quit(1 if failures else 0)

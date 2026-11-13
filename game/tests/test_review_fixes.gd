extends SceneTree
## Régressions de la revue du client : GoPhish, Échap, clavier, forum, consoles.
var failures: int = 0

func check(condition: bool, message: String) -> void:
	if not condition:
		failures += 1
		push_error(message)

func _initialize() -> void:
	call_deferred("_run")

func _key(code: Key) -> void:
	for pressed: bool in [true, false]:
		var event: InputEventKey = InputEventKey.new()
		event.keycode = code
		event.pressed = pressed
		root.push_input(event)

func _texts(node: Node) -> String:
	var parts: PackedStringArray = []
	if node is Label: parts.append(node.text)
	elif node is RichTextLabel: parts.append(node.get_parsed_text())
	for child: Node in node.get_children(): parts.append(_texts(child))
	return "\n".join(parts)

func _run() -> void:
	root.size = Vector2i(1440, 900)
	root.content_scale_size = Vector2i(1440, 900)
	root.gui_embed_subwindows = true
	var desktop: Control = load("res://scenes/desktop.tscn").instantiate()
	root.add_child(desktop)
	await process_frame

	# GoPhish : un rafraîchissement automatique n’efface ni la connexion ni un formulaire.
	desktop._open("GoPhish")
	await process_frame
	var go: Control = desktop.gophish_view
	go.show_login()
	go._user.text = "admin"
	go.show_login()
	check(go._user.text == "admin", "GoPhish : l’identifiant saisi survit au rafraîchissement")
	var data: Dictionary = {"api_key": "k", "resources": {"campaigns": [{"results": [{"status": "Email Sent"}, {"status": "Email Opened"}, {"status": "Clicked Link"}, {"status": "Submitted Data"}]}], "templates": [{"name": "Briefing"}], "pages": [{"name": "Briefing"}], "smtp": [{"name": "Lab"}], "groups": [{"name": "Briefing"}]}}
	go.apply_data(data)
	var dashboard: String = _texts(go)
	check(dashboard.contains("4\nEmails Sent") and dashboard.contains("3\nEmail Opened") and dashboard.contains("2\nClicked Link") and dashboard.contains("1\nSubmitted Data"), "GoPhish : compteurs en entonnoir")
	go._campaign_form()
	go._form_fields.name.text = "Ma campagne"
	var changed: Dictionary = data.duplicate(true)
	changed.resources.campaigns.append({"results": []})
	go.apply_data(changed, true)
	check(is_instance_valid(go._form_fields.name) and go._form_fields.name.text == "Ma campagne", "GoPhish : formulaire conservé pendant un tick")
	check(go.resources.campaigns.size() == 2, "GoPhish : données mises à jour sans redessiner")

	# Échap : la recherche Chordly se ferme, les Paramètres ne s’ouvrent pas.
	desktop._open("Chordly")
	await process_frame
	var chat: Control = desktop.messengers.chordly
	chat._toggle_find()
	await process_frame
	_key(KEY_ESCAPE)
	await process_frame
	check(not chat._find_panel.visible, "Échap ferme la recherche Chordly")
	check(not (desktop.apps.has("Paramètres") and desktop.apps["Paramètres"].visible), "Échap consommé par la recherche n’ouvre pas les Paramètres")
	desktop.get_viewport().gui_release_focus()
	_key(KEY_ESCAPE)
	await process_frame
	check(desktop.apps["Paramètres"].visible, "Échap non utilisé ouvre toujours les Paramètres")

	# Clavier : la recherche du menu Applications garde ses touches, même avec un terminal actif.
	desktop._open("Terminal")
	await process_frame
	desktop._show_menu()
	await process_frame
	desktop._application_search.text = "ter"
	desktop._application_search.caret_column = 3
	_key(KEY_LEFT)
	await process_frame
	check(desktop.get_viewport().gui_get_focus_owner() == desktop._application_search, "Le terminal ne vole pas le focus de la recherche")
	check(desktop._application_search.caret_column == 2, "Flèche gauche appliquée dans la recherche")
	desktop._applications.hide()

	# Forum : un contrat principal reste consultable avec le filtre « Petits contrats ».
	var forum: Control = desktop.forum_view
	forum.contracts = [{"contract_id": "principal", "title": "Contrat principal", "client": {"handle": "client", "forum_rep": 10, "account_age_days": 30}, "body": "Annonce", "forum": "breachboard", "reward": 100, "tier": 0, "unlocked": true, "side_job": false}]
	forum._only_side_jobs = true
	forum.navigate("breachboard", "principal", "Contrats")
	await process_frame
	var page: String = _texts(forum)
	check(not page.contains("Sujet introuvable") and page.contains("Contrat principal"), "Sujet ouvert trouvé malgré le filtre")
	var posts: Array = [{"author": "client", "text": "Bonjour", "reputation": 10, "age": 30}]
	forum.set_replies("principal", posts)
	await process_frame
	var first_child: Node = forum._body.get_child(0)
	forum.set_replies("principal", posts.duplicate(true))
	await process_frame
	check(is_instance_valid(first_child) and first_child.is_inside_tree(), "Sujet inchangé : pas de reconstruction")

	# Consoles : fermer la console principale ne laisse pas de référence libérée.
	desktop._close_console("main")
	check(desktop.terminal == null and desktop.terminal_input == null, "Références de la console principale remises à zéro")

	print("Corrections de revue du client : %s échec(s)" % failures)
	quit(1 if failures else 0)

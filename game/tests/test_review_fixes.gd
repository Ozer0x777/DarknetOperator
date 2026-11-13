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
	var owner_after: Control = desktop.get_viewport().gui_get_focus_owner()
	check(owner_after == desktop._application_search, "Le terminal ne vole pas le focus de la recherche (focus : %s, menu visible : %s)" % [owner_after.get_path() if owner_after != null else "aucun", desktop._applications.visible])
	check(desktop._application_search.caret_column == 2, "Flèche gauche appliquée dans la recherche")
	# Manette branchée : la croix directionnelle et les boutons ne déplacent pas le focus ni ne cliquent.
	# Les événements passent par Input, comme ceux d'un vrai périphérique.
	for button: JoyButton in [JOY_BUTTON_DPAD_LEFT, JOY_BUTTON_DPAD_DOWN, JOY_BUTTON_A]:
		for pressed: bool in [true, false]:
			var pad: InputEventJoypadButton = InputEventJoypadButton.new()
			pad.button_index = button
			pad.pressed = pressed
			pad.pressure = 1.0 if pressed else 0.0
			Input.parse_input_event(pad)
			await process_frame
	var stick: InputEventJoypadMotion = InputEventJoypadMotion.new()
	stick.axis = JOY_AXIS_LEFT_X
	stick.axis_value = -1.0
	Input.parse_input_event(stick)
	await process_frame
	await process_frame
	check(desktop.get_viewport().gui_get_focus_owner() == desktop._application_search and desktop._applications.visible, "Une manette ne retire pas le focus de la saisie")
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

	# Sondage social : des compteurs identiques (décimaux côté JSON) ne reconstruisent pas le sujet ouvert.
	var world: Dictionary = {"threads": [], "profiles": {}, "forum_messages": [{"id": "mp1", "author": "k0rvid", "read": false}], "forum_counts": {"principal": 1.0}}
	forum.set_world(world)
	await process_frame
	var kept: Node = forum._body.get_child(0)
	for _poll: int in range(4):
		forum.set_replies("principal", posts.duplicate(true))
		forum.set_world(world.duplicate(true))
		await process_frame
	check(is_instance_valid(kept) and kept.is_inside_tree(), "Quatre sondages identiques : aucune reconstruction du forum")
	check(forum.message_unread("mp1") and not forum.message_unread("absent"), "Message privé encore non lu détecté")

	# Rechargement automatique : seulement si BreachBoard est visible, avec une adresse qui ne compte pas de vue.
	desktop._open("BreachBoard")
	await process_frame
	check(desktop._should_refresh_thread(), "Sujet visible : rechargement automatique")
	desktop.apps.BreachBoard.minimize_window()
	check(not desktop._should_refresh_thread(), "BreachBoard réduit : pas de rechargement ni de lecture comptée")
	check(desktop._thread_path("principal", true) == "/api/forum/threads/principal?refresh=true", "Adresse de relecture automatique")
	check(desktop._thread_path("principal", false) == "/api/forum/threads/principal", "Adresse d’ouverture réelle")

	# Réponses du moteur : vide, illisible ou du mauvais type → erreur, jamais de data inutilisable.
	var Session = load("res://scripts/session.gd")
	var ok: int = HTTPRequest.RESULT_SUCCESS
	check(Session.parse_response(ok, 200, "{\"id\": \"g1\"}").get("data", {}).get("id") == "g1", "Dictionnaire attendu accepté")
	check(Session.parse_response(ok, 200, "[1, 2]", TYPE_ARRAY).get("data", []).size() == 2, "Liste attendue acceptée")
	for body: String in ["", "   ", "null", "pas du json", "[]", "\"texte\""]:
		check(Session.parse_response(ok, 200, body).has("error"), "Réponse rejetée quand un dictionnaire est attendu : " + body)
	check(Session.parse_response(ok, 200, "{}", TYPE_ARRAY).has("error"), "Dictionnaire rejeté quand une liste est attendue")
	check(Session.parse_response(ok, 409, "{\"detail\": \"Mission déjà en cours\"}").get("error") == "Mission déjà en cours", "Message d’erreur du moteur transmis")
	check(Session.parse_response(HTTPRequest.RESULT_TIMEOUT, 0, "").has("error"), "Moteur injoignable signalé")

	# Consoles : fermer la console principale ne laisse pas de référence libérée.
	desktop._close_console("main")
	check(desktop.terminal == null and desktop.terminal_input == null, "Références de la console principale remises à zéro")

	print("Corrections de revue du client : %s échec(s)" % failures)
	quit(1 if failures else 0)

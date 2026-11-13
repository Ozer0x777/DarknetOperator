extends SceneTree
## Redimensionnement réel des contrôles, rédaction et citations sans moteur externe.
var failures: int = 0
var checks: int = 0
var output: String = "res://../build/social-layout"

func check(condition: bool, message: String) -> void:
	checks += 1
	if not condition:
		failures += 1
		push_error(message)

func _initialize() -> void: call_deferred("run")

func settle() -> void:
	for index: int in range(10): await process_frame

func fits(outer: Control, inner: Control) -> bool:
	return outer.get_global_rect().grow(1).encloses(inner.get_global_rect())

func key(code: Key, shift: bool = false, ctrl: bool = false) -> void:
	var event: InputEventKey = InputEventKey.new()
	event.keycode = code
	event.pressed = true
	event.shift_pressed = shift
	event.ctrl_pressed = ctrl
	root.push_input(event, true)
	event = event.duplicate()
	event.pressed = false
	root.push_input(event, true)
	await process_frame

func capture(name: String) -> void:
	if "--capture" not in OS.get_cmdline_user_args(): return
	if DisplayServer.get_name() == "headless": return
	await RenderingServer.frame_post_draw
	var directory: String = ProjectSettings.globalize_path(output)
	DirAccess.make_dir_recursive_absolute(directory)
	var result: Error = root.get_texture().get_image().save_png(directory.path_join(name + ".png"))
	check(result == OK, "Capture du rendu : " + name)

func run() -> void:
	root.content_scale_size = Vector2i.ZERO
	root.size = Vector2i(1280, 720)
	var desktop: Control = load("res://scenes/desktop.tscn").instantiate()
	root.add_child(desktop)
	await settle()
	var forum: Control = desktop.forum_view
	forum.update_data([], {"tier": 3, "route": "tor", "forum_unlocked": true}, "Operator", false)
	forum.set_world({"threads": [
		{"id": "polish", "forum": "breachboard", "section": "Discussion", "title": "Notes de la communauté : préparer son premier dossier et retrouver les échanges utiles", "author": "mod_echo", "body": "Les notes de la communauté sont disponibles.\nPrenez le temps de relire les conditions et de poser vos questions.", "pinned": true, "locked": false, "created_time": "11/11 09:00", "views": 128},
		{"id": "closed", "forum": "breachboard", "section": "Discussion", "title": "Archives de la communauté", "author": "mod_echo", "body": "Annonce archivée.", "pinned": false, "locked": true}
	], "profiles": {"mod_echo": {"role": "Modération", "age": 930, "reputation": 380}}})
	desktop._open("BreachBoard")
	var frame: Control = desktop.apps.BreachBoard
	frame.position = Vector2(60, 65)
	frame.size = Vector2(600, 600)
	forum.navigate("breachboard", "", "Discussion")
	await settle()
	check(frame.size.x <= 601 and forum._compact, "Forum à 600 px sans largeur imposée")
	check(forum._body.size.x <= forum.size.x + 1, "Index du forum sans débordement horizontal")
	var table: Node = forum._body.find_child("Topics", true, false)
	var visible_topics: int = 0
	for row: Node in table.get_children():
		if row.has_meta("topic") and row.visible: visible_topics += 1
	check(visible_topics == 2, "La recherche vide affiche tous les sujets")
	forum._filter_topics("introuvable")
	forum._filter_topics("")
	visible_topics = 0
	for row: Node in table.get_children():
		if row.has_meta("topic") and row.visible: visible_topics += 1
	check(visible_topics == 2, "Effacer la recherche restaure réellement les lignes")
	check(fits(frame, forum._search), "Recherche visible dans la fenêtre compacte")
	var navigation: Node = forum._body.find_child("SectionNavigation", true, false)
	var rectangles: Array[Rect2] = []
	var navigation_fits: bool = true
	for button: Node in navigation.get_children():
		if not button is Button: continue
		var rectangle: Rect2 = button.get_global_rect()
		if not fits(frame, button): navigation_fits = false
		for previous: Rect2 in rectangles:
			if previous.intersects(rectangle): navigation_fits = false
		rectangles.append(rectangle)
	check(navigation_fits and rectangles.size() == 6, "Rubriques du forum lisibles et sans chevauchement")
	await capture("forum-index-600")
	forum.navigate("breachboard", "polish", "Discussion")
	await settle()
	check(forum._body.size.x <= forum.size.x + 1, "Sujet et profil compacts sans débordement")
	var square_avatars: bool = true
	for avatar: Node in forum._body.find_children("ForumAvatar", "PanelContainer", true, false):
		if absf(avatar.size.x - avatar.size.y) > 1: square_avatars = false
	check(square_avatars, "Les avatars du forum restent carrés en mode compact")
	var quote_sample: VBoxContainer = VBoxContainer.new()
	forum.add_child(quote_sample)
	forum._post_body(quote_sample, "Avant\n> Première ligne\n> Seconde ligne\nAprès")
	check(quote_sample.get_child_count() == 3 and quote_sample.get_child(1) is PanelContainer, "Une citation multiligne forme un encadré unique")
	forum.remove_child(quote_sample)
	quote_sample.queue_free()
	forum._reply.text = "Mon brouillon initial."
	forum._quote_post("mod_echo", "Les notes sont disponibles.")
	check(forum._reply.text.begins_with("Mon brouillon initial.") and forum._reply.text.contains("> mod_echo"), "Une citation conserve le brouillon")
	await settle()
	check(fits(frame, forum._reply) and fits(frame, forum._publish), "Citer amène le compositeur dans la zone visible")
	forum._reply.grab_focus()
	forum._reply.set_caret_line(0)
	forum._reply.set_caret_column(5)
	frame.size.x = 1040
	await settle()
	check(not forum._compact and forum._reply.text.begins_with("Mon brouillon initial."), "Agrandir conserve le brouillon")
	check(forum._reply.get_caret_line() == 0 and forum._reply.get_caret_column() == 5, "Agrandir conserve le curseur de rédaction")
	forum._reply.select(0, 0, 0, 5)
	forum.render()
	check(forum._reply.has_selection() and forum._reply.get_selected_text() == "Mon b", "Actualiser conserve la sélection du brouillon")
	forum._reply.deselect()
	var replies: Array[String] = []
	forum.reply_requested.disconnect(desktop._reply_thread)
	forum.reply_requested.connect(func(_id: String, text: String) -> void: replies.append(text))
	await key(KEY_ENTER, false, true)
	check(replies.size() == 1, "Ctrl+Entrée publie la réponse")
	frame.size.x = 600
	await settle()
	await capture("forum-reponse-600")
	frame.close_window()
	for app_name: String in ["Chordly", "Telegrid", "Sessyon"]:
		var kind: String = app_name.to_lower()
		var chat: Control = desktop.messengers[kind]
		chat.set_identity("Operator")
		chat.set_contacts([{"id": "atelier", "channel": kind, "kind": "group", "name": "Atelier · notes et discussions de la communauté", "members": ["mod_echo", "miette"], "bio": "Un espace pour échanger et retrouver les notes utiles."}])
		chat._select_peer("atelier")
		chat.add_message({"id": kind + ":a", "peer": "atelier", "sender": "mod_echo", "text": "Les notes sont prêtes.", "time": "11/11 09:00"}, false)
		chat.add_message({"id": kind + ":b", "peer": "atelier", "sender": "mod_echo", "text": "Prenez le temps de les relire avant de commencer.\nLes détails sont dans le dossier de la communauté.", "time": "11/11 09:02"}, false)
		chat.add_message({"id": kind + ":c", "peer": "atelier", "sender": "Operator", "text": "Merci, je regarde ça.", "time": "11/11 09:03", "status": "read"}, false)
		desktop._open(app_name)
		frame = desktop.apps[app_name]
		frame.position = Vector2(60, 65)
		frame.size = Vector2(600, 600)
		await settle()
		var bubbles_fit: bool = true
		for row: Node in chat._stream.find_children("*", "Container", true, false):
			if row.get_script() == preload("res://scripts/ui/message_row.gd"):
				var bubble: Control = row.get_child(0)
				if not fits(row, bubble) or bubble.size.x > 561 or bubble.size.x < minf(row.size.x * 0.86, 150) - 1: bubbles_fit = false
		check(bubbles_fit, app_name + " : bulles limitées à la largeur du flux")
		check(frame.size.x <= 601 and fits(frame, chat.composer), app_name + " : rédaction visible à 600 px")
		check(not chat._side_panel.visible and chat._contacts_button.visible, app_name + " : navigation compacte")
		var starts: int = 0
		for row: Node in chat._stream.find_children("*", "Container", true, false):
			if row.get_meta("message_group_start", false): starts += 1
		check(starts == 2, app_name + " : messages proches regroupés par auteur")
		chat._contacts_button.pressed.emit()
		await settle()
		check(chat._side_panel.visible and fits(frame, chat.composer), app_name + " : contacts accessibles sans masquer la rédaction")
		chat._select_peer("atelier")
		chat._details_requested = true
		chat._adapt_layout()
		await settle()
		check(chat._details.visible and fits(frame, chat.composer), app_name + " : profil accessible en petite fenêtre")
		chat._details_requested = false
		chat._adapt_layout()
		var sent: Array[String] = []
		chat.send_message.disconnect(desktop._send_message)
		chat.send_message.connect(func(_channel: String, text: String) -> void: sent.append(text))
		chat.composer.text = "Première ligne"
		chat.composer.set_caret_column(14)
		chat.composer.grab_focus()
		await key(KEY_ENTER, true)
		check(sent.is_empty() and chat.composer.text.contains("\n"), app_name + " : Maj+Entrée ajoute une ligne")
		chat.composer.insert_text_at_caret("Deuxième ligne")
		await capture(kind + "-600")
		await key(KEY_ENTER)
		check(sent.size() == 1 and sent[0].contains("\n"), app_name + " : Entrée envoie le message multiligne")
		chat.acknowledge(true)
		chat.composer.text = "x".repeat(2001)
		chat._update_send_button()
		chat._send()
		check(chat._send_button.disabled and sent.size() == 1, app_name + " : limite de longueur avant envoi")
		chat.composer.text = ""
		frame.size = Vector2(1040, 600)
		await settle()
		check(chat._side_panel.visible and fits(frame, chat.composer), app_name + " : retour à la disposition large")
		await capture(kind + "-1040")
		frame.size = Vector2(600, 420)
		await settle()
		check(frame.size.y <= 421 and fits(frame, chat.composer) and fits(frame, chat._send_button), app_name + " : fenêtre minimale de 600 × 420")
		frame.close_window()
	print("Composition et rédaction : %s contrôles, %s échec(s)" % [checks, failures])
	desktop.queue_free()
	await process_frame
	quit(1 if failures else 0)

extends SceneTree
const DraftStore = preload("res://scripts/ui/draft_store.gd")
const Messenger = preload("res://scripts/ui/messenger.gd")
const Forum = preload("res://scripts/ui/forum.gd")
var checks: int = 0
var failures: int = 0
var temp: String

func _initialize() -> void: call_deferred("run")
func check(condition: bool, message: String) -> void:
	checks += 1
	if not condition:
		failures += 1
		push_error(message)
func settle() -> void:
	for index: int in range(10): await process_frame

func key(code: Key, shift: bool = false) -> void:
	var event: InputEventKey = InputEventKey.new()
	event.keycode = code
	event.pressed = true
	event.shift_pressed = shift
	root.push_input(event, true)
	event = event.duplicate()
	event.pressed = false
	root.push_input(event, true)
	await process_frame

func run() -> void:
	temp = "/tmp/rts-social-workflow-%s-%s" % [OS.get_process_id(), Time.get_ticks_usec()]
	DirAccess.make_dir_recursive_absolute(temp)
	root.content_scale_size = Vector2i.ZERO
	root.size = Vector2i(1280, 720)
	var desktop: Control = load("res://scenes/desktop.tscn").instantiate()
	root.add_child(desktop)
	await settle()
	var chat: Control = desktop.messengers.chordly
	chat._draft_store.directory_override = temp
	chat.set_identity("Workflow")
	chat.composer.text = "Brouillon durable\nDeuxième ligne"
	chat._update_send_button()
	await create_timer(0.5).timeout
	var restored: Control = Messenger.new()
	root.add_child(restored)
	restored.setup("chordly", "operator")
	restored.hide()
	restored._draft_store.directory_override = temp
	restored.set_identity("Workflow")
	check(restored.composer.text == "Brouillon durable\nDeuxième ligne", "Une nouvelle messagerie retrouve le brouillon sur disque")
	restored.queue_free()
	await process_frame
	var independent: RefCounted = DraftStore.new()
	independent.directory_override = temp
	independent.configure("Workflow", "telegrid")
	check(independent.values.is_empty(), "Brouillons isolés par service")
	independent.configure("Autre joueur", "chordly")
	check(independent.values.is_empty(), "Brouillons isolés par pseudo")
	independent.configure("Récupération", "forums")
	check(independent.save({"a": "Version précédente"}) == OK, "Premier enregistrement du brouillon")
	check(independent.save({"a": "Version récente"}) == OK, "Remplacement du brouillon avec copie précédente")
	var file: FileAccess = FileAccess.open(independent._path, FileAccess.WRITE)
	file.store_string("fichier interrompu")
	file.close()
	var recovered: RefCounted = DraftStore.new()
	recovered.directory_override = temp
	recovered.configure("Récupération", "forums")
	check(recovered.values.get("a") == "Version précédente", "Un brouillon endommagé récupère sa copie précédente")
	check(recovered.save({"a": "Version réparée"}) == OK, "Un brouillon récupéré peut être enregistré de nouveau")
	var verified: RefCounted = DraftStore.new()
	verified.directory_override = temp
	verified.configure("Récupération", "forums")
	check(verified.values.get("a") == "Version réparée", "Le fichier réparé est restaurable")
	file = FileAccess.open(temp.path_join("pas-un-dossier"), FileAccess.WRITE)
	file.store_string("test")
	file.close()
	var unavailable: RefCounted = DraftStore.new()
	unavailable.directory_override = temp.path_join("pas-un-dossier")
	unavailable.configure("Workflow", "forums")
	check(unavailable.save({"a": "À conserver"}) != OK, "Une erreur de disque est remontée")
	var forum: Control = desktop.forum_view
	forum._draft_store.directory_override = temp
	forum.update_data([], {"tier": 3, "route": "tor", "forum_unlocked": true}, "Workflow", false)
	var world: Dictionary = {"threads": [
		{"id": "workflow-a", "forum": "breachboard", "section": "Discussion", "title": "Dossier A", "author": "mod_echo", "body": "Notes A."},
		{"id": "workflow-b", "forum": "breachboard", "section": "Discussion", "title": "Dossier B", "author": "mod_echo", "body": "Notes B."}
	]}
	forum.set_world(world)
	forum.navigate("breachboard", "workflow-a", "Discussion")
	var publications: Array[String] = []
	forum.reply_requested.disconnect(desktop._reply_thread)
	forum.reply_requested.connect(func(_id: String, text: String) -> void: publications.append(text))
	forum._reply.text = "Réponse à publier"
	forum._submit_reply()
	forum._submit_reply()
	check(publications.size() == 1 and forum._publish.disabled and not forum._reply.editable, "Une publication en attente bloque les doubles envois")
	forum.set_replies("workflow-a", [])
	check(forum._publish.disabled and not forum._reply.editable, "Une actualisation ne débloque pas une publication en cours")
	var error_text: String = "Erreur temporaire : la publication ne peut pas être confirmée pour le moment. Ton texte est conservé et tu peux réessayer quand le moteur répondra."
	forum.acknowledge_reply("workflow-a", false, error_text)
	check(forum._reply.text == "Réponse à publier" and forum._reply.editable and not forum._publish.disabled and forum._reply_status.text == error_text, "Une erreur conserve la réponse et permet de réessayer")
	forum._submit_reply()
	forum.navigate("breachboard", "workflow-b", "Discussion")
	forum._reply.text = "Brouillon du dossier B"
	forum._update_reply_state()
	forum.acknowledge_reply("workflow-a", true)
	check(forum._reply.text == "Brouillon du dossier B", "Un accusé tardif ne touche pas un autre sujet")
	forum.navigate("breachboard", "workflow-a", "Discussion")
	check(forum._reply.text.is_empty() and forum._reply_status.text == "Réponse publiée.", "Seule la réponse publiée est effacée avec confirmation")
	forum.navigate("breachboard", "workflow-b", "Discussion")
	forum._save_drafts()
	var restored_forum: Control = Forum.new()
	root.add_child(restored_forum)
	restored_forum.setup()
	restored_forum.hide()
	restored_forum._draft_store.directory_override = temp
	restored_forum.update_data([], {"tier": 3, "route": "tor"}, "Workflow", false)
	restored_forum.set_world(world)
	restored_forum.navigate("breachboard", "workflow-b", "Discussion")
	check(restored_forum._reply.text == "Brouillon du dossier B", "Le forum restaure les brouillons après reconstruction complète")
	restored_forum.queue_free()
	await process_frame
	chat.messages.clear()
	chat.set_contacts([])
	check(chat._activity_by_peer.is_empty(), "Recharger les contacts après effacement des messages invalide les anciennes heures")
	chat._ids.clear()
	chat._contacts.clear()
	chat._select_peer("alpha")
	chat.add_message({"id": "a", "peer": "alpha", "sender": "alpha", "text": "x".repeat(55) + " balise", "time": "11/11 09:12"}, false)
	chat.add_message({"id": "b", "peer": "beta", "sender": "beta", "text": "Message récent", "time": "11/11 09:15"}, false)
	chat.add_message({"id": "old", "peer": "alpha", "sender": "alpha", "text": "Vieille archive", "time": "11/11 09:00"}, false)
	check(chat._ordered_peers()[0] == "beta" and chat._contacts.alpha.ends_with("balise"), "Une archive chargée tard ne remplace pas l’activité récente")
	chat._search.text = "balise"
	chat._search.text_changed.emit(chat._search.text)
	check(chat._list.get_child_count() == 1 and chat._list.get_child(0).get_meta("peer") == "alpha", "Recherche des contacts au-delà des 38 premiers caractères")
	chat._search.clear()
	chat.add_message({"id": "a2", "peer": "alpha", "sender": "alpha", "text": "Balise numéro deux", "time": "11/11 09:16"}, false)
	chat.add_message({"id": "a3", "peer": "alpha", "sender": "alpha", "text": "Balise numéro trois", "time": "11/11 09:17"}, false)
	check(chat._ordered_peers()[0] == "alpha", "Une nouvelle activité remonte la conversation")
	chat.send_message.disconnect(desktop._send_message)
	chat.composer.text = "Texte envoyé"
	chat._send()
	chat.acknowledge(true)
	var sent_store: RefCounted = DraftStore.new()
	sent_store.directory_override = temp
	sent_store.configure("Workflow", "chordly")
	check(not sent_store.values.has("alpha"), "Un message envoyé n’est pas restauré comme brouillon")
	desktop._open("Chordly")
	desktop.apps.Chordly.size = Vector2(600, 600)
	chat._find_panel.show()
	chat._find.text = "BALISE"
	chat._find.text_changed.emit(chat._find.text)
	await settle()
	check(chat._result_nodes.size() == 3 and chat._find_count.text == "1 / 3", "Recherche de messages avec compteur insensible à la casse")
	chat._navigate_result(1)
	check(chat._find_count.text == "2 / 3", "Résultat suivant")
	chat._navigate_result(-1)
	check(chat._find_count.text == "1 / 3", "Résultat précédent")
	chat._navigate_result(-1)
	check(chat._find_count.text == "3 / 3", "Navigation circulaire entre les résultats")
	chat._result_index = 0
	chat._render_messages()
	chat._find.grab_focus()
	await key(KEY_ENTER)
	check(chat._find_count.text == "2 / 3", "Entrée passe au résultat suivant depuis le champ")
	await key(KEY_ENTER, true)
	check(chat._find_count.text == "1 / 3", "Maj+Entrée passe au résultat précédent depuis le champ")
	chat._find.text = "absent-123"
	chat._find.text_changed.emit(chat._find.text)
	check(chat._find_count.text == "0 résultat" and chat._find_next.disabled and chat._find_previous.disabled, "Une recherche vide de résultats désactive la navigation")
	chat._toggle_find()
	for index: int in range(60):
		chat.messages.append({"id": "scroll:%s" % index, "peer": "alpha", "sender": "alpha", "text": "Une note de la conversation pour vérifier la lecture des anciens échanges. ".repeat(2), "time": "11/11 10:%02d" % index})
	chat._select_peer("alpha")
	await settle()
	chat._scroll.scroll_vertical = 0
	await settle()
	var incoming: Dictionary = {"id": "new", "peer": "alpha", "sender": "alpha", "text": "Nouveau message reçu pendant la lecture.", "time": "11/11 11:00"}
	chat.add_message(incoming, false)
	await settle()
	check(chat._new_messages_button.visible and chat._pending_new == 1 and not chat._at_bottom(), "Un nouveau message signale son arrivée sans déplacer la lecture")
	chat.add_message(incoming, false)
	check(chat._pending_new == 1, "Une actualisation ne duplique pas le signal de nouveau message")
	chat._new_messages_button.pressed.emit()
	await settle()
	check(chat._at_bottom() and chat._pending_new == 0 and not chat._new_messages_button.visible, "Le bouton rejoint les derniers messages et efface le signal")
	chat._find_panel.show()
	chat._find.text = "balise"
	chat._find.text_changed.emit(chat._find.text)
	await settle()
	chat.add_message({"id": "new-search", "peer": "alpha", "sender": "alpha", "text": "Un message hors recherche.", "time": "11/11 11:01"}, false)
	await settle()
	check(chat._new_messages_button.visible and chat._result_nodes.size() == 3, "Un message hors recherche reste signalé")
	chat._jump_to_latest()
	await settle()
	check(chat._find.text.is_empty() and not chat._find_panel.visible and chat._at_bottom(), "Rejoindre les derniers messages quitte la recherche")
	desktop.queue_free()
	await process_frame
	var directory: DirAccess = DirAccess.open(temp)
	for name: String in directory.get_files(): directory.remove(name)
	DirAccess.remove_absolute(temp)
	print("Flux sociaux persistants : %s contrôles, %s échec(s)" % [checks, failures])
	quit(1 if failures else 0)

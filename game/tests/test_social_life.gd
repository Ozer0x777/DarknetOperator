extends SceneTree
var failures: int = 0
var checks: int = 0
func check(condition: bool, message: String) -> void:
	checks += 1
	if not condition:
		failures += 1
		push_error(message)
func _initialize() -> void: call_deferred("run")
func run() -> void:
	root.size = Vector2i(1440, 900)
	var desktop: Control = load("res://scenes/desktop.tscn").instantiate()
	root.add_child(desktop)
	await process_frame
	await process_frame
	desktop.session.handle = "Operator"
	var forum: Control = desktop.forum_view
	var world: Dictionary = {
		"time": "09/11 09:12",
		"profiles": {"mod_echo": {"role": "Modération", "age": 930, "reputation": 380, "bio": "Signalements et litiges."}},
		"threads": [
			{"id": "welcome", "forum": "breachboard", "section": "Discussion", "title": "Bienvenue", "author": "mod_echo", "body": "Lisez les règles.", "pinned": true, "locked": false, "created_time": "08/11 09:00", "last_author": "miette", "last_time": "09/11 09:12", "last_minute": 12},
			{"id": "maintenance", "forum": "breachboard", "section": "Discussion", "title": "Maintenance", "author": "mod_echo", "body": "Annonce fermée.", "pinned": false, "locked": true}
		],
		"forum_counts": {"welcome": 3},
		"contacts": [
			{"id": "atelier", "name": "Atelier · communauté", "channel": "chordly", "kind": "group", "members": ["miette", "sable"], "bio": "Un groupe de discussion", "typing": true},
			{"id": "miette", "name": "miette", "channel": "chordly", "kind": "direct", "bio": "Apprentissage", "status_text": "Absent", "typing": false}
		],
		"messages": [
			{"id": "group:atelier", "channel": "chordly", "peer": "atelier", "sender": "miette", "text": "Les notes sont dans le groupe.", "time": "09/11 09:10"},
			{"id": "m1", "channel": "chordly", "peer": "miette", "sender": "miette", "text": "Salut Operator.", "time": "09/11 09:12"}
		]
	}
	desktop._update_social(world)
	check(desktop._world_time == "09/11 09:12", "Horloge du monde")
	desktop._open("BreachBoard")
	check(forum.profile.forum_counts.welcome == 3, "Compteurs conservés à l’ouverture du navigateur")
	var chat: Control = desktop.messengers.chordly
	check(chat.contact_profiles.has("atelier"), "Groupe visible")
	check(not desktop.messengers.telegrid.contact_profiles.has("atelier"), "Contacts séparés par messagerie")
	chat._select_peer("atelier")
	check(chat._header_name.text == "Atelier · communauté", "Nom de groupe")
	check(chat._header_status.text.contains("2 membres") and chat._header_status.text.contains("écrit"), "Membres et saisie différée")
	chat.composer.text = "Mon brouillon privé"
	desktop._update_social(world)
	check(chat.composer.text == "Mon brouillon privé", "Rafraîchissement conserve le brouillon du tchat")
	check(chat.messages.size() == 2, "Actualisation ne duplique pas les messages")
	chat._select_peer("miette")
	check(chat._header_status.text == "Absent", "Présence réelle du profil, sans faux statut en ligne")
	check(chat.unread == 0, "Lecture distincte des deux conversations")
	chat.add_message({"id": "code", "channel": "chordly", "peer": "miette", "sender": "miette", "text": "Lis `cat ~/mission/briefing.txt`, puis attends le résultat."}, false)
	var copy_buttons: int = 0
	for button: Node in chat._stream.find_children("*", "Button", true, false):
		if button.text == "Copier": copy_buttons += 1
	check(copy_buttons == 1, "Commande du guide copiable séparément")
	forum.navigate("breachboard", "welcome", "Discussion")
	forum._reply.text = "Mon brouillon forum"
	forum.set_replies("welcome", [{"author": "miette", "text": "Nouveau message", "time": "09/11 09:13", "age": 94}])
	check(forum._reply.text == "Mon brouillon forum", "Nouveau message conserve le brouillon du forum")
	forum._show_member("mod_echo")
	check(forum._member_dialog.dialog_text.contains("Modération") and forum._member_dialog.dialog_text.contains("930"), "Profil consultable avec son historique")
	forum._member_dialog.hide()
	forum.navigate("breachboard", "maintenance", "Discussion")
	forum.navigate("breachboard", "welcome", "Discussion")
	check(forum._reply.text == "Mon brouillon forum", "Brouillon restauré après changement de sujet")
	forum.navigate("breachboard", "maintenance", "Discussion")
	check(forum._reply == null, "Sujet verrouillé sans compositeur actif")
	for button: Node in forum._body.find_children("*", "Button", true, false):
		if button.text.ends_with("Citer"): check(button.disabled, "Pas de citation dans un sujet verrouillé")
	forum.navigate("breachboard", "", "Activité")
	check(forum._topics().size() == 2, "Navigation par activité")
	forum._search.text = "introuvable-123"
	forum._search.text_changed.emit(forum._search.text)
	check(forum._empty_search.visible, "Recherche forum sans résultat explicite")
	forum.render()
	check(forum._search.text == "introuvable-123" and forum._empty_search.visible, "Filtre conservé pendant une actualisation")
	forum._search.clear()
	check(not forum._empty_search.visible, "Effacement du filtre restaure les sujets")
	chat._search.text = "communauté"
	chat._search.text_changed.emit(chat._search.text)
	check(chat._list.get_child_count() == 1 and chat._list.get_child(0) is Button, "Recherche par nom affiché du groupe")
	chat._search.text = "introuvable-123"
	chat._search.text_changed.emit(chat._search.text)
	check(chat._list.get_child_count() == 1 and chat._list.get_child(0) is PanelContainer, "Recherche de contact sans résultat explicite")
	chat._search.clear()
	# Navigation sur les vrais nouveaux contenus, pour détecter les champs manquants.
	var source: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://../backend/data/social_world.json"))
	forum.update_data([], {"tier": 3, "route": "tor"}, "Operator", false)
	forum.set_world({"threads": source.threads, "profiles": source.profiles})
	for topic: Dictionary in source.threads:
		if topic.id in ["seller-dispute", "affiliate-terms", "incident-aftermath", "aquila-homonymes", "aquila-portail"]:
			forum.navigate(topic.forum, topic.id, "Discussion")
			check(forum._reply != null, "Nouveau fil consultable : " + topic.id)
	chat.mission_requested.disconnect(desktop._accept)
	var requested: Array[String] = []
	chat.mission_requested.connect(func(id: String) -> void: requested.append(id))
	chat._select_peer("miette")
	chat.composer.text = "Brouillon réservé à miette"
	chat._select_peer("k0rvid")
	check(chat.composer.text != "Brouillon réservé à miette", "Brouillon séparé par contact")
	chat.set_offers([{"id": "intro_terminal", "peer": "k0rvid", "title": "Premiers fichiers", "text": "Lire le dossier", "reward": 25}])
	for button: Node in chat._stream.find_children("*", "Button", true, false):
		if button.text == "Ouvrir le dossier": button.pressed.emit()
	check(requested == ["intro_terminal"], "Dossier accepté depuis le tchat")
	chat._select_peer("miette")
	check(chat.composer.text == "Brouillon réservé à miette", "Brouillon restauré au retour")
	forum.new_tab()
	var new_index: int = forum._tab_index
	forum.navigate("breachboard", "welcome", "Discussion")
	forum._switch_tab(0)
	forum._switch_tab(new_index)
	check(forum.selected_thread == "welcome", "Page conservée dans son onglet")
	forum._close_tab(new_index)
	check(forum._tabs.size() >= 1, "Fermeture d’un onglet conserve le navigateur")
	chat.send_message.disconnect(desktop._send_message)
	chat._select_peer("miette")
	chat.composer.text = "Message pour miette"
	chat._send()
	chat._select_peer("k0rvid")
	chat.composer.text = "Autre brouillon privé"
	chat.acknowledge(true)
	check(chat.composer.text == "Autre brouillon privé", "Accusé d’un contact conserve le brouillon de l’autre")
	chat._select_peer("miette")
	check(chat.composer.text.is_empty(), "Seul le brouillon envoyé est effacé")
	# Plusieurs changements avant le frame suivant ne doivent pas conserver un ancien portrait.
	chat._select_peer("k0rvid")
	chat._select_peer("miette")
	chat._select_peer("nullroute")
	check(chat._header_avatar.get_child_count() == 1 and chat._header_avatar.get_child(0).visible, "Un contact sans portrait retrouve son monogramme sans ancienne image")
	chat._select_peer("k0rvid")
	check(chat._header_avatar.get_child_count() == 2 and not chat._header_avatar.get_child(0).visible, "Un seul portrait est affiché au retour sur le contact")
	# Propositions et invitation résident dans les MP du forum.
	forum.update_data([], {"tier": 1, "forum_unlocked": true, "campaign": {"completed": 9, "chapters": [{"id": "act1_recommandation", "number": 10, "title": "Quelqu’un répond de toi", "peer": "bytewarden", "status": "available"}]}}, "Operator", false)
	forum.set_world({"forum_messages": [{"id": "test-offer", "author": "bytewarden", "subject": "Dossier privé", "body": "Pièces en privé.", "contract_id": "act1_recommandation", "read": false}, {"id": "test-invitation", "author": "bytewarden", "subject": "Invitation", "body": "Bienvenue.", "invitation": "exployt", "read": false}]})
	forum.navigate("breachboard", "", "Messages")
	check(forum._private_messages.size() == 2, "Les MP du forum ont leur boîte séparée")
	forum.navigate("breachboard", "test-offer", "Messages")
	var offers: Array[String] = []
	forum.accept_contract.disconnect(desktop._accept)
	forum.accept_contract.connect(func(id: String) -> void: offers.append(id))
	for button: Node in forum._body.find_children("*", "Button", true, false):
		if button.text == "Ouvrir le dossier privé": button.pressed.emit()
	check(offers == ["act1_recommandation"], "Un dossier peut être accepté depuis un MP du forum")
	forum.navigate("breachboard", "test-invitation", "Messages")
	var invitations: Array[String] = []
	forum.invitation_requested.disconnect(desktop._accept_invitation)
	forum.invitation_requested.connect(func(id: String) -> void: invitations.append(id))
	for button: Node in forum._body.find_children("*", "Button", true, false):
		if button.text.begins_with("Accepter l’invitation"): button.pressed.emit()
	check(invitations == ["test-invitation"], "L’invitation exige un clic explicite dans les MP")
	forum.navigate("breachboard", "", "Campagne")
	check(forum._body.find_children("*", "Label", true, false).any(func(label: Node) -> bool: return label.text.contains("9 / 10")), "Progression des dix chapitres visible")
	print("Vie sociale : %s contrôles, %s échec(s)" % [checks, failures])
	desktop.queue_free()
	await process_frame
	quit(1 if failures else 0)

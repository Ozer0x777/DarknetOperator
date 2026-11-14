extends SceneTree
## Exporte la géométrie réelle des contrôles pour une revue vectorielle sans GPU.
const UI = preload("res://scripts/ui/style.gd")
var output: String = ""
var records: Array[Dictionary] = []

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	root.size = Vector2i(1440, 900)
	root.content_scale_size = Vector2i(1440, 900)
	output = ProjectSettings.globalize_path("res://../build/ui-previews")
	DirAccess.make_dir_recursive_absolute(output)
	var desktop: Control = load("res://scenes/desktop.tscn").instantiate()
	root.add_child(desktop)
	print("Préparation de la scène de revue")
	await _settle()
	var data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://tests/fixtures/social_demo.json"))
	desktop.session.handle = "nightshift"
	desktop.session.contracts = data.contracts
	desktop._profile = data.profile
	desktop.profile_label.text = "nightshift"
	for messenger: Control in desktop.messengers.values(): messenger.set_identity("nightshift")
	desktop._render_board()
	await _capture(desktop, "01-bureau")
	desktop._show_menu()
	await _capture(desktop, "02-menu")
	desktop._applications.hide()
	var chordly: Control = desktop.messengers.chordly
	chordly.add_message({"id": "demo:1", "sender": "k0rvid", "peer": "k0rvid", "text": "Salut nightshift. J'ai un contrat pour toi. Le cabinet Ravelle : un petit réseau et un serveur de fichiers à atteindre.", "time": "14:32"}, false)
	chordly.add_message({"id": "demo:2", "sender": "nightshift", "peer": "k0rvid", "text": "Bien reçu. Je regarde les conditions sur le forum avant de commencer.", "time": "14:33"}, false)
	chordly.add_message({"id": "demo:3", "sender": "k0rvid", "peer": "k0rvid", "text": "L'annonce est sur BreachBoard. Les détails et la prime sont dans le sujet. Reviens ici si tu as besoin d'aide.", "time": "14:33", "link": true}, false)
	desktop._open("Chordly")
	await _capture(desktop, "03-chordly")
	desktop.apps.Chordly.close_window()
	desktop._open("BreachBoard")
	await _capture(desktop, "04-forum-index")
	desktop.forum_view.navigate("breachboard", "tuto_p0", "Contrats")
	desktop.forum_view.set_replies("tuto_p0", [{"author": "nightshift", "reputation": 200, "text": "Intéressé. Je consulte le brief et je te contacte sur Chordly."}])
	await _capture(desktop, "05-forum-sujet")
	desktop.forum_view.navigate("exployt", "", "Contrats")
	await _capture(desktop, "09-exployt")
	desktop.forum_view.profile = data.profile.duplicate(true)
	desktop.forum_view.profile.tier = 3
	desktop.forum_view.profile.reputation = 350
	desktop.forum_view.navigate("xsx", "", "Contrats")
	await _capture(desktop, "10-xsx")
	desktop.apps.BreachBoard.close_window()
	var telegrid: Control = desktop.messengers.telegrid
	telegrid.add_message({"id": "demo:4", "sender": "relay", "peer": "relay", "text": "L'accès à Exployt est ouvert. Configure ta route Tor avant de rejoindre le forum.", "time": "15:06"}, false)
	telegrid.add_message({"id": "demo:5", "sender": "nightshift", "peer": "relay", "text": "La route est prête. Je vais consulter les nouvelles annonces.", "time": "15:07"}, false)
	desktop._open("Telegrid")
	await _capture(desktop, "06-telegrid")
	desktop.apps.Telegrid.close_window()
	var sessyon: Control = desktop.messengers.sessyon
	sessyon.add_message({"id": "demo:6", "sender": "spectre", "peer": "spectre", "text": "Invitation reçue. Les membres de XSX préparent leurs accès avant chaque opération.", "time": "18:20"}, false)
	sessyon.add_message({"id": "demo:7", "sender": "nightshift", "peer": "spectre", "text": "Compris. Je vérifie le relais et l'équipement avant d'accepter.", "time": "18:21"}, false)
	desktop._open("Sessyon")
	await _capture(desktop, "07-sessyon")
	desktop.apps.Sessyon.close_window()
	desktop._open("Terminal")
	desktop._terminal_lines(["┌──(operator㉿kali)-[~]", "└─$ nmap -sV 10.20.0.0/24", "", "Nmap scan report for POSTE-ACCUEIL (10.20.0.21)", "Host is up.", "PORT     STATE SERVICE", "22/tcp   open  ssh", "445/tcp  open  smb", "", "Nmap scan report for SRV-FICHIERS (10.20.0.10)", "Host is up.", "445/tcp  open  smb"])
	await _capture(desktop, "08-terminal")
	desktop.apps.Terminal.close_window()
	desktop.files.set_loot([{"username": "m.leroux", "type": "PLAINTEXT", "value": "Password123!", "valid": true}, {"username": "it.presta", "type": "NTLM_HASH", "value": "0123456789abcdef0123456789abcdef", "valid": true}])
	desktop.files.navigate("/home/operator/loot")
	desktop._open("Fichiers")
	await _capture(desktop, "11-fichiers")
	desktop.apps.Fichiers.close_window()
	desktop._open("Terminal")
	desktop.apps.Terminal.position = Vector2(125, 90)
	desktop.apps.Terminal.size = Vector2(870, 450)
	desktop.terminal.clear()
	desktop._terminal_lines(["┌──(operator㉿kali)-[~]", "└─$ gophish --config /opt/gophish/config.json", "Starting admin server at https://127.0.0.1:3333", "Starting phishing server at http://0.0.0.0:80"])
	desktop._console_context("main", {"user": "operator", "cwd": "/home/operator", "hostname": "kali", "foreground": 3200})
	desktop._new_terminal()
	var secondary: String = "term-%s" % desktop.console_counter
	var secondary_app: String = desktop.console_apps[secondary]
	desktop.apps[secondary_app].position = Vector2(440, 390)
	desktop.apps[secondary_app].size = Vector2(870, 450)
	desktop._console_output(secondary, ["┌──(operator㉿kali)-[~]", "└─$ API_KEY=$(cat ~/gophish/api-key.txt)", "└─$ curl -k -H \"Authorization: $API_KEY\" https://127.0.0.1:3333/api/groups/", "[", "  { \"id\": 1, \"name\": \"Briefing\", \"targets\": [ ... ] }", "]"])
	await _capture(desktop, "12-plusieurs-consoles")
	desktop.apps.Terminal.close_window()
	desktop.apps[secondary_app].close_window()
	desktop._create_gophish()
	var gp: Dictionary = {"groups": [{"id": 1, "name": "Briefing"}], "templates": [{"id": 1, "name": "Briefing"}], "pages": [{"id": 1, "name": "Briefing"}], "smtp": [{"id": 1, "name": "Lab"}], "campaigns": [{"id": 1, "name": "Premier contrat", "status": "In progress", "results": [{"email": "m.leroux@ravelle.lab", "status": "Submitted Data"}]}]}
	desktop.gophish_view.apply_data({"resources": gp, "api_key": "0123456789abcdef"})
	desktop._open("GoPhish")
	await _capture(desktop, "13-gophish-dashboard")
	desktop.gophish_view.section = "Campaigns"
	desktop.gophish_view.render()
	desktop.gophish_view._campaign_form()
	desktop.gophish_view._form_fields.name.text = "Premier contrat"
	await _capture(desktop, "14-gophish-campagne")
	for frame: Control in desktop.apps.values(): frame.close_window()
	var social_path: String = "res://../build/validation/social-preview.json"
	if FileAccess.file_exists(social_path):
		var social: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(social_path))
		desktop._update_social(social)
		desktop.forum_view.profile = {"tier": 3, "route": "relay", "forum_counts": social.forum_counts}
		desktop.forum_view.navigate("breachboard", "", "Discussion")
		desktop._open("BreachBoard")
		await _capture(desktop, "15-communaute-active")
		desktop.forum_view.navigate("breachboard", "welcome", "Discussion")
		var posts: Array = [{"author": "miette", "text": "Salut, nouvelle ici. Je commence par les sujets épinglés.", "time": "07/11 18:10", "age": 94, "reputation": 29}, {"author": "mod_echo", "text": "Bienvenue. Cherche un sujet existant avant de publier.", "time": "07/11 18:33", "age": 930, "reputation": 380}]
		desktop.forum_view.set_replies("welcome", posts)
		await _capture(desktop, "16-discussion-archivee")
		desktop.apps.BreachBoard.close_window()
		desktop.messengers.chordly._select_peer("atelier")
		desktop._open("Chordly")
		await _capture(desktop, "17-tchat-groupe")
		desktop.messengers.chordly.add_message({"id": "preview:guide", "peer": "k0rvid", "sender": "k0rvid", "text": social.tutorial_guide, "time": "09/11 09:00"}, false)
		desktop.messengers.chordly._select_peer("k0rvid")
		await _capture(desktop, "18-tutoriel-commandes-copiables")
	for frame: Control in desktop.apps.values(): frame.close_window()
	desktop.gophish_view.section = "Landing Pages"
	desktop.gophish_view.render()
	desktop._open("GoPhish")
	await _capture(desktop, "19-gophish-capture-options")
	desktop.apps.GoPhish.close_window()
	var replay_path: String = "res://../build/validation/ui-replays.json"
	if FileAccess.file_exists(replay_path):
		var replays: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(replay_path))
		var found: bool = false
		for record: Dictionary in replays.successes:
			if found: break
			for step: Dictionary in record.steps:
				if step.response.context.get("shell") == "powershell":
					desktop._open("Terminal")
					desktop.terminal_views["main"].output.clear()
					desktop._console_context("main", step.state.terminals[step.console_id])
					desktop._console_output("main", [step.line] + step.response.output)
					desktop._open("Terminal")
					await _capture(desktop, "20-powershell")
					found = true
					break
	if FileAccess.file_exists(social_path):
		var community: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(social_path))
		desktop._profile.tier = 3
		desktop._profile.route = "relay"
		desktop._open("BreachBoard")
		desktop.forum_view.set_world(community)
		for entry: Array in [["seller-dispute", "breachboard", "21-litige-vendeur"], ["incident-aftermath", "xsx", "22-apres-incident"]]:
			desktop.forum_view.navigate(entry[1], entry[0], "Discussion")
			await _capture(desktop, entry[2])
		desktop.apps.BreachBoard.close_window()
	if FileAccess.file_exists(replay_path):
		var corpus: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(replay_path))
		var last_record: Dictionary = corpus.successes[-1]
		desktop._show_report(last_record.steps[-1].state)
		await _capture(desktop, "23-rapport-incident")
	if FileAccess.file_exists(social_path):
		var latest: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(social_path))
		desktop.forum_view.update_data(data.contracts, {"tier": 3, "route": "relay", "forum_unlocked": true}, "nightshift", false)
		desktop.forum_view.set_world(latest)
		desktop.forum_view.navigate("breachboard", "", "Discussion")
		desktop._open("BreachBoard")
		await _capture(desktop, "24-navigateur-forum")
		desktop.forum_view.navigate("breachboard", "welcome", "Discussion")
		await _capture(desktop, "25-forum-avatars")
		desktop.apps.BreachBoard.close_window()
		var direct: Control = desktop.messengers.chordly
		direct.messages.clear()
		direct._ids.clear()
		direct._contacts.clear()
		direct.contact_profiles.clear()
		desktop._update_social(latest.onboarding_world)
		direct._select_peer("k0rvid")
		desktop._open("Chordly")
		await _capture(desktop, "52-nouvelle-carriere-prochaine-piste")
		direct.add_message({"id": "preview:first-job", "peer": "k0rvid", "sender": "k0rvid", "text": str(latest.onboarding_brief).replace("{handle}", "nightshift"), "time": "09/11 09:00"}, false)
		direct._select_peer("k0rvid")
		desktop._open("Chordly")
		await _capture(desktop, "26-premier-dossier-chordly")
		desktop.apps.Chordly.close_window()
	if FileAccess.file_exists(social_path):
		var chapter_data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(social_path))
		desktop._update_social(chapter_data.chapter_world)
		desktop.messengers.chordly._select_peer("nullroute")
		desktop._open("Chordly")
		await _capture(desktop, "27-chapitre-8-proposition-privee")
		desktop.apps.Chordly.close_window()
		desktop.forum_view.update_data([], {"tier": 1, "forum_unlocked": true}, "nightshift", false)
		desktop.forum_view.navigate("breachboard", "aquila-portail", "Discussion")
		desktop.forum_view.set_replies("aquila-portail", chapter_data.chapter_posts)
		desktop._open("BreachBoard")
		await _capture(desktop, "28-chapitre-8-enquete-forum")
		desktop.apps.BreachBoard.close_window()
	var act1_path: String = "res://../build/validation/act1-sqlmap.json"
	if FileAccess.file_exists(act1_path):
		var act1: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(act1_path))
		desktop._profile = act1.profile_before_accept.duplicate(true)
		desktop.session.handle = "NightShift"
		desktop.session.contracts = []
		desktop._update_social(act1.world_before_accept)
		desktop._render_board()
		desktop._open("BreachBoard")
		desktop.forum_view.navigate("breachboard", "", "Campagne")
		await _capture(desktop, "29-acte-I-dix-chapitres")
		desktop.forum_view.navigate("breachboard", "act1-invitation", "Messages")
		await _capture(desktop, "30-invitation-en-MP")
		desktop.apps.BreachBoard.close_window()
	var home: Control = load("res://scenes/main_menu.tscn").instantiate()
	root.add_child(home)
	home.profile = {"handle": "nightshift", "money": 1425, "tier": 2, "has_active": true}
	home._set_busy(false)
	home.message.text = "nightshift · palier 2 · 1 425 ₵\nLogistique Varenne · mission suspendue"
	await _capture(home, "00-menu-accueil")
	var save_panel: Control = load("res://scripts/ui/save_manager.gd").new()
	home.add_child(save_panel)
	if FileAccess.file_exists(social_path):
		var fixture: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(social_path))
		save_panel.set_slots(fixture.get("save_slots", []))
		if save_panel.slots.size() > 0:
			save_panel.records.select(0)
			save_panel._select_slot(0)
	await _capture(home, "00b-sauvegardes")
	save_panel.queue_free()
	await process_frame
	home.handle_input.text = "nightshift"
	home.new_dialog.show()
	await _capture(home, "00c-nouvelle-carriere")
	home.new_dialog.hide()
	root.content_scale_size = Vector2i.ZERO
	root.size = Vector2i(1280, 720)
	await _settle()
	await _capture(home, "00d-menu-720p")
	var compact_saves: Control = load("res://scripts/ui/save_manager.gd").new()
	home.add_child(compact_saves)
	if FileAccess.file_exists(social_path):
		var compact_fixture: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(social_path))
		compact_saves.set_slots(compact_fixture.get("save_slots", []))
	await _capture(home, "00e-sauvegardes-720p")
	home.queue_free()
	await process_frame
	# Dispositions sociales compactes : bureau 720p et fenêtres réellement réduites.
	for frame: Control in desktop.apps.values(): frame.close_window()
	for entry: Array in [["Chordly", "31-chordly-600"], ["Telegrid", "32-telegrid-600"], ["Sessyon", "33-sessyon-600"]]:
		var app_name: String = entry[0]
		var chat: Control = desktop.messengers[app_name.to_lower()]
		chat.set_contacts([{"id": "atelier_preview", "channel": app_name.to_lower(), "name": "Atelier · notes de la communauté", "kind": "group", "members": ["mod_echo", "miette"], "bio": "Notes partagées et échanges entre membres de la communauté."}])
		chat.add_message({"id": app_name + ":preview:1", "peer": "atelier_preview", "sender": "mod_echo", "text": "Les notes sont prêtes.", "time": "11/11 09:00"}, false)
		chat.add_message({"id": app_name + ":preview:2", "peer": "atelier_preview", "sender": "mod_echo", "text": "Les conditions sont dans le dossier de la communauté. Prenez le temps de les relire avant de commencer.", "time": "11/11 09:01"}, false)
		chat.add_message({"id": app_name + ":preview:3", "peer": "atelier_preview", "sender": "nightshift", "text": "Bien reçu, je regarde ça.\nJe reviens vers vous si j’ai une question.", "time": "11/11 09:02", "status": "read"}, false)
		chat.add_message({"id": app_name + ":preview:4", "peer": "atelier_preview", "sender": "miette", "text": "Merci pour les notes !", "time": "11/11 09:03"}, false)
		chat._select_peer("atelier_preview")
		chat.composer.text = "J’ai consulté les conditions.\nVoici mes premières questions…"
		chat._update_send_button()
		desktop._open(app_name)
		desktop.apps[app_name].position = Vector2(280, 60)
		desktop.apps[app_name].size = Vector2(600, 600)
		await _capture(desktop, entry[1])
		if app_name == "Chordly":
			chat._details_requested = true
			chat._adapt_layout()
			await _capture(desktop, "36-profil-contact-600")
			chat._details_requested = false
			chat._adapt_layout()
			desktop.apps[app_name].size.x = 1040
			desktop.apps[app_name].position.x = 120
			await _capture(desktop, "37-chordly-groupes-1040")
		desktop.apps[app_name].close_window()
	if FileAccess.file_exists(social_path):
		var compact_world: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(social_path))
		desktop.forum_view.update_data(data.contracts, {"tier": 3, "route": "relay", "forum_unlocked": true}, "nightshift", false)
		desktop.forum_view.set_world(compact_world)
		desktop._open("BreachBoard")
		desktop.apps.BreachBoard.position = Vector2(280, 60)
		desktop.apps.BreachBoard.size = Vector2(600, 600)
		desktop.forum_view.navigate("breachboard", "", "Discussion")
		await _capture(desktop, "34-forum-index-600")
		desktop.forum_view.navigate("breachboard", "welcome", "Discussion")
		await _capture(desktop, "35-forum-sujet-600")
		desktop.forum_view._reply.text = "Merci pour l’accueil."
		desktop.forum_view._quote_post("mod_echo", "Bienvenue sur BreachBoard. Lis les sujets épinglés avant de publier.")
		await _capture(desktop, "38-forum-citation-600")
		desktop.apps.BreachBoard.size.x = 1040
		desktop.apps.BreachBoard.position.x = 120
		await _capture(desktop, "39-forum-reponse-1040")
	for frame: Control in desktop.apps.values(): frame.close_window()
	var search_chat: Control = desktop.messengers.chordly
	search_chat._select_peer("atelier_preview")
	desktop._open("Chordly")
	desktop.apps.Chordly.size = Vector2(600, 600)
	desktop.apps.Chordly.position = Vector2(280, 60)
	search_chat._find_panel.show()
	search_chat._find.text = "notes"
	search_chat._find.text_changed.emit(search_chat._find.text)
	await _capture(desktop, "40-recherche-messages-600")
	search_chat.add_message({"id": "preview:message-pendant-recherche", "peer": "atelier_preview", "sender": "miette", "text": "Un nouveau dossier vient d’arriver.", "time": "11/11 09:04"}, false)
	await _capture(desktop, "41-nouveau-message-pendant-lecture")
	search_chat._jump_to_latest()
	desktop.apps.Chordly.close_window()
	if FileAccess.file_exists(social_path):
		desktop._open("BreachBoard")
		desktop.apps.BreachBoard.size = Vector2(600, 600)
		desktop.apps.BreachBoard.position = Vector2(280, 60)
		desktop.forum_view.navigate("breachboard", "welcome", "Discussion")
		desktop.forum_view._reply.text = "Merci pour l’accueil, j’ai bien consulté les règles."
		desktop.forum_view._update_reply_state()
		desktop.forum_view._scroll.ensure_control_visible.call_deferred(desktop.forum_view._reply_panel)
		desktop.forum_view._submit_reply()
		await _capture(desktop, "42-publication-en-cours")
		desktop.forum_view.acknowledge_reply("welcome", false, "Publication interrompue. Ton brouillon est conservé ; tu peux réessayer.")
		await _capture(desktop, "43-publication-erreur-et-brouillon")
	for frame: Control in desktop.apps.values(): frame.close_window()
	desktop._profile = {"tier": 0, "forum_unlocked": false, "access": {"shop": {"unlocked": false, "reason": "Termine le dossier Ravelle."}, "forums": {
		"breachboard": {"unlocked": false, "reason": "Retrouve k0rvid sur Chordly et termine le dossier Ravelle."},
		"exployt": {"unlocked": false, "reason": "Invitation requise."},
		"xsx": {"unlocked": false, "reason": "Recommandation requise."}}}}
	desktop._render_board()
	desktop.forum_view.navigate("breachboard")
	desktop._open("BreachBoard")
	desktop._show_menu()
	await _capture(desktop, "44-progression-et-boutique-verrouillee")
	desktop._applications.hide()
	desktop.apps.BreachBoard.close_window()
	var wallet_data: Dictionary = {"device_id": "CV-DEMO", "balance": 1000, "connected": false, "unlocked": false,
		"pending": {"id": "demo-payment", "label": "GPU niveau 1", "amount": 400, "recipient": "Fournisseurs - services et matériel"},
		"entries": [{"id": "opening", "label": "Solde repris", "amount": 1000, "balance": 1000}]}
	desktop.wallet_view.set_data(wallet_data)
	desktop._open("ColdVault")
	desktop.apps.ColdVault.position = Vector2(300, 55)
	desktop.apps.ColdVault.size = Vector2(640, 620)
	await _capture(desktop, "45-coldvault-appareil-deconnecte")
	wallet_data.connected = true
	wallet_data.unlocked = true
	desktop.wallet_view.set_data(wallet_data)
	await _capture(desktop, "46-coldvault-confirmer-paiement")
	wallet_data.balance = 600
	wallet_data.pending = null
	wallet_data.entries.append({"id": "purchase", "label": "GPU niveau 1", "amount": -400, "balance": 600})
	desktop.wallet_view.set_data(wallet_data)
	await _capture(desktop, "47-coldvault-journal-et-solde")
	desktop.apps.ColdVault.close_window()
	desktop._open("Paramètres")
	desktop.apps["Paramètres"].position = Vector2(290, 55)
	desktop.apps["Paramètres"].size = Vector2(680, 620)
	await _capture(desktop, "48-reglages-audio-et-musique")
	desktop.apps["Paramètres"].close_window()
	var audio_home: Control = load("res://scenes/main_menu.tscn").instantiate()
	root.add_child(audio_home)
	audio_home._settings()
	await _capture(audio_home, "49-audio-depuis-menu")
	audio_home.queue_free()
	await process_frame
	for frame: Control in desktop.apps.values(): frame.close_window()
	if FileAccess.file_exists(social_path):
		var journey_data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(social_path))
		desktop._render_shop(journey_data.get("shop_catalog", []))
		desktop.apps.Boutique.open_window(0)
		desktop.apps.Boutique.position = Vector2(290,55)
		desktop.apps.Boutique.size = Vector2(690,620)
		await _capture(desktop, "50-boutique-effets-et-reserve")
		desktop.apps.Boutique.size = Vector2(600,420)
		await _capture(desktop, "51-boutique-600")
		desktop.apps.Boutique.close_window()
	if FileAccess.file_exists(social_path):
		var first_data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(social_path))
		var first_chat: Control = desktop.messengers.chordly
		first_chat._unread_by_peer.clear()
		first_chat.unread = 0
		first_chat.unread_changed.emit(0)
		first_chat.messages.clear()
		first_chat._ids.clear()
		first_chat._contacts.clear()
		first_chat.set_offers([])
		first_chat.set_journey({})
		first_chat._select_peer("k0rvid")
		desktop._social_ready = false
		desktop._message_notifications.clear()
		desktop._toast.hide()
		desktop.session.game_id = "preview-first-hour"
		desktop.session.state = first_data.first_hour_state
		desktop._update_state(first_data.first_hour_state)
		desktop._open("Chordly")
		desktop.apps.Chordly.position = Vector2(280,60)
		desktop.apps.Chordly.size = Vector2(600,600)
		first_chat._toggle_mission_goal()
		await _capture(desktop, "53-console-objectif-et-indice-600")
		desktop.apps.Chordly.size = Vector2(600,420)
		await _capture(desktop, "54-console-objectif-et-indice-minimal")
		desktop.apps.Chordly.close_window()
		desktop._notification_cooldown = 0
		desktop.active_app = "Terminal"
		for index: int in range(3): desktop._queue_message_notification("Nouveau message", "Chordly", "k0rvid")
		desktop._flush_message_notifications()
		await _capture(desktop, "55-notifications-regroupees")
	for frame: Control in desktop.apps.values(): frame.close_window()
	var demo_chat: Control = desktop.messengers.chordly
	demo_chat.set_mission_context({})
	demo_chat.set_offers([])
	demo_chat.set_contacts([{"id":"miette", "name":"miette", "channel":"chordly", "kind":"direct", "members":["miette"], "bio":"Confiance établie - Tu as vérifié les sources avant de conclure."}])
	demo_chat.set_journey({"title":"Démo terminée - une annonce corrigée dans ton dossier", "detail":"Tu as confronté une annonce aux faits par le partage public. Le client conserve les preuves en privé. Miette se souvient de ta vérification. Tes primes, preuves et décisions restent sauvegardées. Continue la campagne pour découvrir les autres outils, Ravelle et BreachBoard.", "app":"Chordly", "peer":"miette", "action":"continue_campaign"})
	demo_chat._select_peer("miette")
	desktop._open("Chordly")
	desktop.apps.Chordly.position = Vector2(280,60)
	desktop.apps.Chordly.size = Vector2(600,420)
	await _capture(desktop, "56-conclusion-demo-600")
	if FileAccess.file_exists(social_path):
		var learning_data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(social_path))
		var learning_chat: Control = desktop.messengers.chordly
		learning_chat.messages.clear()
		learning_chat._ids.clear()
		learning_chat.set_offers([])
		learning_chat.set_journey({})
		learning_chat._select_peer("nullroute")
		desktop.session.game_id = "preview-learning"
		desktop.session.state = learning_data.learning_state
		desktop._update_state(learning_data.learning_state)
		desktop.apps.Chordly.size = Vector2(600,420)
		await _capture(desktop, "57-aide-service-par-phase-600")
	if FileAccess.file_exists(social_path):
		var second_data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(social_path))
		for frame: Control in desktop.apps.values(): frame.close_window()
		desktop.session.game_id = ""
		desktop._toast.hide()
		desktop._create_bloodhound()
		var analysis: Control = desktop.apps.BloodHound.get_meta("analysis")
		analysis.apply_data(second_data.bloodhound)
		desktop.apps.BloodHound.open_window(0)
		desktop.apps.BloodHound.position = Vector2(180,70)
		desktop.apps.BloodHound.size = Vector2(1000,600)
		await _capture(desktop,"58-bloodhound-collecte-et-relations")
		desktop.apps.BloodHound.close_window()
		desktop._profile = second_data.act2_profile
		desktop.forum_view.update_data([],second_data.act2_profile,"nightshift",false)
		desktop.forum_view.navigate("exployt","","Campagne")
		desktop._open("BreachBoard")
		desktop.apps.BreachBoard.position = Vector2(180,50)
		desktop.apps.BreachBoard.size = Vector2(1040,620)
		await _capture(desktop,"59-acte-II-campagne")
	if FileAccess.file_exists(social_path):
		var current_data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(social_path))
		for frame: Control in desktop.apps.values(): frame.close_window()
		for messenger: Control in desktop.messengers.values():
			messenger.messages.clear()
			messenger._ids.clear()
			messenger._contacts.clear()
			messenger.set_mission_context({})
		desktop.session.game_id = ""
		desktop._social_ready = false
		desktop._profile = current_data.current_profile
		desktop._update_social(current_data.current_world)
		desktop.messengers.chordly._select_peer("k0rvid")
		desktop._open("Chordly")
		desktop.apps.Chordly.position = Vector2(280,60)
		desktop.apps.Chordly.size = Vector2(600,420)
		await _capture(desktop,"60-ravelle-public-600")
		desktop.apps.Chordly.close_window()
		desktop._profile = current_data.transition_profile
		desktop._update_social(current_data.transition_world)
		desktop.messengers.telegrid._select_peer("cendre")
		desktop._open("Telegrid")
		desktop.apps.Telegrid.position = Vector2(250,60)
		desktop.apps.Telegrid.size = Vector2(760,560)
		await _capture(desktop,"61-cendre-passation")
		desktop.apps.Telegrid.close_window()
		desktop.forum_view.update_data([],current_data.transition_profile,"nightshift",false)
		desktop.forum_view.navigate("exployt","","Campagne")
		desktop._open("BreachBoard")
		desktop.apps.BreachBoard.position = Vector2(280,60)
		desktop.apps.BreachBoard.size = Vector2(600,420)
		await _capture(desktop,"62-transition-campagne-600")
	for frame: Control in desktop.apps.values(): frame.close_window()
	desktop._toast.hide()
	desktop._message_notifications.clear()
	var music: Node = root.get_node("Audio")
	music.set_context("desktop")
	music.next_track()
	desktop._open("Lecteur audio")
	desktop.apps["Lecteur audio"].position = Vector2(300,60)
	desktop.apps["Lecteur audio"].size = Vector2(620,520)
	await _capture(desktop,"63-lecteur-audio")
	desktop.apps["Lecteur audio"].size = Vector2(520,420)
	await _capture(desktop,"64-lecteur-audio-compact")
	print("Géométrie des vues exportée dans " + output)
	desktop.queue_free()
	await process_frame
	quit(0)

func _settle() -> void:
	for i: int in range(8): await process_frame

func _capture(desktop: Control, id: String) -> void:
	print("Vue : " + id)
	await _settle()
	records.clear()
	var canvas_size: Vector2 = root.get_visible_rect().size
	_walk(desktop, 0, Rect2(Vector2.ZERO, canvas_size))
	var file: FileAccess = FileAccess.open(output.path_join(id + ".json"), FileAccess.WRITE)
	file.store_string(JSON.stringify({"name": id, "width": int(canvas_size.x), "height": int(canvas_size.y), "nodes": records}, "\t"))

func _rect(rect: Rect2) -> Array:
	return [rect.position.x, rect.position.y, rect.size.x, rect.size.y]

func _color(color: Color) -> String:
	return "#" + color.to_html(true)

func _walk(node: Node, parent_z: int, clip: Rect2, window_offset: Vector2 = Vector2.ZERO) -> void:
	var z: int = parent_z
	if node is Window and node != root:
		if not node.visible: return
		window_offset += Vector2(node.position)
		var window_rect: Rect2 = Rect2(window_offset, Vector2(node.size))
		clip = clip.intersection(window_rect)
		z += 400
		records.append({"path": str(node.get_path()), "type": "Window", "rect": _rect(window_rect), "z": z, "clip": _rect(clip), "background": "#252733ff", "border": "#576171ff", "border_width": 1, "radius": 4})
	if node is CanvasItem:
		if not node.is_visible_in_tree(): return
		z += node.z_index
	if node is Control:
		var rect: Rect2 = node.get_global_rect()
		rect.position += window_offset
		if node.clip_contents: clip = clip.intersection(rect)
		var r: Dictionary = {"path": str(node.get_path()), "type": node.get_class(), "rect": _rect(rect), "z": z, "clip": _rect(clip)}
		if "positions" in node and "edges" in node:
			var segments: Array = []
			for edge: Dictionary in node.edges:
				var start: Vector2 = node.get_global_transform_with_canvas()*(node.positions[edge.source]+Vector2(130,80))+window_offset
				var finish: Vector2 = node.get_global_transform_with_canvas()*(node.positions[edge.target]+Vector2(130,0))+window_offset
				segments.append({"from":[start.x,start.y],"to":[finish.x,finish.y],"label":str(edge.type)})
			r["graph_edges"] = segments
		var style: StyleBox
		if node is PanelContainer: style = node.get_theme_stylebox("panel")
		elif node is Button: style = node.get_theme_stylebox("disabled" if node.disabled else "normal")
		elif node is LineEdit or node is TextEdit: style = node.get_theme_stylebox("normal")
		elif node is Tree or node is ItemList: style = node.get_theme_stylebox("panel")
		if style is StyleBoxFlat:
			r["background"] = _color(style.bg_color)
			r["border"] = _color(style.border_color)
			r["border_width"] = style.border_width_left
			r["radius"] = style.corner_radius_top_left
			r["margins"] = [style.get_content_margin(SIDE_LEFT), style.get_content_margin(SIDE_TOP), style.get_content_margin(SIDE_RIGHT), style.get_content_margin(SIDE_BOTTOM)]
		var text: String = ""
		var font: Font
		var font_size: int = 14
		if node is Label or node is Button or node is LineEdit or node is TextEdit:
			text = node.text
			if node is LineEdit or node is TextEdit:
				if text.is_empty(): text = node.placeholder_text
				if node is TextEdit: r["wrap"] = node.wrap_mode != TextEdit.LINE_WRAPPING_NONE
				if node is LineEdit and node.secret: text = "••••••••"
				if node.get_script() == preload("res://scripts/ui/command_input.gd") and node.secret: text = ""
			font = node.get_theme_font("font")
			font_size = node.get_theme_font_size("font_size")
			r["color"] = _color(node.get_theme_color("font_disabled_color" if node is Button and node.disabled else "font_color"))
			if node is Label:
				r["align"] = node.horizontal_alignment
				r["valign"] = node.vertical_alignment
				r["wrap"] = node.autowrap_mode != TextServer.AUTOWRAP_OFF
			if node is Button:
				r["wrap"] = node.autowrap_mode != TextServer.AUTOWRAP_OFF
				r["align"] = node.alignment
				r["valign"] = VERTICAL_ALIGNMENT_CENTER
				if node.icon != null:
					r["icon"] = node.icon.resource_path
					r["icon_size"] = node.get_theme_constant("icon_max_width")
		elif node is RichTextLabel:
			text = node.get_parsed_text()
			font = node.get_theme_font("normal_font")
			font_size = node.get_theme_font_size("normal_font_size")
			r["color"] = _color(node.get_theme_color("default_color"))
			r["wrap"] = true
		if font != null:
			r["text"] = text
			r["font"] = font.resource_path
			r["font_size"] = font_size
			r["ascent"] = font.get_ascent(font_size)
			r["height"] = font.get_height(font_size)
			r["lines"] = _wrap(text, maxf(20, rect.size.x - (12 if node is Button else 0)), font, font_size) if r.get("wrap", false) else Array(text.split("\n"))
		if node is HSlider: r["slider"] = {"value": node.value, "min": node.min_value, "max": node.max_value}
		if node is ColorRect: r["background"] = _color(node.color)
		if node is ItemList:
			var items: Array[Dictionary] = []
			for i: int in range(node.item_count):
				var item_rect: Rect2 = node.get_item_rect(i)
				var icon: Texture2D = node.get_item_icon(i)
				items.append({"text": node.get_item_text(i), "rect": _rect(item_rect), "icon": icon.resource_path if icon else "", "selected": node.is_selected(i)})
			r["items"] = items
		if node is TextureRect and node.texture != null:
			r["round_avatar"] = node.get_meta("round_avatar", false)
			if node.texture is AtlasTexture:
				r["image"] = node.texture.atlas.resource_path
				r["atlas_region"] = _rect(node.texture.region)
				r["atlas_size"] = [node.texture.atlas.get_width(), node.texture.atlas.get_height()]
			else: r["image"] = node.texture.resource_path
			r["cover"] = node.stretch_mode == TextureRect.STRETCH_KEEP_ASPECT_COVERED
		records.append(r)
	for child: Node in node.get_children(): _walk(child, z, clip, window_offset)

func _wrap(text: String, width: float, font: Font, font_size: int) -> Array[String]:
	var result: Array[String] = []
	for paragraph: String in text.split("\n"):
		var line: String = ""
		for word: String in paragraph.split(" "):
			var candidate: String = word if line.is_empty() else line + " " + word
			if not line.is_empty() and font.get_string_size(candidate, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x > width:
				result.append(line)
				line = word
			else: line = candidate
		result.append(line)
	return result

extends SceneTree
## Les nouvelles pistes et fiches d'achat doivent rester lisibles à 600 × 420.
var checks: int = 0
var failures: int = 0
func _initialize() -> void: call_deferred("run")
func check(value: bool, message: String) -> void:
	checks += 1
	if not value:
		failures += 1
		push_error(message)
func settle() -> void:
	for index: int in range(12): await process_frame
func fits(outer: Control, inner: Control) -> bool:
	return outer.get_global_rect().grow(1).encloses(inner.get_global_rect())
func run() -> void:
	root.content_scale_size = Vector2i.ZERO
	root.size = Vector2i(1280,720)
	var desktop: Control = load("res://scenes/desktop.tscn").instantiate()
	root.add_child(desktop)
	await settle()
	var chat: Control = desktop.messengers.chordly
	chat._select_peer("k0rvid")
	chat.set_journey({"title":"Premier contrat — cabinet Ravelle", "detail":"Aucun achat requis. Consulte ColdVault pour les règlements ; demande aide au client si tu bloques.", "app":"ColdVault", "peer":"k0rvid", "contract_id":"tuto_p0"})
	desktop._open("Chordly")
	var frame: Control = desktop.apps.Chordly
	frame.position = Vector2(60,60)
	frame.size = Vector2(600,420)
	await settle()
	check(chat._stream.find_child("NextStep",true,false) != null, "La prochaine piste est visible dans la bonne conversation")
	check(fits(frame,chat.composer) and fits(frame,chat._send_button), "La piste ne masque pas la rédaction compacte")
	var opened: Array[String] = []
	chat.open_app.connect(func(app: String) -> void: opened.append(app))
	for button: Node in chat._stream.find_children("*","Button",true,false):
		if button.text == "Ouvrir ColdVault": button.pressed.emit()
	check(opened == ["ColdVault"], "La piste ouvre son application cible")
	chat.set_offers([{"id":"tuto_p0","peer":"k0rvid","title":"Cabinet Ravelle","text":"Un premier dossier complet.","reward":300}])
	await settle()
	check(chat._stream.find_child("NextStep",true,false) == null, "Une offre et sa piste ne créent pas deux cartes redondantes")
	chat.composer.text = "Ma note à conserver"
	chat.set_journey({"title":"Prochaine piste principale", "detail":"La bonne mission.", "app":"Chordly", "peer":"k0rvid", "contract_id":"main"})
	chat.set_offers([
		{"id":"side","peer":"k0rvid","channel":"chordly","title":"Petit contrat", "text":"Optionnel.","reward":30,"side_job":true,"reason":"Un autre dossier est en cours."},
		{"id":"main","peer":"k0rvid","channel":"chordly","title":"Dossier principal", "text":"En cours.","reward":300,"active":true},
		{"id":"foreign","peer":"k0rvid","channel":"telegrid","title":"Autre messagerie", "text":"Ne pas afficher ici.","reward":300}])
	await settle()
	check(chat._offers.size()==2,"Les offres sont isolées par messagerie même pour un même pseudo")
	var offer_labels: Array[Node] = chat._stream.find_children("*","Label",true,false)
	check(offer_labels.filter(func(label: Node) -> bool: return label.text=="Prochaine piste principale").size()==1,"Une seule offre porte la prochaine piste principale")
	check(offer_labels.any(func(label: Node) -> bool: return label.text=="DOSSIER FACULTATIF"),"Un petit contrat est présenté comme facultatif")
	var offer_buttons: Array[Node] = chat._stream.find_children("*","Button",true,false)
	check(offer_buttons.any(func(button: Node) -> bool: return button.text=="Ouvrir le dossier" and button.disabled),"Un second départ impossible est expliqué et désactivé")
	check(offer_buttons.any(func(button: Node) -> bool: return button.text=="Reprendre le dossier" and not button.disabled),"Le dossier actif reste accessible")
	check(chat.composer.text=="Ma note à conserver","Actualiser les offres préserve le brouillon")
	chat.set_offers([{"id":"side","peer":"k0rvid","channel":"chordly","title":"Petit contrat","text":"Optionnel.","reward":30}])
	await settle()
	check(chat._stream.find_child("NextStep",true,false)!=null,"Un contrat facultatif ne masque pas la prochaine piste principale")
	chat.set_journey({"title":"Passation", "app":"Telegrid", "peer":"k0rvid", "contract_id":"foreign"})
	check(chat._journey.is_empty(),"Une piste privée Telegrid n’apparaît pas sur Chordly")
	chat._select_peer("autre")
	await settle()
	check(chat._stream.find_child("NextStep",true,false) == null, "La piste privée ne s’affiche pas chez un autre contact")
	desktop.apps.Chordly.close_window()
	desktop._render_shop([
		{"id":"gpu2","name":"GPU niveau 2","price":800,"description":"Hashcat : trois ticks de base. Le prix reprend la valeur du GPU déjà acquis.","owned":false,"unlocked":true,"reason":"","reserve":50},
		{"id":"glasswing","name":"Glasswing — licence","price":450,"description":"Conserve 100 % du règlement modulé des contrats affiliation. Comparer le coût et les conditions avant de payer.","owned":false,"unlocked":false,"reason":"Garde 300 ₵ pour la route obligatoire du prochain dossier.","reserve":300}])
	frame = desktop.apps.Boutique
	frame.open_window(0)
	frame.position = Vector2(60,60)
	frame.size = Vector2(600,420)
	await settle()
	check(frame.size.x <= 601 and frame.size.y <= 421, "Fiches d'achat dans une fenêtre minimale")
	check(desktop.shop.size.x <= frame.size.x, "Description et paiement sans débordement horizontal")
	var buttons: Array[Node] = desktop.shop.find_children("*","Button",true,false)
	check(buttons.size()==2 and not buttons[0].disabled and buttons[1].disabled, "Les conditions d'achat désactivent le bon paiement")
	var labels: Array[Node] = desktop.shop.find_children("*","Label",true,false)
	check(labels.any(func(label: Node) -> bool: return label.text.contains("Réserve pour le prochain accès")), "La réserve obligatoire est expliquée avant de dépenser")
	check(labels.any(func(label: Node) -> bool: return label.text.contains("Garde 300")), "Le refus d'achat affiche sa raison")
	desktop.queue_free()
	await process_frame
	print("Parcours et achats : %s contrôles, %s échec(s)" % [checks,failures])
	quit(1 if failures else 0)

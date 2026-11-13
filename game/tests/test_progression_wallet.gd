extends SceneTree
var checks: int = 0
var failures: int = 0
func _initialize() -> void: call_deferred("run")
func check(value: bool, message: String) -> void:
	checks += 1
	if not value:
		failures += 1
		push_error(message)
func settle() -> void:
	for index: int in range(10): await process_frame
func run() -> void:
	root.content_scale_size = Vector2i.ZERO
	root.size = Vector2i(1280,720)
	var desktop: Control = load("res://scenes/desktop.tscn").instantiate()
	root.add_child(desktop)
	await settle()
	desktop._profile = {"tier": 0, "forum_unlocked": false, "access": {"shop": {"unlocked": false, "reason": "Termine Ravelle."}, "forums": {
		"breachboard": {"unlocked": false, "reason": "Termine Ravelle."},
		"exployt": {"unlocked": false, "reason": "Invitation nécessaire."},
		"xsx": {"unlocked": false, "reason": "Recommandation nécessaire."}}}}
	desktop._render_board()
	desktop._open("Boutique")
	check(not desktop.apps.Boutique.opened, "Boutique inaccessible avant la progression")
	desktop._render_applications()
	var buttons: Array[Node] = desktop._application_list.find_children("*", "Button", true, false)
	check(buttons.any(func(button: Node) -> bool: return button.text == "Services et matériel" and button.disabled), "Le menu explique la boutique verrouillée")
	var forum: Control = desktop.forum_view
	check(not forum._bookmarks.exployt.visible and not forum._bookmarks.xsx.visible, "Forums non débloqués absents des favoris")
	check(forum._tab_row.find_children("*", "Button", true, false).all(func(button: Node) -> bool: return not button.text.contains("Exployt") and not button.text.contains("XSX")), "Forums non débloqués absents des onglets")
	forum.navigate("xsx")
	check(not forum.lock_reason().is_empty() and forum._reply == null, "Une adresse saisie à la main ne contourne pas le verrouillage")
	var profile: Dictionary = {"tier": 3, "money": 999999, "reputation": 99, "forum_reputation": {"breachboard": 17, "exployt": 3, "xsx": 0}}
	forum.update_data([], profile, "Operator", false)
	forum.navigate("exployt")
	var labels: Array[Node] = forum._body.find_children("*", "Label", true, false)
	check(labels.any(func(label: Node) -> bool: return label.text == "Réputation locale : 3"), "Réputation propre au forum sélectionné")
	check(not labels.any(func(label: Node) -> bool: return label.text.contains("999999")), "Le solde n’apparaît plus dans les forums")
	var wallet: Control = desktop.wallet_view
	wallet.device_action.disconnect(desktop._wallet_action)
	var events: Array = []
	wallet.device_action.connect(func(action: String, id: String) -> void: events.append([action, id]))
	wallet.set_data({"balance": 1000, "device_id": "CV-TEST", "connected": false, "unlocked": false, "pending": {"id": "request-1", "label": "GPU niveau 1", "amount": 400, "recipient": "Fournisseur"}, "entries": [{"id": "opening", "amount": 1000, "balance": 1000, "label": "Solde initial"}]})
	desktop._open("ColdVault")
	var frame: Control = desktop.apps.ColdVault
	frame.position = Vector2(100,60)
	frame.size = Vector2(600,600)
	await settle()
	check(frame.size.x <= 601 and frame.size.y <= 601, "Portefeuille dans une fenêtre compacte")
	var confirm: Button
	for button: Node in wallet.find_children("*", "Button", true, false):
		if button.text == "Confirmer sur l’appareil": confirm = button
	check(confirm != null and confirm.disabled, "Signature impossible lorsque l’appareil est déconnecté")
	wallet.set_data({"balance": 1000, "device_id": "CV-TEST", "connected": true, "unlocked": true, "pending": {"id": "request-1", "label": "GPU niveau 1", "amount": 400, "recipient": "Fournisseur"}})
	for button: Node in wallet.find_children("*", "Button", true, false):
		if button.text == "Confirmer sur l’appareil": confirm = button
	confirm.pressed.emit()
	wallet._action("approve", "request-1")
	check(events == [["approve", "request-1"]], "Une seule confirmation de l’identifiant de paiement")
	wallet.set_data({"balance": 600, "connected": true, "unlocked": true, "pending": null})
	check(not wallet.find_children("*", "Button", true, false).any(func(button: Node) -> bool: return button.text == "Confirmer sur l’appareil"), "Demande confirmée retirée de l’appareil")
	desktop.queue_free()
	await process_frame
	print("Progression et portefeuille : %s contrôles, %s échec(s)" % [checks, failures])
	quit(1 if failures else 0)

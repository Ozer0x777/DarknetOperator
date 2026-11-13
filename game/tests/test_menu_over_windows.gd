extends SceneTree
## Régression : le menu Applications reste cliquable au-dessus des fenêtres ouvertes.
var failures: int = 0

func check(condition: bool, message: String) -> void:
	if not condition:
		failures += 1
		push_error(message)

func _initialize() -> void:
	call_deferred("_run")

func _click(point: Vector2) -> void:
	for pressed: bool in [true, false]:
		var event: InputEventMouseButton = InputEventMouseButton.new()
		event.position = point
		event.global_position = point
		event.button_index = MOUSE_BUTTON_LEFT
		event.pressed = pressed
		root.push_input(event, true)

func _run() -> void:
	root.size = Vector2i(1440, 900)
	root.content_scale_size = Vector2i(1440, 900)
	var desktop: Control = load("res://scenes/desktop.tscn").instantiate()
	root.add_child(desktop)
	await process_frame
	desktop._open("Terminal")
	var terminal: Control = desktop.apps.Terminal
	terminal.position = Vector2(0, 32)
	terminal.size = Vector2(900, 700)
	terminal.focus_window()
	await process_frame
	desktop._show_menu()
	await process_frame
	await process_frame
	var target: Button = null
	for button: Node in desktop._application_list.get_children():
		if button is Button and button.text == "Gestionnaire de fichiers": target = button
	check(target != null, "Entrée Fichiers présente dans le menu")
	if target != null:
		var point: Vector2 = target.get_global_rect().get_center()
		check(terminal.get_global_rect().has_point(point), "L’entrée du menu recouvre bien le terminal")
		_click(point)
		await process_frame
		await process_frame
		check(desktop.apps.has("Fichiers") and desktop.apps.Fichiers.visible, "Le clic sur le menu ouvre l’application, pas la fenêtre dessous")
		check(not desktop._applications.visible, "Le menu se ferme après le lancement")
	desktop._show_menu()
	await process_frame
	terminal.focus_window()
	await process_frame
	check(not desktop._applications.visible, "Activer une fenêtre ferme le menu")
	check(desktop.get_child(desktop.get_child_count() - 1) != terminal, "Le panneau reste au-dessus des fenêtres pour les clics")
	print("Menu au-dessus des fenêtres : %s échec(s)" % failures)
	quit(1 if failures else 0)

extends SceneTree
## Régression : les poignées ne doivent jamais recouvrir le contenu interactif.
const Frame = preload("res://scripts/ui/window_frame.gd")
var failures: int = 0
var clicks: int = 0

func check(condition: bool, message: String) -> void:
	if not condition:
		failures += 1
		push_error(message)

func _initialize() -> void:
	call_deferred("_run")

func _move(point: Vector2) -> void:
	var event: InputEventMouseMotion = InputEventMouseMotion.new()
	event.position = point
	event.global_position = point
	root.push_input(event, true)

func _click(point: Vector2, pressed: bool) -> void:
	var event: InputEventMouseButton = InputEventMouseButton.new()
	event.position = point
	event.global_position = point
	event.button_index = MOUSE_BUTTON_LEFT
	event.pressed = pressed
	root.push_input(event, true)

func _run() -> void:
	root.size = Vector2i(1440, 900)
	root.content_scale_size = Vector2i(1440, 900)
	var desktop: Control = Control.new()
	desktop.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.add_child(desktop)
	var frame: PanelContainer = Frame.new()
	desktop.add_child(frame)
	var body: VBoxContainer = frame.setup("Regression", "Regression", "terminal", Vector2i(800, 500))
	frame.position = Vector2(150, 100)
	var button: Button = Button.new()
	button.text = "Cliquer ici"
	button.custom_minimum_size.y = 90
	button.pressed.connect(func() -> void: clicks += 1)
	body.add_child(button)
	var field: LineEdit = LineEdit.new()
	body.add_child(field)
	frame.open_window(0)
	for i: int in range(4): await process_frame
	var center: Vector2 = button.get_global_rect().get_center()
	for handle: Control in frame._resize_handles:
		check(not handle.get_global_rect().has_point(center), "Une poignée couvre le bouton central")
		check(handle.size.x <= 7 or handle.size.y <= 7, "Une poignée dépasse la bordure")
	_move(center)
	await process_frame
	check(root.gui_get_hovered_control() == button, "Le pointeur doit atteindre le bouton")
	_click(center, true)
	_click(center, false)
	await process_frame
	check(clicks == 1, "Le clic doit déclencher le bouton")
	check(not frame._resize, "Le clic intérieur ne doit pas redimensionner")
	var field_center: Vector2 = field.get_global_rect().get_center()
	_move(field_center)
	_click(field_center, true)
	_click(field_center, false)
	await process_frame
	check(field.has_focus(), "Le champ doit recevoir le focus souris")
	var corner: Control = frame._resize_handles[-1]
	var corner_point: Vector2 = corner.get_global_rect().get_center()
	_move(corner_point)
	_click(corner_point, true)
	check(frame._resize, "Le coin doit conserver son action de redimensionnement")
	_click(corner_point, false)
	frame.toggle_maximize()
	for i: int in range(3): await process_frame
	for handle: Control in frame._resize_handles:
		check(handle.mouse_filter == Control.MOUSE_FILTER_IGNORE, "Une fenêtre maximisée ne doit pas intercepter par ses poignées")
	center = button.get_global_rect().get_center()
	_move(center)
	_click(center, true)
	_click(center, false)
	check(clicks == 2, "Le bouton doit rester cliquable après maximisation")
	frame.toggle_maximize()
	for i: int in range(3): await process_frame
	for handle: Control in frame._resize_handles:
		check(handle.size.x <= 7 or handle.size.y <= 7, "La restauration doit garder des poignées fines")
	print("Clics et bordures : %s échec(s)" % failures)
	desktop.queue_free()
	await process_frame
	quit(1 if failures else 0)

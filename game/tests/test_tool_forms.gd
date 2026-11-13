extends SceneTree
var failures: int = 0
var checks: int = 0
func check(value: bool, message: String) -> void:
	checks += 1
	if not value:
		failures += 1
		push_error(message)
func _initialize() -> void: call_deferred("run")
func run() -> void:
	root.size = Vector2i(1440, 900)
	var view: Control = load("res://scripts/ui/gophish.gd").new()
	root.add_child(view)
	view.setup()
	view.authenticated = true
	view.section = "Landing Pages"
	view.resources = {"campaigns":[],"groups":[],"templates":[],"pages":[],"smtp":[]}
	view.render()
	await process_frame
	var capture: CheckBox
	var passwords: CheckBox
	for box: Node in view.find_children("*", "CheckBox", true, false):
		if box.text == "Capture Submitted Data": capture = box
		if box.text == "Capture Passwords": passwords = box
	check(capture != null and passwords != null, "Options réelles de capture dans GoPhish")
	check(not capture.button_pressed and passwords.disabled, "Capture désactivée à la création d’une page")
	capture.button_pressed = true
	check(not passwords.disabled, "Capture du mot de passe accessible après activation de la collecte")
	passwords.button_pressed = true
	capture.button_pressed = false
	check(not passwords.button_pressed and passwords.disabled, "Désactiver la collecte désactive aussi les mots de passe")
	var terminal: Control = load("res://scripts/ui/terminal_view.gd").new()
	root.add_child(terminal)
	terminal.setup("test")
	terminal.set_context({"shell":"powershell","display_cwd":"C:\\Tools"})
	check(terminal.prompt.text == "PS C:\\Tools>", "Invite PowerShell distincte")
	terminal.set_context({"shell":"cmd","display_cwd":"C:\\Tools"})
	check(terminal.prompt.text == "C:\\Tools>", "Retour à cmd")
	terminal.queue_free()
	view.queue_free()
	await process_frame
	print("Formulaires et shells : %s contrôles, %s échec(s)" % [checks, failures])
	quit(1 if failures else 0)

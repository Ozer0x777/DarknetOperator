extends SceneTree
const Terminal = preload("res://scripts/ui/terminal_view.gd")
class Clipboard extends RefCounted:
	var text: String = ""
	func get_text() -> String: return text
	func set_text(value: String) -> void: text = value
var failures: int = 0
var interrupts: int = 0
var completions: int = 0
func check(value: bool, message: String) -> void:
	if not value:
		failures += 1
		push_error(message)
func key(view: Control, code: Key, ctrl: bool = false, shift: bool = false) -> void:
	var event: InputEventKey = InputEventKey.new()
	event.keycode = code
	event.pressed = true
	event.ctrl_pressed = ctrl
	event.shift_pressed = shift
	view.key_input(event)
func _initialize() -> void: call_deferred("run")
func run() -> void:
	root.size = Vector2i(900, 600)
	root.gui_embed_subwindows = true
	var view: VBoxContainer = Terminal.new()
	root.add_child(view)
	view.size = Vector2(800, 500)
	view.setup("test")
	view.clipboard_backend = Clipboard.new()
	view.interrupted.connect(func(_id: String) -> void: interrupts += 1)
	view.completion_requested.connect(func(_id: String, _line: String, _caret: int) -> void: completions += 1)
	await process_frame
	view.input.text = "abcd"
	view.input.caret_column = 2
	key(view, KEY_LEFT)
	check(view.input.caret_column == 1, "Flèche gauche")
	key(view, KEY_RIGHT, false, true)
	key(view, KEY_C, true)
	check(view.clipboard_backend.text == "b" and interrupts == 0, "Ctrl+C copie la sélection")
	view.input.deselect()
	view.input.caret_column = 2
	view.clipboard_backend.text = "XY"
	key(view, KEY_V, true)
	check(view.input.text == "abXYcd", "Collage au curseur")
	view.clipboard_backend.text = "commande 1\ncommande 2"
	key(view, KEY_V, true)
	check(view.input.text == "abXYcd" and not view._completion_hint.text.is_empty(), "Collage multiligne expliqué sans modifier la saisie")
	key(view, KEY_C, true)
	check(interrupts == 1, "Ctrl+C interrompt sans sélection")
	key(view, KEY_TAB)
	check(completions == 1, "Tab demande une complétion")
	view.apply_completion({"source_line": "abXYcd", "source_caret": 4, "line": "gophish ", "caret": 8, "candidates": ["gophish"]})
	check(view.input.text == "gophish ", "Réponse de complétion")
	view.apply_completion({"source_line": "ancien", "source_caret": 0, "line": "incorrect"})
	check(view.input.text == "gophish ", "Réponse obsolète ignorée")
	var mouse: InputEventMouseButton = InputEventMouseButton.new()
	mouse.button_index = MOUSE_BUTTON_RIGHT
	mouse.pressed = true
	view.key_input(mouse)
	check(view.context_menu.visible, "Menu clic droit visible")
	view.context_menu.hide()
	for i: int in range(200): view.append_lines(["Ligne %s" % i])
	await process_frame
	await process_frame
	var bottom: float = view.output.get_v_scroll_bar().value
	key(view, KEY_PAGEUP)
	check(view.output.get_v_scroll_bar().value < bottom, "Page précédente défile")
	key(view, KEY_PAGEDOWN)
	check(view.output.get_v_scroll_bar().value >= bottom - 1, "Page suivante défile")
	var sent: Array[String] = []
	view.command_submitted.connect(func(_id: String, line: String) -> void: sent.append(line))
	view.output.clear()
	view.set_context({"shell": "bash", "password_prompt": true, "password_label": "Password:"})
	view.append_lines(["Password:"])
	check(view.prompt.get_parent() == view.input.get_parent() and view.prompt.text == "Password:" and view.input.placeholder_text.is_empty(), "Invite mot de passe sans invite Kali")
	check(not view.output.get_parsed_text().contains("Password:"), "Invite active non dupliquée dans le défilement")
	var history_size: int = view.history.size()
	view.clipboard_backend.text = " pass/@:word! "
	view.paste_clipboard()
	check(view.input.text == " pass/@:word! ", "Espaces du mot de passe conservés au collage")
	view.submit(view.input.text)
	check(sent[-1] == " pass/@:word! " and view.history.size() == history_size, "Secret envoyé intact et absent de l’historique")
	check(not view.output.get_parsed_text().contains("pass/@:word"), "Secret absent du défilement")
	view.submit("")
	check(sent[-1].is_empty(), "Mot de passe vide envoyé")
	view.input.text = "secret interrompu"
	view.set_context({"shell": "bash", "password_prompt": false})
	check(view.input.text.is_empty() and not view.input.secret, "Sortie du mode secret efface le brouillon")
	check(view.prompt.get_parent() != view.input.get_parent() and view._shell_prefix.visible and view._shell_prefix.text == "└─$", "Invite Kali rétablie")
	view.set_context({"shell": "cmd", "display_cwd": "C:\\Windows\\system32"})
	check(view.prompt.text == "C:\\Windows\\system32>" and view.input.placeholder_text.is_empty(), "Invite cmd sans symbole Kali")
	view.set_context({"shell": "powershell", "display_cwd": "C:\\Windows\\system32"})
	check(view.prompt.text == "PS C:\\Windows\\system32>", "Invite PowerShell")
	view.set_context({"shell": "bash"})
	var long_command: String = "curl -H " + "argument_".repeat(70)
	view.input.text = long_command
	view.input.caret_column = long_command.length()
	await process_frame
	await process_frame
	check(view.input.get_line_wrap_count(0) > 0, "Longue commande repliée visuellement")
	view.set_context({"shell": "bash"})
	check(view.input.text == long_command, "Rafraîchissement conserve le début et la totalité de la saisie")
	view.input.caret_column = 0
	view.input.insert_text_at_caret("prefixe ")
	check(view._shell_prefix.visible and view.input.text == "prefixe " + long_command, "Insertion au début après une longue saisie")
	view.queue_free()
	await process_frame
	print("Clavier, presse-papiers et complétion : %s échec(s)" % failures)
	quit(1 if failures else 0)

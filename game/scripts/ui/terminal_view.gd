extends VBoxContainer
## Une instance = une console, son historique, sa sortie et sa session propre.
const UI = preload("res://scripts/ui/style.gd")
signal command_submitted(console_id: String, line: String)
signal interrupted(console_id: String)
signal completion_requested(console_id: String, line: String, caret: int)
signal new_window
var console_id: String
var output: RichTextLabel
const CommandInput = preload("res://scripts/ui/command_input.gd")
var input: TextEdit
var prompt: Label
var history: Array[String] = []
var history_index: int = 0
var context: Dictionary = {}
var _shell_prefix: Label
var _input_row: HBoxContainer
var _column: VBoxContainer
var _foreground: Label
var context_menu: PopupMenu
var clipboard_backend: RefCounted
var _draft: String = ""
var _completion_hint: Label

func setup(id: String) -> void:
	console_id = id
	size_flags_vertical = Control.SIZE_EXPAND_FILL
	add_theme_constant_override("separation", 0)
	var menus: HBoxContainer = HBoxContainer.new()
	add_child(menus)
	for label: String in ["Fichier", "Édition", "Affichage", "Aide"]:
		var menu: MenuButton = MenuButton.new()
		menu.text = label
		menus.add_child(menu)
		var popup: PopupMenu = menu.get_popup()
		if label == "Fichier":
			popup.add_item("Nouvelle fenêtre", 0)
			popup.add_item("Interrompre le processus (Ctrl+C)", 1)
			popup.id_pressed.connect(func(item: int) -> void:
				if item == 0: new_window.emit()
				else: interrupted.emit(console_id))
		elif label == "Édition":
			popup.add_item("Copier la sélection", 0)
			popup.add_item("Coller", 1)
			popup.add_item("Effacer", 2)
			popup.id_pressed.connect(func(item: int) -> void:
				if item == 0: copy_selection()
				elif item == 1: paste_clipboard()
				else: output.clear())
		elif label == "Affichage":
			popup.add_item("Agrandir la police", 0)
			popup.add_item("Réduire la police", 1)
			popup.id_pressed.connect(func(item: int) -> void:
				output.add_theme_font_size_override("normal_font_size", clampi(output.get_theme_font_size("normal_font_size") + (1 if item == 0 else -1), 10, 25)))
		else:
			popup.add_item("Commandes et outils")
			popup.id_pressed.connect(func(_item: int) -> void: submit("help"))
	var panel: PanelContainer = UI.panel(Color("12131c"), 12)
	panel.size_flags_vertical = Control.SIZE_EXPAND_FILL
	add_child(panel)
	var column: VBoxContainer = VBoxContainer.new()
	_column = column
	panel.add_child(column)
	output = RichTextLabel.new()
	output.size_flags_vertical = Control.SIZE_EXPAND_FILL
	output.selection_enabled = true
	output.scroll_following = true
	output.bbcode_enabled = false
	output.add_theme_font_override("normal_font", UI.MONO)
	output.add_theme_font_size_override("normal_font_size", 14)
	column.add_child(output)
	_foreground = UI.label("", 12, Color("929bad"))
	_foreground.visible = false
	column.add_child(_foreground)
	prompt = UI.label("┌──(operator㉿kali)-[~]", 13, Color("6ba8e8"))
	prompt.add_theme_font_override("font", UI.MONO)
	prompt.size_flags_vertical = Control.SIZE_SHRINK_BEGIN
	column.add_child(prompt)
	_input_row = HBoxContainer.new()
	_input_row.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	column.add_child(_input_row)
	_shell_prefix = UI.label("└─$", 14, Color("6ba8e8"))
	_shell_prefix.add_theme_font_override("font", UI.MONO)
	# Invite et saisie alignées en haut avec la même police : même ligne de base.
	_shell_prefix.size_flags_vertical = Control.SIZE_SHRINK_BEGIN
	_input_row.add_child(_shell_prefix)
	input = CommandInput.new()
	input.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	input.add_theme_font_override("font", UI.MONO)
	input.add_theme_font_size_override("font_size", 14)
	input.add_theme_constant_override("line_spacing", 0)
	input.add_theme_stylebox_override("normal", UI.box(Color("12131c")))
	input.add_theme_stylebox_override("focus", UI.box(Color("12131c")))
	input.placeholder_text = ""
	input.max_length = 16384
	input.text_submitted.connect(submit)
	input.gui_input.connect(key_input)
	_input_row.add_child(input)
	input.context_menu_enabled = false
	output.context_menu_enabled = false
	output.gui_input.connect(key_input)
	_completion_hint = UI.label("", 12, Color("929bad"))
	_completion_hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	column.add_child(_completion_hint)
	context_menu = PopupMenu.new()
	add_child(context_menu)
	for item: String in ["Copier", "Coller", "Tout sélectionner", "Effacer", "Nouvelle fenêtre"]:
		context_menu.add_item(item)
	context_menu.id_pressed.connect(func(id: int) -> void:
		if id == 0: copy_selection()
		elif id == 1: paste_clipboard()
		elif id == 2: output.select_all()
		elif id == 3: output.clear()
		else: new_window.emit())

func submit(line: String) -> void:
	if (line.strip_edges().is_empty() and not input.secret) or not input.editable: return
	input.clear()
	if not input.secret:
		history.append(line)
		history_index = history.size()
		output.append_text("\n" + prompt.text + (" " if context.get("shell") in ["cmd", "powershell"] else "\n└─$ ") + line + "\n")
	else: output.append_text(prompt.text + "\n")
	if line == "clear" and not input.secret: output.clear()
	# clear part aussi au moteur : il vide l’historique sauvegardé de cette console.
	command_submitted.emit(console_id, line)

## Reprise d’une sauvegarde : le moteur renvoie le texte affiché dans cette console.
func restore_transcript(lines: Array) -> void:
	output.clear()
	if lines.is_empty(): return
	var text: PackedStringArray = []
	for line: Variant in lines: text.append(str(line))
	output.append_text("\n".join(text) + "\n")

func append_lines(lines: Array) -> void:
	for line: Variant in lines:
		if input.secret and str(line).strip_edges() == prompt.text: continue
		output.append_text(str(line) + "\n")

func set_context(value: Dictionary) -> void:
	var was_secret: bool = input.secret
	context = value
	prompt.text = ("PS " if context.get("shell") == "powershell" else "") + str(context.get("display_cwd", "C:\\Data")) + ">" if context.get("shell") in ["cmd", "powershell"] else "┌──(%s㉿%s)-[%s]" % [context.get("user", "operator"), context.get("hostname", "kali"), str(context.get("cwd", "~")).replace("/home/operator", "~")]
	input.secret = context.get("password_prompt", false)
	if input.secret != was_secret:
		input.clear()
		_completion_hint.text = ""
	if input.secret: prompt.text = str(context.get("password_label", "Password:"))
	input.placeholder_text = ""
	var inline_prompt: bool = input.secret or context.get("shell") in ["cmd", "powershell"]
	prompt.add_theme_font_size_override("font_size", 14 if inline_prompt else 13)
	if inline_prompt and prompt.get_parent() != _input_row:
		prompt.reparent(_input_row)
		_input_row.move_child(prompt, 0)
	elif not inline_prompt and prompt.get_parent() != _column:
		prompt.reparent(_column)
		_column.move_child(prompt, _input_row.get_index())
	var running: bool = context.get("foreground") != null or int(context.get("pending", 0)) > 0
	input.editable = not running
	input.visible = not running
	prompt.visible = not running
	_shell_prefix.visible = not running and not inline_prompt
	_foreground.visible = running
	_foreground.text = "Commande en cours · Ctrl+C pour interrompre · Fichier → Nouvelle fenêtre" if int(context.get("pending", 0)) > 0 else "Processus au premier plan · Ctrl+C pour l’arrêter · Fichier → Nouvelle fenêtre"

func selected_text() -> String:
	if input.has_selection() and not input.secret: return input.get_selected_text()
	return output.get_selected_text()

func copy_selection() -> void:
	var text: String = selected_text()
	if text.is_empty(): return
	if clipboard_backend != null: clipboard_backend.set_text(text)
	else: DisplayServer.clipboard_set(text)

func paste_clipboard() -> void:
	if not input.editable: return
	var text: String = clipboard_backend.get_text() if clipboard_backend != null else DisplayServer.clipboard_get()
	text = text.replace("\r\n", "\n").replace("\r", "\n")
	if not input.secret: text = text.strip_edges()
	if text.contains("\n"):
		_completion_hint.text = "Collage de plusieurs lignes : copie une seule commande, puis Entrée. La saisie a été conservée."
		return
	_completion_hint.text = ""
	input.grab_focus()
	if input.has_selection():
		var start: int = input.get_selection_from_column()
		input.remove_text(0, start, 0, input.get_selection_to_column())
		input.deselect()
		input.caret_column = start
	input.insert_text_at_caret(text)

func key_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_RIGHT and event.pressed:
		context_menu.set_item_disabled(0, selected_text().is_empty())
		context_menu.set_item_disabled(1, not input.editable)
		context_menu.position = Vector2i(get_global_mouse_position())
		context_menu.popup()
		get_viewport().set_input_as_handled()
	elif event is InputEventKey and handle_key(event):
		get_viewport().set_input_as_handled()

func handle_key(event: InputEventKey) -> bool:
	if not event.pressed or event.alt_pressed or event.meta_pressed: return false
	if event.ctrl_pressed and event.keycode == KEY_C:
		if not selected_text().is_empty() or event.shift_pressed: copy_selection()
		else: interrupted.emit(console_id)
		return true
	if event.ctrl_pressed and event.keycode == KEY_V:
		paste_clipboard()
		return true
	if event.keycode in [KEY_PAGEUP, KEY_PAGEDOWN]:
		var bar: VScrollBar = output.get_v_scroll_bar()
		output.scroll_following = false
		bar.value += maxf(bar.page * 0.85, 1.0) * (-1 if event.keycode == KEY_PAGEUP else 1)
		if bar.value >= bar.max_value - bar.page: output.scroll_following = true
		return true
	if not input.editable: return false
	if event.keycode == KEY_TAB and not event.ctrl_pressed:
		if not input.secret: completion_requested.emit(console_id, input.text, input.caret_column)
		return true
	if event.keycode in [KEY_LEFT, KEY_RIGHT, KEY_HOME, KEY_END]:
		input.grab_focus()
		var old: int = input.caret_column
		var target: int = old
		if event.keycode == KEY_HOME: target = 0
		elif event.keycode == KEY_END: target = input.text.length()
		else:
			var direction: int = -1 if event.keycode == KEY_LEFT else 1
			target = clampi(old + direction, 0, input.text.length())
			if not event.shift_pressed and input.has_selection():
				target = input.get_selection_from_column() if direction < 0 else input.get_selection_to_column()
			elif event.ctrl_pressed:
				while target > 0 and target < input.text.length() and input.text[target - (1 if direction < 0 else 0)] != " ": target += direction
		if event.shift_pressed:
			var anchor: int = old
			if input.has_selection(): anchor = input.get_selection_to_column() if old == input.get_selection_from_column() else input.get_selection_from_column()
			input.select(0, mini(anchor, target), 0, maxi(anchor, target))
		else: input.deselect()
		input.caret_column = target
		return true
	if not input.secret and event.keycode in [KEY_UP, KEY_DOWN]:
		if history_index == history.size(): _draft = input.text
		history_index = clampi(history_index + (-1 if event.keycode == KEY_UP else 1), 0, history.size())
		input.text = history[history_index] if history_index < history.size() else _draft
		input.caret_column = input.text.length()
		input.grab_focus()
		return true
	return false

func apply_completion(result: Dictionary) -> void:
	if input.secret or not input.editable: return
	if input.text != result.get("source_line", "") or input.caret_column != int(result.get("source_caret", -1)): return
	input.text = result.get("line", input.text)
	input.caret_column = int(result.get("caret", input.caret_column))
	var candidates: Array = result.get("candidates", [])
	_completion_hint.text = "  ".join(candidates) if candidates.size() > 1 else ""
	input.grab_focus()

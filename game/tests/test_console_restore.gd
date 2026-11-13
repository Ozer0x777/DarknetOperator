extends SceneTree
## Régression : à la reprise d’une sauvegarde, chaque console retrouve son texte, sans doublon.
var failures: int = 0

func check(condition: bool, message: String) -> void:
	if not condition:
		failures += 1
		push_error(message)

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	root.size = Vector2i(1440, 900)
	var desktop: Control = load("res://scenes/desktop.tscn").instantiate()
	root.add_child(desktop)
	await process_frame
	var saved: Dictionary = {
		"tick": 1, "max_ticks": 40, "status": "RUNNING", "discovered": [], "scanned": [], "hosts": [], "messages": [], "loot": [], "alerts": [], "contract": {"client": "client"}, "available_abilities": {"red": []},
		"terminals": {"main": {}, "term-2": {}},
		"history": [{"tick": 1, "team": "red", "console_id": "term-2", "message": "nmap (scan réseau) a réussi"}],
		"terminal_transcripts": {
			"main": ["", "┌──(operator㉿kali)-[~]", "└─$ pwd", "/home/operator"],
			"term-2": ["", "┌──(operator㉿kali)-[~]", "└─$ nmap -sV 10.20.0.21", "nmap: action en attente…", "[1] nmap (scan réseau) a réussi"],
		},
	}
	desktop._restore_console_windows(saved)
	await process_frame
	var main_text: String = desktop.terminal_views.main.output.get_parsed_text()
	var second: String = desktop.terminal_views["term-2"].output.get_parsed_text()
	check(main_text.contains("└─$ pwd") and main_text.contains("/home/operator"), "Console principale restaurée")
	check(second.contains("└─$ nmap -sV 10.20.0.21"), "Seconde console recréée avec son texte")
	check(second.count("nmap (scan réseau) a réussi") == 1, "Un résultat déjà dans l’historique n’est pas réaffiché")
	print("Reprise des consoles : %s échec(s)" % failures)
	quit(1 if failures else 0)

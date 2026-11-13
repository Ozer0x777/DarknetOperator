extends RefCounted
## Client transitoire du moteur de référence. Aucun outil système n'est exécuté.
## L'interface et le protocole restent distincts pour permettre le portage natif.
signal updated(state: Dictionary)
signal social_updated(data: Dictionary)
signal completion_ready(console_id: String, result: Dictionary)
signal terminal_output(console_id: String, lines: Array)
signal failure(message: String)
signal context_updated(console_id: String, context: Dictionary)
signal open_url(url: String)

var base_url: String = "http://127.0.0.1:8001"
var game_id: String = ""
var state: Dictionary = {}
var contracts: Array = []
var handle: String = ""
var busy: bool = false
var _engine_pid: int = 0
var request_transport: RefCounted = null
var _owner: Node
var _socket: WebSocketPeer = WebSocketPeer.new()
var _history_seen: Dictionary = {}
var _retry_seconds: float = 0.0
var _social_seconds: float = 0.0
var _social_pending: bool = false
var _state_pending: bool = false
const SOCKET_BUFFER_BYTES: int = 16 * 1024 * 1024

func _init(owner_node: Node) -> void:
	_owner = owner_node
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--api="):
			base_url = arg.trim_prefix("--api=").trim_suffix("/")

## expect : type JSON attendu en cas de succès. Presque toutes les routes renvoient un
## dictionnaire ; celles qui renvoient une liste le précisent avec TYPE_ARRAY.
func request(path: String, payload: Variant = null, expect: int = TYPE_DICTIONARY) -> Dictionary:
	if request_transport != null: return request_transport.request(path, payload)
	var http: HTTPRequest = HTTPRequest.new()
	_owner.add_child(http)
	http.timeout = 8.0
	var method: int = HTTPClient.METHOD_GET if payload == null else HTTPClient.METHOD_POST
	var err: Error = http.request(base_url + path, ["Content-Type: application/json"], method, "" if payload == null else JSON.stringify(payload))
	if err != OK:
		http.queue_free()
		return {"error": "Impossible de contacter le moteur (%s)." % err}
	var response: Array = await http.request_completed
	http.queue_free()
	return parse_response(response[0], int(response[1]), response[3].get_string_from_utf8(), expect)

## Transforme une réponse HTTP en {"data": …} ou {"error": …}. Les appelants lisent directement
## result.data : une réponse vide, illisible ou du mauvais type est donc toujours une erreur.
static func parse_response(result_code: int, http_code: int, body: String, expect: int = TYPE_DICTIONARY) -> Dictionary:
	if result_code != HTTPRequest.RESULT_SUCCESS:
		return {"error": "Le moteur ne répond pas. Vérifie le lanceur et la connexion locale."}
	var parsed: Variant = null
	if not body.strip_edges().is_empty():
		var json: JSON = JSON.new()
		if json.parse(body) == OK: parsed = json.data
	if http_code >= 400:
		return {"error": str(parsed.get("detail", "Erreur du moteur")) if parsed is Dictionary else "Erreur HTTP %s" % http_code}
	if typeof(parsed) != expect:
		return {"error": "Réponse du moteur illisible. Relance le jeu si le problème persiste."}
	return {"data": parsed}

func bootstrap() -> bool:
	var result: Dictionary = await request("/api/contracts", null, TYPE_ARRAY)
	if result.has("error"):
		failure.emit(result.error)
		return false
	contracts = result.data
	var handles: Dictionary = await request("/api/handles")
	if handles.has("error"):
		failure.emit(handles.error)
		return false
	handle = handles.data.handles[0]
	return true

func start(contract_id: String) -> bool:
	if busy:
		return false
	busy = true
	var result: Dictionary = await request("/api/games", {"contract": contract_id, "handle": handle, "tick_interval": 2.0})
	if result.has("error"):
		busy = false
		failure.emit(result.error)
		return false
	game_id = result.data.id
	handle = result.data.state.get("player_handle", handle)
	_history_seen.clear()
	apply_state(result.data.state)
	var started: Dictionary = await request("/api/games/%s/start" % game_id, {})
	busy = false
	if started.has("error"):
		# Partie non démarrée : les commandes repartent vers le bureau, pas vers un identifiant mort.
		game_id = ""
		failure.emit(started.error)
		return false
	if result.data.get("resumed", false):
		var resumed: Dictionary = await request("/api/games/%s/resume" % game_id, {})
		if resumed.has("error"):
			failure.emit(resumed.error)
			return false
	connect_socket()
	return true

func command(line: String, console_id: String = "main", interrupt: bool = false) -> void:
	var path: String = "/api/workspace/terminal" if game_id.is_empty() else "/api/games/%s/terminal" % game_id
	var result: Dictionary = await request(path, {"line": line, "console_id": console_id, "interrupt": interrupt})
	if result.has("error"):
		terminal_output.emit(console_id, ["Erreur : " + str(result.error)])
	else:
		context_updated.emit(console_id, result.data.get("context", {}))
		terminal_output.emit(console_id, result.data.output)
		if result.data.has("state"): apply_state(result.data.state)
		if result.data.get("open_url") != null: open_url.emit(result.data.open_url)

func close_console(console_id: String) -> void:
	var path: String = "/api/workspace/terminals/" + console_id if game_id.is_empty() else "/api/games/%s/terminals/%s" % [game_id, console_id]
	var http: HTTPRequest = HTTPRequest.new()
	_owner.add_child(http)
	http.timeout = 5
	if http.request(base_url + path, [], HTTPClient.METHOD_DELETE) == OK:
		await http.request_completed
	http.queue_free()

## Renvoie true si le moteur a accepté l’action.
func control(action: String) -> bool:
	if game_id.is_empty():
		return false
	var result: Dictionary = await request("/api/games/%s/%s" % [game_id, action], {})
	if result.has("error"):
		failure.emit(result.error)
		return false
	if action == "disconnect":
		apply_state(result.data)
	return true

func connect_socket() -> void:
	if request_transport != null: return
	_socket.close()
	_socket = WebSocketPeer.new()
	# L'état final d'une mission (débriefing complet) dépasse largement les 64 Ko par défaut :
	# au-delà du tampon, Godot ferme la connexion (code 1009) sans rien livrer.
	_socket.inbound_buffer_size = SOCKET_BUFFER_BYTES
	var url: String = base_url.replace("https://", "wss://").replace("http://", "ws://")
	var err: Error = _socket.connect_to_url(url + "/ws/games/" + game_id)
	if err != OK:
		failure.emit("Connexion temps réel indisponible (%s)." % err)

func poll(delta: float) -> void:
	if request_transport != null: return
	if not "--offline-test" in OS.get_cmdline_user_args():
		_social_seconds += delta
		if _social_seconds >= 6.0 and not _social_pending:
			_social_seconds = 0.0
			refresh_social()
	if game_id.is_empty():
		return
	_socket.poll()
	if _socket.get_ready_state() == WebSocketPeer.STATE_OPEN:
		while _socket.get_available_packet_count() > 0:
			var data: Variant = JSON.parse_string(_socket.get_packet().get_string_from_utf8())
			if data is Dictionary:
				apply_state(data)
	elif _socket.get_ready_state() == WebSocketPeer.STATE_CLOSED:
		_retry_seconds += delta
		if _retry_seconds >= 3.0 and state.get("status") == "RUNNING":
			_retry_seconds = 0.0
			connect_socket()
			# Filet de sécurité : l'état est aussi relu par HTTP, qui n'a pas de limite de taille.
			# Une fin de mission est ainsi toujours apprise, même si le temps réel reste coupé.
			refresh_state()

func refresh_state() -> void:
	if _state_pending or game_id.is_empty(): return
	_state_pending = true
	var requested: String = game_id
	var result: Dictionary = await request("/api/games/%s" % requested)
	_state_pending = false
	if not result.has("error") and requested == game_id: apply_state(result.data)

## Changement de partie : les identifiants d’historique sont des index propres à chaque partie.
func clear_history_seen() -> void:
	_history_seen.clear()

## Les résultats déjà présents dans l’historique restauré des consoles ne sont pas réaffichés.
func mark_history_seen(data: Dictionary) -> void:
	for entry: Dictionary in data.get("history", []):
		_history_seen[str(entry.get("id", "%s|%s|%s" % [entry.get("console_id", "main"), entry.tick, entry.message]))] = true

func apply_state(data: Dictionary) -> void:
	state = data
	var history: Array = data.get("history", []).duplicate()
	history.reverse()
	for entry: Dictionary in history:
		if entry.get("team") != "red":
			continue
		var key: String = str(entry.get("id", "%s|%s|%s" % [entry.get("console_id", "main"), entry.tick, entry.message]))
		if not _history_seen.has(key):
			_history_seen[key] = true
			terminal_output.emit(entry.get("console_id", "main"), ["[%s] %s" % [entry.tick, entry.message]])
	updated.emit(state)

func ensure_engine() -> bool:
	# Dans un paquet exporté, le moteur autonome est livré à côté du jeu.
	# En développement, scripts/launch.py gère le processus moteur.
	if OS.has_feature("template"):
		var binary: String = OS.get_executable_path().get_base_dir().path_join("engine/redteam-engine/redteam-engine")
		if OS.get_name() == "Windows":
			binary += ".exe"
		if not FileAccess.file_exists(binary):
			failure.emit("Moteur autonome absent du paquet : " + binary)
			return false
		var probe: TCPServer = TCPServer.new()
		if probe.listen(0, "127.0.0.1") != OK:
			failure.emit("Impossible de réserver un port local pour le moteur.")
			return false
		var port: int = probe.get_local_port()
		probe.stop()
		base_url = "http://127.0.0.1:%s" % port
		_engine_pid = OS.create_process(binary, PackedStringArray(["--port", str(port)]))
		if _engine_pid < 0:
			failure.emit("Le moteur autonome n'a pas pu démarrer.")
			return false
		for attempt: int in range(40):
			await _owner.get_tree().create_timer(0.25).timeout
			var result: Dictionary = await request("/api/health")
			if not result.has("error"):
				return true
		failure.emit("Le moteur autonome n'a pas répondu au lancement.")
		return false
	return true

func shutdown() -> void:
	_socket.close()
	if _engine_pid > 0 and OS.is_process_running(_engine_pid):
		OS.kill(_engine_pid)

func complete(line: String, caret: int, console_id: String) -> void:
	var path: String = "/api/workspace/terminal/complete" if game_id.is_empty() else "/api/games/%s/terminal/complete" % game_id
	var result: Dictionary = await request(path, {"line": line, "caret": caret, "console_id": console_id})
	if not result.has("error"): completion_ready.emit(console_id, result.data)

func refresh_social() -> void:
	if _social_pending: return
	_social_pending = true
	var result: Dictionary = await request("/api/social")
	_social_pending = false
	if not result.has("error"): social_updated.emit(result.data)

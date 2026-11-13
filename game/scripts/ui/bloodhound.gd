extends VBoxContainer
const UI = preload("res://scripts/ui/style.gd")
class GraphCanvas extends Control:
	var nodes: Array = []
	var edges: Array = []
	var positions: Dictionary = {}
	func set_graph(items: Array, relations: Array, query: String) -> void:
		for child: Node in get_children():
			remove_child(child)
			child.queue_free()
		nodes.clear()
		edges.clear()
		positions.clear()
		for item: Dictionary in items:
			if not query.is_empty() and not str(item.get("name", "")).to_lower().contains(query.to_lower()): continue
			var index: int = nodes.size()
			var origin: Vector2 = Vector2(24+(index % 2)*330,24+(index / 2)*144)
			positions[item.id] = origin
			nodes.append(item)
			var card: PanelContainer = UI.panel(Color("263349"),12,7)
			card.position = origin
			card.custom_minimum_size = Vector2(260,80)
			card.size = Vector2(260,80)
			card.tooltip_text = str(item.id)
			var box: VBoxContainer = VBoxContainer.new()
			card.add_child(box)
			box.add_child(UI.label(str(item.get("kind","objet")),11,Color("91a2ba")))
			box.add_child(UI.wrapped(str(item.get("name","")),13))
			add_child(card)
		for edge: Dictionary in relations:
			if positions.has(edge.source) and positions.has(edge.target): edges.append(edge)
		custom_minimum_size = Vector2(640,maxi(220,((nodes.size()+1)/2)*144+32))
		queue_redraw()
	func _draw() -> void:
		for edge: Dictionary in edges:
			var start: Vector2 = positions[edge.source]+Vector2(130,80)
			var end: Vector2 = positions[edge.target]+Vector2(130,0)
			var tint: Color = Color("73b4ed")
			draw_line(start,end,tint,2,true)
			var direction: Vector2 = (end-start).normalized()
			var normal: Vector2 = Vector2(-direction.y,direction.x)
			draw_colored_polygon(PackedVector2Array([end,end-direction*10+normal*5,end-direction*10-normal*5]),tint)
			draw_string(UI.FONT,(start+end)/2+Vector2(5,-5),str(edge.get("type","")),HORIZONTAL_ALIGNMENT_LEFT,-1,11,tint)
var session: RefCounted
var files: OptionButton
var status: Label
var graph: GraphCanvas
var search: LineEdit
var _data: Dictionary = {}
func setup(value: RefCounted) -> void:
	session = value
	add_theme_constant_override("separation",10)
	add_child(UI.label("BloodHound · Analyse de la collecte",20))
	var row: HBoxContainer = HBoxContainer.new()
	add_child(row)
	files = OptionButton.new()
	files.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	files.clip_text = true
	row.add_child(files)
	row.add_child(UI.button("Actualiser",refresh))
	row.add_child(UI.button("Importer la collecte",_import))
	status = UI.wrapped("Récupère l’archive SharpHound dans ~/loot, puis importe-la.",13)
	add_child(status)
	search = LineEdit.new()
	search.placeholder_text = "Rechercher un compte, groupe ou ordinateur"
	search.text_changed.connect(func(_text: String) -> void: _render())
	add_child(search)
	var scroll: ScrollContainer = ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.custom_minimum_size = Vector2(400,220)
	add_child(scroll)
	graph = GraphCanvas.new()
	scroll.add_child(graph)
func refresh() -> void:
	if session.game_id.is_empty():
		status.text = "Ouvre le dossier de collecte pour examiner ses données."
		return
	var result: Dictionary = await session.request("/api/games/"+session.game_id+"/bloodhound")
	if result.has("error"):
		status.text = str(result.error)
		return
	apply_data(result.data)
func _import() -> void:
	if files.selected < 0 or session.game_id.is_empty(): return
	var result: Dictionary = await session.request("/api/games/"+session.game_id+"/bloodhound/import",{"path":files.get_item_text(files.selected)})
	if result.has("error"):
		status.text = str(result.error)
		return
	apply_data(result.data)
func apply_data(value: Dictionary) -> void:
	_data = value.duplicate(true)
	files.clear()
	for path: String in _data.get("files",[]): files.add_item(path)
	status.text = "Source : %s · %s objets · %s relations. Une relation doit être vérifiée avant d’en déduire un accès." % [_data.get("source","aucune collecte importée"),_data.get("nodes",[]).size(),_data.get("edges",[]).size()]
	if _data.get("stale",false): status.text += " Collecte d’un dossier précédent : les droits sont à revérifier."
	_render()
func _render() -> void:
	graph.set_graph(_data.get("nodes",[]),_data.get("edges",[]),search.text)

"""Aperçus vectoriels tirés des positions de la scène Godot, sans capture GPU."""
from pathlib import Path
import base64
import argparse
import html
import json
import os
import shutil
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--only', nargs='+', help='Noms des vues à rendre, sans extension ; export de géométrie complet.')
args = parser.parse_args()
ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'build/ui-previews'
godot=os.environ.get('GODOT') or shutil.which('godot') or shutil.which('godot4')
if not godot: raise SystemExit('Godot 4 est requis pour construire les aperçus.')
subprocess.run([os.environ.get('PYTHON', str(ROOT/'backend/.venv/bin/python')), str(ROOT/'backend/export_world_preview.py'), str(ROOT/'build/validation/social-preview.json')], check=True)
result=subprocess.run([godot,'--headless','--path',str(ROOT/'game'),'--script','tests/preview_desktop.gd','--','--offline-test'],capture_output=True,text=True,timeout=45)
print(result.stdout,end='')
if result.returncode or 'ERROR:' in result.stderr:
    raise SystemExit(result.stderr or result.returncode)


def color(value):
    return value[:7],int(value[7:9],16)/255 if len(value)==9 else 1


def image_data(path):
    source=ROOT/'game'/path.removeprefix('res://')
    if not source.is_file():return ''
    mime = 'image/png' if source.suffix.lower() == '.png' else 'image/svg+xml'
    return 'data:'+mime+';base64,'+base64.b64encode(source.read_bytes()).decode()


def render(path):
    data=json.loads(path.read_text())
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{data["width"]}" height="{data["height"]}" viewBox="0 0 {data["width"]} {data["height"]}">', '<rect width="100%" height="100%" fill="#101622"/>']
    for family,filename,mime in [('Cantarell','Cantarell.otf','font/otf'),('DejaVu Sans Mono','DejaVuSansMono.ttf','font/ttf')]:
        font64=base64.b64encode((ROOT/'game/assets/fonts'/filename).read_bytes()).decode()
        parts.append(f'<style>@font-face{{font-family:"{family}";src:url(data:{mime};base64,{font64})}}</style>')
    for index,node in sorted(enumerate(data['nodes']),key=lambda item:item[1]['z']):
        x,y,w,h=node['rect'];cx,cy,cw,ch=node['clip']
        if w<=0 or h<=0 or cw<=0 or ch<=0:continue
        parts.append(f'<defs><clipPath id="c{index}"><rect x="{cx}" y="{cy}" width="{cw}" height="{ch}"/></clipPath></defs><g clip-path="url(#c{index})">')
        for edge in node.get('graph_edges', []):
            sx,sy=edge['from'];tx,ty=edge['to']
            parts.append(f'<defs><marker id="arrow{index}" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8" fill="#73b4ed"/></marker></defs><path d="M{sx},{sy} L{tx},{ty}" stroke="#73b4ed" stroke-width="2" marker-end="url(#arrow{index})"/><text x="{(sx+tx)/2+5}" y="{(sy+ty)/2-5}" fill="#73b4ed" font-size="11" font-family="Cantarell">{html.escape(edge["label"])}</text>')
        if 'background' in node:
            bg,alpha=color(node['background']);border,ba=color(node.get('border','#00000000'))
            parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{node.get("radius",0)}" fill="{bg}" fill-opacity="{alpha}" stroke="{border}" stroke-opacity="{ba}" stroke-width="{node.get("border_width",0)}"/>')
        if node.get('image'):
            if node.get('round_avatar'):
                parts.append(f'<defs><clipPath id="avatar{index}"><ellipse cx="{x+w/2}" cy="{y+h/2}" rx="{w/2}" ry="{h/2}"/></clipPath></defs><g clip-path="url(#avatar{index})">')
            if node.get('atlas_region'):
                ax,ay,aw,ah=node['atlas_region']
                parts.append(f'<svg x="{x}" y="{y}" width="{w}" height="{h}" viewBox="{ax} {ay} {aw} {ah}" preserveAspectRatio="xMidYMid meet"><image href="{image_data(node["image"])}" width="{node["atlas_size"][0]}" height="{node["atlas_size"][1]}"/></svg>')
            else:
                parts.append(f'<image href="{image_data(node["image"])}" x="{x}" y="{y}" width="{w}" height="{h}" preserveAspectRatio="xMidYMid {"slice" if node.get("cover") else "meet"}"/>')
        if node.get('image') and node.get('round_avatar'): parts.append('</g>')
        if 'slider' in node:
            slider=node['slider']; fraction=(slider['value']-slider['min'])/max(1,slider['max']-slider['min'])
            knob=x+6+(w-12)*fraction; cy=y+h/2
            parts.append(f'<rect x="{x+6}" y="{cy-2}" width="{max(0,w-12)}" height="4" rx="2" fill="#465568"/><rect x="{x+6}" y="{cy-2}" width="{max(0,knob-x-6)}" height="4" rx="2" fill="#72a9de"/><circle cx="{knob}" cy="{cy}" r="6" fill="#dce4ef" stroke="#8caccb"/>')
        for item in node.get('items',[]):
            rx,ry,rw,rh=item['rect'];rx+=x;ry+=y
            if item.get('selected'):parts.append(f'<rect x="{rx}" y="{ry}" width="{rw}" height="{rh}" rx="3" fill="#355270"/>')
            if item.get('icon'):parts.append(f'<image href="{image_data(item["icon"])}" x="{rx+(rw-48)/2}" y="{ry+4}" width="48" height="48"/>')
            if item.get('icon'):
                parts.append(f'<text x="{rx+rw/2}" y="{ry+67}" text-anchor="middle" font-family="Cantarell" font-size="13" fill="#dce4ef">{html.escape(item["text"])}</text>')
            else:
                parts.append(f'<text x="{rx+8}" y="{ry+18}" font-family="Cantarell" font-size="14" fill="#dce4ef">{html.escape(item["text"])}</text>')
        left,top,right,bottom=node.get('margins',[0,0,0,0])
        ix=0
        if node.get('icon'):
            ix=min(node.get('icon_size',22) or 22,h-4)
            parts.append(f'<image href="{image_data(node["icon"])}" x="{x+left}" y="{y+(h-ix)/2}" width="{ix}" height="{ix}"/>')
        if node.get('text'):
            size=node.get('font_size',14);ascent=node.get('ascent',size);lineheight=node.get('height',size*1.2)
            lines=node.get('lines',[node['text']]);ty=y+top+ascent
            if node.get('valign')==1:ty=y+(h-len(lines)*lineheight)/2+ascent
            tx=x+left+(ix+4 if ix else 0);anchor='start'
            if node.get('align')==1:tx=x+w/2+(ix/2 if ix else 0);anchor='middle'
            elif node.get('align')==2:tx=x+w-right;anchor='end'
            font='DejaVu Sans Mono' if 'Mono' in node.get('font','') else 'Cantarell'
            fill,alpha=color(node.get('color','#dcdee4ff'))
            for i,line in enumerate(lines):
                parts.append(f'<text x="{tx}" y="{ty+i*lineheight}" font-family="{font}" font-size="{size}" fill="{fill}" fill-opacity="{alpha}" text-anchor="{anchor}">{html.escape(str(line))}</text>')
        parts.append('</g>')
    parts.append('</svg>')
    target=path.with_suffix('.svg');target.write_text(''.join(parts))
    converter=shutil.which('rsvg-convert')
    if converter:subprocess.run([converter,'-o',str(path.with_suffix('.png')),str(target)],check=True)
    return target.name

images=[render(path) for path in sorted(OUTPUT.glob('*.json')) if not args.only or path.stem in args.only]
gallery='<!doctype html><html lang="fr"><meta charset="utf-8"><title>RedTeamSimulator - revue des interfaces</title><style>body{margin:32px;background:#111622;color:#dce4ef;font:16px system-ui}img{width:100%;border:1px solid #40516b;border-radius:6px}figure{margin:32px 0}a{color:#85c6ff}</style><h1>RedTeamSimulator - interfaces</h1><p>Aperçus vectoriels issus de la géométrie de la scène Godot. Ce ne sont pas des captures du rendu GPU.</p>'
for name in images:gallery+=f'<figure><figcaption>{html.escape(name)}</figcaption><a href="{name}"><img src="{name}"></a></figure>'
(OUTPUT/'index.html').write_text(gallery+'</html>')
print(OUTPUT/'index.html')

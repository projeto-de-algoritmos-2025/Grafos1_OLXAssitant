from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
import os
import json
import io
import hashlib
import time
from grafo import GrafoOlx
from interactive_graph import create_interactive_graph

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Necessário fazer cache devido ao peso do grafo e das imagens
CACHE_DIR = 'visualization_cache'
CACHE_EXPIRY = 3600
os.makedirs(CACHE_DIR, exist_ok=True)

# Inicializa o grafo
mg = GrafoOlx('motos_data.json')

@app.route('/')
def index():
    return 

@app.route('/listings')
def get_listings():
    state = request.args.get('state', '')
    brand = request.args.get('brand', '')
    
    filtered_listings = mg.listings
    
    if state:
        filtered_listings = [m for m in filtered_listings if m['estado'] == state]
    
    if brand:
        filtered_listings = [m for m in filtered_listings if m['marca'] == brand]
    
    # Ordena por preço
    filtered_listings = sorted(filtered_listings, key=lambda m: m.get('price_value', 0))
    
    # Mapeia 'imagens' para 'images' para consistência
    for m in filtered_listings:
        if 'imagens' in m and 'images' not in m:
            m['images'] = m['imagens']
    
    return jsonify(filtered_listings)

@app.route('/listing/<int:listing_id>')
def get_listing(listing_id):
    # Converte listing_id para string para depuração
    str_id = str(listing_id)
   
    # Agora tenta a busca regular
    for m in mg.listings:
        # Tenta múltiplas comparações para capturar casos especiais
        if m['listId'] == listing_id:
            if 'imagens' in m and 'images' not in m:
                m['images'] = m['imagens']
            return jsonify(m)
        elif str(m['listId']) == str_id:
            if 'imagens' in m and 'images' not in m:
                m['images'] = m['imagens']
            return jsonify(m)
    
    return jsonify({'error': 'Anúncio não encontrado'}), 404

@app.route('/communities')
def communities_page():
    partition = mg.detect_communities()
    
    # Calcula estatísticas para cada comunidade
    communities = {}
    for node, community_id in partition.items():
        if community_id not in communities:
            communities[community_id] = []
        
        communities[community_id].append(mg.G.nodes[node])
    
    # Ordena por tamanho (maior primeiro)
    sorted_communities = sorted(communities.items(), key=lambda x: len(x[1]), reverse=True)
    
    return render_template('communities.html', communities=sorted_communities)


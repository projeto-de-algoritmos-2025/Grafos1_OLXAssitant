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

@app.route('/similar/<int:listing_id>')
def get_similar(listing_id):
    listing = None
    for m in mg.listings:
        if m['listId'] == listing_id or str(m['listId']) == str(listing_id):
            listing = m
            break
    
    if not listing:
        return jsonify([])
        
    similar = mg.get_similar_listings(listing['listId'])
    
    full_similar = []
    for s in similar:
        for m in mg.listings:
            if m['listId'] == s['id'] or str(m['listId']) == str(s['id']):
                if 'imagens' in m and 'images' not in m:
                    m['images'] = m['imagens']
                
                full_similar.append({**s, **m})
                break
    return jsonify(full_similar)

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

@app.route('/interactive-graph')
def interactive_graph():
    return render_template('interactive_graph.html')

@app.route('/api/graph-data')
def get_graph_data():
    # Filtra conforme necessário
    state = request.args.get('state', '')
    brand = request.args.get('brand', '')
    color_by = request.args.get('color_by', 'community')
    
    # Obtém os dados do grafo
    graph_data = mg.create_interactive_graph_data(color_by)
    
    # Cria grafo interativo
    fig, config = create_interactive_graph(graph_data, color_by)
    
    # Converte para JSON
    graph_json = fig.to_json()
    
    return jsonify({
        'graph': json.loads(graph_json),
        'config': config
    })

@app.route('/api/node/<int:node_id>')
def get_node_info(node_id):
    # Obter dados do nó
    print(f"API - Buscando informações para nó ID: {node_id} (tipo: {type(node_id)})")
    
    # Verificar se o nó existe diretamente no grafo
    node_exists = node_id in mg.G.nodes
    print(f"Nó existe no grafo diretamente? {node_exists}")
    
    # Tentar conversão de string se necessário
    str_id = str(node_id)
    str_exists = any(str(n) == str_id for n in mg.G.nodes)
    print(f"Nó existe como string? {str_exists}")
    
    # Mostrar alguns IDs de nós do grafo para depuração
    node_sample = list(mg.G.nodes)[:5]
    print(f"Amostra de IDs de nós no grafo: {node_sample} (tipos: {[type(n) for n in node_sample]})")
    
    # Se o nó não existe por ID direto, tentar encontrá-lo por comparação de string
    if not node_exists:
        for graph_node_id in mg.G.nodes:
            if str(graph_node_id) == str_id:
                print(f"Encontrado nó por comparação de string: {graph_node_id}")
                node_id = graph_node_id  # Usar o ID do nó real do grafo
                node_exists = True
                break
    
    # Obter dados do nó com nós similares usando nossa implementação personalizada
    node_data = mg.get_node_data_with_similar(node_id)
    
    if 'error' in node_data:
        print(f"Erro ao obter dados do nó: {node_data['error']}")
        return jsonify(node_data), 404
    
    # Adicionar o ID do nó à resposta para referência
    if 'node_data' in node_data and node_data['node_data']:
        node_data['node_id'] = str(node_id)  # Garantir que node_id seja uma string para consistência
    
    # Para cada nó similar, garantir que tenha um campo id para destaque
    if 'similar_nodes' in node_data and node_data['similar_nodes']:
        for node in node_data['similar_nodes']:
            if 'listId' in node and 'id' not in node:
                node['id'] = str(node['listId'])  # Converter para string para consistência
            elif 'id' in node:
                node['id'] = str(node['id'])  # Converter id existente para string
    
    print(f"Retornando com sucesso dados para o nó {node_id}")
    return jsonify(node_data)


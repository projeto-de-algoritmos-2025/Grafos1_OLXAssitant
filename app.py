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
    num_listings = len(mg.listings)
    num_nodes = mg.G.number_of_nodes()
    num_edges = mg.G.number_of_edges()
    
    # Obtém estados e marcas para filtragem
    states = sorted(list(set([m['estado'] for m in mg.listings if m['estado']])))
    brands = sorted(list(set([m['marca'] for m in mg.listings if m['marca']])))
    
    return render_template('index.html', 
                           num_listings=num_listings,
                           num_nodes=num_nodes,
                           num_edges=num_edges,
                           states=states,
                           brands=brands)

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

@app.route('/search')
def search():
    query = request.args.get('q', '')
    if not query:
        return jsonify([])
    
    results = mg.search_listings(query)
    
    valid_results = []
    for result in results:
        listing = result['listing']
        listing_id = listing.get('listId')
        
        # Converte para string para comparação
        str_id = str(listing_id)
        
        for m in mg.listings:
            if m['listId'] == listing_id or str(m['listId']) == str_id:
                result['listing'] = m
                valid_results.append(result)
                break
    return jsonify(valid_results)

@app.route('/visualize')
def visualize():
    visualization_type = request.args.get('type', 'graph')
    color_by = request.args.get('color_by', 'community')
    highlight_id = request.args.get('highlight_id', None)
    
    # Remove o parâmetro de timestamp se presente (usado para evitar cache do navegador)
    params = {k: v for k, v in request.args.items() if k != '_'}
    
    # Cria uma chave de cache a partir dos parâmetros da requisição
    cache_key = hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()
    cache_path = os.path.join(CACHE_DIR, f"{cache_key}.png")
    
    # Verifica se existe cache válida
    if os.path.exists(cache_path):
        cache_age = time.time() - os.path.getmtime(cache_path)
        if cache_age < CACHE_EXPIRY:
            # Retorna imagem salva em cache
            return send_file(cache_path, mimetype='image/png')
    
    # Converte highlight_id para int se necessário
    if highlight_id and highlight_id.isdigit():
        highlight_id = int(highlight_id)
    else:
        highlight_id = None
    
    # Gera a visualização
    if visualization_type == 'graph':
        plt = mg.create_interactive_graph_data(highlight_id=highlight_id, color_by=color_by)
    elif visualization_type == 'state':
        plt = mg.visualize_state_distribution()
    elif visualization_type == 'brand':
        plt = mg.visualize_brand_distribution()
    elif visualization_type == 'price':
        plt = mg.visualize_price_distribution()
    else:
        plt = mg.visualize_graph()
    
    # Salva em cache
    plt.savefig(cache_path, format='png')
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    
    plt.close()
    
    return send_file(buf, mimetype='image/png')

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

if __name__ == '__main__':
    app.run(debug=True) 
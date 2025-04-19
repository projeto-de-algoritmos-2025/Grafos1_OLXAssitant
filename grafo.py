import json
import numpy as np
from collections import defaultdict

class Grafo:
    """Implementação simples de grafos com representação em dicionários e algoritmos de comunidade para classificação de nós e cálculo de similaridades"""
    
    def __init__(self):
        # Dicionário para armazenar nós {node_id: {attributes}}
        self.nodes = {}
        # Dicionário para armazenar arestas {node_id: {neighbor_id: {attributes}}}
        self.edges = defaultdict(dict)
    
    def __iter__(self):
        return iter(self.nodes)
    
    def add_node(self, node_id, **attributes):
        # Adiciona um nó com atributos ao grafo
        self.nodes[node_id] = attributes
    
    def add_edge(self, node1, node2, **attributes):
        # Adiciona uma aresta entre node1 e node2 com atributos
        self.edges[node1][node2] = attributes
        self.edges[node2][node1] = attributes  # Grafo não direcionado
    
    def neighbors(self, node_id):
        # Obtém vizinhos de um nó
        return self.edges[node_id].keys()
    
    def number_of_nodes(self):
        # Obtém o número de nós no grafo
        return len(self.nodes)
    
    def number_of_edges(self):
        # Obtém o número de arestas no grafo
        return sum(len(neighbors) for neighbors in self.edges.values()) // 2  # Divide por 2 para grafo não direcionado
    
    def detect_communities(self):
        
        # Cria comunidade
        
        # Inicializa cada nó para sua própria comunidade
        communities = {node: i for i, node in enumerate(self.nodes)}
        
        # Conecta nós em comunidades
        for node in self.nodes:
            for neighbor in self.neighbors(node):
                if communities[node] != communities[neighbor]:
                    old_community = communities[neighbor]
                    new_community = communities[node]
                    for n in self.nodes:
                        if communities[n] == old_community:
                            communities[n] = new_community
        
        # Cria mapa de comunidades
        unique_communities = set(communities.values())
        community_map = {old: new for new, old in enumerate(unique_communities)}
        return {node: community_map[comm] for node, comm in communities.items()}
        
    def get_edges(self):
        # Obtém todas as arestas no grafo
        edges = []
        for node1 in self.nodes:
            for node2 in self.edges[node1]:
                if node1 < node2:  # Para evitar duplicatas no grafo não direcionado
                    edges.append((node1, node2, self.edges[node1][node2]))
        return edges
        
    def kamada_kawai_layout(self, iterations=20): 
        # Layout Kamada-Kawai: algoritmo de layout de grafo baseado em forças 
        # -> importante para visualização de grafos e classificação de comunidades
        
        # Inicializa com posições aleatórias
        positions = {node: (np.random.rand(), np.random.rand()) for node in self.nodes}
        
        # Parâmetros
        k = 0.1  # Distância ideal entre nós
        
        # Lista de nós para evitar repetições quando se calcula as forças
        nodes = list(self.nodes.keys())
        node_count = len(nodes)
        
        # Skip factor - apenas calcula forças para um subconjunto de pares de nós
        skip_factor = max(1, node_count // 100)  # Ajusta com base no número de nós
        
        # Iterações do algoritmo de Kamada-Kawai
        for _ in range(iterations):
            for i in range(0, node_count, skip_factor):
                node1 = nodes[i]
                for j in range(0, node_count, skip_factor):
                    node2 = nodes[j]
                    if node1 != node2:
                        # Get positions
                        pos1 = positions[node1]
                        pos2 = positions[node2]
                        
                        dx = pos1[0] - pos2[0]
                        dy = pos1[1] - pos2[1]
                        distance = max(0.1, np.sqrt(dx*dx + dy*dy))
                        
                        force = min(k*k / distance, 5.0) 
                        if np.isfinite(force):
                            factor = dx*force*0.05, dy*force*0.05
                            positions[node1] = (pos1[0] + factor[0], pos1[1] + factor[1])
            
            # Calcula forças atrativas entre nós conectados (sempre processa todas as arestas)
            for node1 in nodes:
                neighbors = list(self.neighbors(node1))
                for node2 in neighbors:
                    pos1 = positions[node1]
                    pos2 = positions[node2]
                    
                    dx = pos1[0] - pos2[0]
                    dy = pos1[1] - pos2[1]
                    distance = max(0.1, np.sqrt(dx*dx + dy*dy))
                    
                    force = min(distance*distance / k, 5.0) 
                    if np.isfinite(force):
                        factor = dx*force*0.05, dy*force*0.05
                        positions[node1] = (pos1[0] - factor[0], pos1[1] - factor[1])
                        positions[node2] = (pos2[0] + factor[0], pos2[1] + factor[1])
        
        return positions

class GrafoOlx:
    def __init__(self, data_file):
        self.data_file = data_file
        self.listings = []
        self.G = Grafo()
        self.layout_cache = {}
        self.load_data()
        self.build_graph()
        
    def load_data(self):
        """Carrega json da olx"""
        with open(self.data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Filtra entradas nulas
        self.listings = [m for m in data if m['listId'] is not None]
        
        # Limpa dados de preço
        for m in self.listings:
            if m['price'] and isinstance(m['price'], str):
                m['price_value'] = float(m['price'].replace('R$ ', '').replace('.', '').replace(',', '.'))
            else:
                m['price_value'] = 0.0
                
            # Converte quilometragem para numérico
            if m['quilometragem'] and m['quilometragem'].isdigit():
                m['km'] = int(m['quilometragem'])
            else:
                m['km'] = 0
                
            # Mapeia 'imagens' para 'images' para manter as keys em inglês
            if 'imagens' in m and 'images' not in m:
                m['images'] = m['imagens']
    
    def build_graph(self):
        """Cria o grafo com anúncios como nós e similaridades como arestas"""

        for m in self.listings:
            self.G.add_node(m['listId'], **m)
        
        # Calcula similaridades e adiciona arestas para anúncios com similaridade e peso
        for i, m1 in enumerate(self.listings):
            for j, m2 in enumerate(self.listings[i+1:], i+1):
                similarity = self.calculate_similarity(m1, m2)
                if similarity > 0.7:
                    self.G.add_edge(m1['listId'], m2['listId'], weight=similarity)
    
    def calculate_similarity(self, m1, m2):
        """Calcula similaridade entre dois anúncios"""
        similarity = 0.0
    
        if m1['marca'] == m2['marca']:
            similarity += 0.1
            
        if m1['modelo'] == m2['modelo']:
            similarity += 0.3
        
        
        if m1['cilindrada'] == m2['cilindrada']:
            similarity += 0.4
        else:
            
            try:
                cil1 = int(''.join(filter(str.isdigit, str(m1['cilindrada']))))
                cil2 = int(''.join(filter(str.isdigit, str(m2['cilindrada']))))
                if cil1 <= cil2 * 1.5:
                    similarity += 0.3
                elif cil1 >= cil2 * 0.5:
                    similarity += 0.3
                else:
                    similarity -= 0.6
            except (ValueError, TypeError):
                pass
        
    
        if m1['estado'] == m2['estado'] or ((m1['modelo'] == m2['modelo'] or m1['marca'] == m2['marca'] )and m1['estado'] == m2['estado'] ):
            similarity += 0.2
        else:
            similarity -= 0.1
        
        # Similaridade de preço -> preço mais próximo, maior similaridade
        if m1['price_value'] > 0 and m2['price_value'] > 0:
            price_diff = abs(m1['price_value'] - m2['price_value'])
            max_price = max(m1['price_value'], m2['price_value'])
            # Se diferença de preço maior que 70% - 50% - 30%, retorna 0 para excluir
            if price_diff / max_price > 0.7:
                similarity -= 0.5
            elif price_diff / max_price > 0.5:
                similarity -= 0.3
            elif price_diff / max_price > 0.3:
                similarity -= 0.2
            else:
                similarity += 0.1 * (1 - min(price_diff / max_price, 1))
    
    
        if m1['ano'] and m2['ano'] and m1['ano'].isdigit() and m2['ano'].isdigit():
            year_diff = abs(int(m1['ano']) - int(m2['ano']))
            if year_diff <= 3:
                similarity += 0.1 * (1 - min(year_diff / 3, 1))  # Máximo de 3 anos de diferença
            else:
                similarity -= 0.1 * (1 - min(year_diff / 2, 1))  # Máximo de 2 anos de diferença
        return similarity
    
    def get_listings_by_state(self):
        """Agrupa anúncios por estado"""
        state_groups = defaultdict(list)
        for m in self.listings:
            if m['estado']:
                state_groups[m['estado']].append(m)
        return state_groups
    
    def get_listings_by_brand(self):
        """Agrupa anúncios por marca"""
        brand_groups = defaultdict(list)
        for m in self.listings:
            if m['marca']:
                brand_groups[m['marca']].append(m)
        return brand_groups
    
    def get_similar_listings(self, listing_id, top_n=5):
        """Encontra os N anúncios mais similares ao anúncio fornecido"""
        print(f"Procurando por anúncios similares para ID: {listing_id} (tipo: {type(listing_id)})")
        
        # Verifica se o nó existe diretamente
        node_exists = listing_id in self.G.nodes
        print(f"Node exists directly in graph? {node_exists}")
        
        # Se não, tenta comparar strings
        if not node_exists:
            str_id = str(listing_id)
            for graph_node_id in self.G.nodes:
                if str(graph_node_id) == str_id:
                    print(f"Encontrei nó por comparação de strings: {graph_node_id}")
                    listing_id = graph_node_id  # Use o ID do nó real do grafo
                    node_exists = True
                    break
        
        if not node_exists or listing_id not in self.G.nodes:
            print(f"Não foi possível encontrar anúncios similares: Nó {listing_id} não encontrado no grafo")
            return []
        
        # Obtém todos os vizinhos com pesos
        neighbors = [(neighbor, self.G.edges[listing_id][neighbor]['weight']) 
                     for neighbor in self.G.neighbors(listing_id)]
        
        # If there are no neighbors, return empty list
        if not neighbors:
            print(f"Nó {listing_id} não tem vizinhos/anúncios similares")
            return []
        
        # Ordena por peso de similaridade
        neighbors.sort(key=lambda x: x[1], reverse=True)
        print(f"Encontrei {len(neighbors)} vizinhos para o nó {listing_id}")
        
        similar_listings = []
        for n_id, similarity in neighbors[:top_n]:
            listing = self.G.nodes[n_id]
            similar_listings.append({
                'id': n_id,
                'title': listing['title'],
                'price': listing['price'],
                'marca': listing['marca'],
                'modelo': listing['modelo'],
                'ano': listing['ano'],
                'similarity': similarity
            })
        
        print(f"Retornando {len(similar_listings)} anúncios similares")
        return similar_listings
    
    def detect_communities(self):
        return self.G.detect_communities()
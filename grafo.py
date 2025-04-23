import json
import matplotlib
matplotlib.use('Agg')  # Set non-GUI backend
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import pandas as pd
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
    
    def create_interactive_graph_data(self, color_by='community'):
        """Cria a visualização interativa do grafo utilizando a biblioteca Plotly"""
        # Tenta obter o layout armazenado primeiro
        cache_key = f'layout_{len(self.G.nodes)}'  # Chave de cache baseada no tamanho do grafo
        
        if cache_key in self.layout_cache:
            positions = self.layout_cache[cache_key]
        else:
            # Obtém posições usando o layout Kamada-Kawai
            positions = self.G.kamada_kawai_layout()
            # Armazena o layout
            self.layout_cache[cache_key] = positions
        
        x_nodes = [positions[node][0] for node in self.G.nodes]
        y_nodes = [positions[node][1] for node in self.G.nodes]
    
        edge_x = []
        edge_y = []
        edge_weights = []
        
        for node1, node2, attrs in self.G.get_edges():
            x0, y0 = positions[node1]
            x1, y1 = positions[node2]
            
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
            
            # Get edge weight
            weight = attrs.get('weight', 1.0)
            edge_weights.append(weight)
        
        node_colors = []
        color_legend = {}
        
        if color_by == 'community':
            partition = self.detect_communities()
            unique_communities = set(partition.values())
            
            # Cria um mapa de cores para as comunidades aleatóriamente
            color_map = {comm: f'hsl({int(i * 360 / len(unique_communities))},70%,60%)' 
                        for i, comm in enumerate(unique_communities)}
            node_colors = [color_map[partition[node]] for node in self.G.nodes]
            color_legend = {f"Community {comm}": color for comm, color in color_map.items()}
            
        elif color_by == 'brand':
            brands = set(self.G.nodes[node]['marca'] for node in self.G.nodes)
            color_map = {brand: f'hsl({int(i * 360 / len(brands))},70%,60%)' 
                        for i, brand in enumerate(brands)}
            node_colors = [color_map[self.G.nodes[node]['marca']] for node in self.G.nodes]
            color_legend = color_map
            
        elif color_by == 'state':
            states = set(self.G.nodes[node]['estado'] for node in self.G.nodes)
            color_map = {state: f'hsl({int(i * 360 / len(states))},70%,60%)' 
                        for i, state in enumerate(states)}
            node_colors = [color_map[self.G.nodes[node]['estado']] for node in self.G.nodes]
            color_legend = color_map
            
        elif color_by == 'price':
            prices = [self.G.nodes[node].get('price_value', 0) for node in self.G.nodes]
            max_price = max(prices) if max(prices) > 0 else 1
            node_colors = [f'hsl({int(240 - 240 * (price / max_price))},70%,60%)' for price in prices]
            color_legend = {"Lower Price": "hsl(240,70%,60%)", "Higher Price": "hsl(0,70%,60%)"}
        
        else:
            # Cor padrão
            node_colors = ['#1f77b4'] * len(self.G.nodes)
            
        # Dados mostrados ao passar o mouse sobre o nó
        node_hover_text = []
        for node in self.G.nodes:
            node_data = self.G.nodes[node]
            text = f"<b>{node_data.get('title', 'Anúncio sem título')}</b><br>"
            text += f"Marca: {node_data.get('marca', 'N/A')}<br>"
            text += f"Modelo: {node_data.get('modelo', 'N/A')}<br>"
            text += f"Ano: {node_data.get('ano', 'N/A')}<br>"
            text += f"Preço: {node_data.get('price', 'N/A')}<br>"
            text += f"Cilindrada: {node_data.get('cilindrada', 'N/A')}cc<br>"
            text += f"Localização: {node_data.get('estado', 'N/A')}<br>"
            text += f"Clique para ver detalhes e anúncios similares"
            node_hover_text.append(text)
        
        node_ids = list(self.G.nodes)
        
        return {
            'positions': positions,
            'x_nodes': x_nodes,
            'y_nodes': y_nodes,
            'edge_x': edge_x,
            'edge_y': edge_y,
            'edge_weights': edge_weights,
            'node_colors': node_colors,
            'node_hover_text': node_hover_text,
            'node_ids': node_ids,
            'color_legend': color_legend
        }
    
    def get_node_data_with_similar(self, node_id, top_n=5):
        """Obtém os dados do nó e os nós similares para exibição interativa ao clicar no nó do grafo plotado"""
        
        node_exists = node_id in self.G.nodes
        
        if not node_exists:
            str_id = str(node_id)
            for graph_node_id in self.G.nodes:
                if str(graph_node_id) == str_id:
                    node_id = graph_node_id
                    node_exists = True
                    break
        
        # Final check if we have the node
        if not node_exists or node_id not in self.G.nodes:
            print(f"Nó não encontrado no grafo: {node_id}")
            return {
                'error': 'Nó não encontrado',
                'node_data': None,
                'similar_nodes': []
            }
        
        node_data = self.G.nodes[node_id]
        
        similar_nodes = self.get_similar_listings(node_id, top_n)
        
        return {
            'node_data': node_data,
            'similar_nodes': similar_nodes
        }
        
    def visualize_state_distribution(self):
        """Visualiza a distribuição de motocicletas por estado"""
        state_counts = defaultdict(int)
        for m in self.listings:
            if m['estado']:
                state_counts[m['estado']] += 1
        
        # Ordena por contagem
        sorted_states = sorted(state_counts.items(), key=lambda x: x[1], reverse=True)
        states, counts = zip(*sorted_states)
        
        plt.figure(figsize=(10, 6))
        plt.bar(states, counts)
        plt.xlabel('State')
        plt.ylabel('Number of Anúncios')
        plt.title('Distribuição de Anúncios por Estado')
        plt.xticks(rotation=45)
        plt.tight_layout()
        return plt
    
    def visualize_brand_distribution(self):
        """Visualiza a distribuição de motocicletas por marca"""
        brand_counts = defaultdict(int)
        for m in self.listings:
            if m['marca']:
                brand_counts[m['marca']] += 1
        
        # Ordena por contagem
        sorted_brands = sorted(brand_counts.items(), key=lambda x: x[1], reverse=True)
        brands, counts = zip(*sorted_brands)
        
        plt.figure(figsize=(12, 6))
        plt.bar(brands, counts)
        plt.xlabel('Marca')
        plt.ylabel('Number of Anúncios')
        plt.title('Distribuição de Anúncios por Marca')
        plt.xticks(rotation=45)
        plt.tight_layout()
        return plt
    
    def visualize_price_distribution(self):
        """Visualiza a distribuição de preço de motocicletas"""
        prices = [m['price_value'] for m in self.listings if m['price_value'] > 0]
        
        plt.figure(figsize=(10, 6))
        plt.hist(prices, bins=20)
        plt.xlabel('Preço (R$)')
        plt.ylabel('Number of Anúncios')
        plt.title('Distribuição de Preço de Anúncios')
        plt.tight_layout()
        return plt

    def search_listings(self, query_text, top_n=10):
        """Busca anúncios com base no texto da consulta usando TF-IDF"""
        # Cria uma lista de documentos de anúncios
        docs = []
        for m in self.listings:
            doc = f"{m['title']} {m['marca']} {m['modelo']} {m['cilindrada']} {m['ano']}"
            docs.append(doc)
        
        # Cria a matriz TF-IDF
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix = vectorizer.fit_transform(docs)
        
        # Transforma a consulta
        query_vector = vectorizer.transform([query_text])
        
        # Calcula a similaridade
        similarity_scores = cosine_similarity(query_vector, tfidf_matrix)[0]
        
        # Obtém os top resultados
        top_indices = similarity_scores.argsort()[-top_n:][::-1]
        results = []
        
        for idx in top_indices:
            if similarity_scores[idx] > 0:
                results.append({
                    'listing': self.listings[idx],
                    'similarity': similarity_scores[idx]
                })
        
        return results
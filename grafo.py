import json
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
        

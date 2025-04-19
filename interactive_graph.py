import plotly.graph_objects as go

def create_interactive_graph(graph_data, color_by='community'):
    """Cria um grafo interativo usando Plotly"""
    
    # Extrai dados do graph_data
    edge_x = graph_data['edge_x']
    edge_y = graph_data['edge_y']
    node_colors = graph_data['node_colors']
    node_hover_text = graph_data['node_hover_text']
    node_ids = graph_data['node_ids']
    x_nodes = graph_data['x_nodes']
    y_nodes = graph_data['y_nodes']
    color_legend = graph_data['color_legend']
    
    # Cria o tracejado da aresta
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=0.5, color='#888'),
        hoverinfo='none',
        mode='lines',
        opacity=0.3
    )
    
    # Cria o tracejado do nó
    node_trace = go.Scatter(
        x=x_nodes, y=y_nodes,
        mode='markers',
        hoverinfo='text',
        text=node_hover_text,
        marker=dict(
            showscale=False,
            color=node_colors,
            size=10,
            line_width=1,
            line=dict(color='#000', width=0.5)
        ),
        customdata=node_ids,
        hovertemplate='%{text}<extra></extra>'
    )
    
    # Cria a figura para o grafo (é o que será exibido no navegador)
    fig = go.Figure(data=[edge_trace, node_trace],
                 layout=go.Layout(
                    title=f'Grafo de Similaridade de Anúncios (Colorido por {color_by})',
                    titlefont_size=16,
                    showlegend=False,
                    hovermode='closest',
                    margin=dict(b=20, l=5, r=5, t=40),
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    height=600,
                    plot_bgcolor='#f8f9fa',
                    paper_bgcolor='#f8f9fa',
                    clickmode='event+select'
                ))

    legend_y = 1.1
    legend_x = 0
    legend_step = 0.05
    
    for i, (label, color) in enumerate(color_legend.items()):
        legend_annotation = go.layout.Annotation(
            x=legend_x,
            y=legend_y - (i * legend_step),
            xref="paper",
            yref="paper",
            text=f"<span style='color:{color}'>●</span> {label}",
            showarrow=False,
            font=dict(size=12),
            align="left"
        )
        fig.add_annotation(legend_annotation)
    
    # Cria configuração para opções de download
    config = {
        'toImageButtonOptions': {
            'format': 'png',
            'filename': 'grafo_de_anuncios',
            'height': 600,
            'width': 800,
            'scale': 2
        },
        'displayModeBar': True,
        'responsive': True,
        'scrollZoom': True,
        'modeBarButtonsToRemove': ['select2d', 'lasso2d', 'autoScale2d'],
        'displaylogo': False
    }
    
    return fig, config 
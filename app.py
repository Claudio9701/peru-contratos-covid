import pandas as pd
import geopandas as gpd
import dash
import dash_bootstrap_components as dbc
import dash_cytoscape as cyto
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import plotly.express as px

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Data preparation
df = pd.read_csv('inputs/CONOSCE_CONTRATACIONDIRECTA.csv', nrows=25)
geo_df = gpd.read_file('inputs/departamentos.geojson')

# Data filters
TIPO_ENTIDAD_OPTIONS = [{'label': x.title(), 'value': x} for x in df['TIPOENTIDADOEE'].unique()]
TIPO_PROVEEDOR_OPTIONS = [{'label': x.title(), 'value': x} for x in df['TIPOPROVEEDOR'].unique()]
RUBROS_OPTIONS = [{'label': x.title(), 'value': x} for x in df['RUBROS'].unique()]

# Scale amount 
df['edgeWidth'] = ((df['MONTOADJUDICADOSOLES']-df['MONTOADJUDICADOSOLES'].min())*(15-3))/(df['MONTOADJUDICADOSOLES'].max()-df['MONTOADJUDICADOSOLES'].min())

# Nodes
source_nodes = df[['RUC_ENTIDAD', 'ENTIDAD']].drop_duplicates()
target_nodes = df[['RUCPROVEEDOR', 'PROVEEDOR']].drop_duplicates()

source_nodes['id'] = source_nodes['RUC_ENTIDAD']
target_nodes['id'] = target_nodes['RUCPROVEEDOR']
source_nodes['label-complete'] = source_nodes['ENTIDAD'].str.title()
target_nodes['label-complete'] = target_nodes['PROVEEDOR'].str.title()
source_nodes['label'] = source_nodes['ENTIDAD'].str.title().str[:15] + '...'
target_nodes['label'] = target_nodes['PROVEEDOR'].str.title().str[:15] + '...'
source_nodes['type'] = 'entidad'
target_nodes['type'] = 'proveedor'

nodes_df = pd.concat([source_nodes, target_nodes])
nodes = [{'data': data} for data in nodes_df.to_dict(orient='records')]
# Edges
edges = df.apply(
    lambda x: {'data': {'source': x['RUC_ENTIDAD'], 'target': x['RUCPROVEEDOR'], **x}},
    axis=1
).tolist()
# Cytoscope elements
elements = nodes + edges
# Cityscope stylesheet
stylesheet = [
    {
        'selector': 'edge',
        'style': {
            'width': 'data(edgeWidth)',
            'line-color': '#000'
        }
    },
    {
        'selector': '[type = "entidad"]',
        'style': {
            'background-color': '#dc3545',
            'label': 'data(label)'
        }
    },
    {
        'selector': '[type = "proveedor"]',
        'style': {
            'background-color': '#ffc107',
            'label': 'data(label)'
        }
    }
]

# Generate Map
map_fig = px.choropleth_mapbox(geo_df,
                               geojson=geo_df.geometry,
                               locations=geo_df.index,
                               color='Monto Per Capita',
                               hover_name='Departamento',
                               hover_data={
                                   'Poblacion Estimada 2020': ':,.0', 
                                   'Superficie (km²)': True,
                                   'Densidad 2017 (hab/km²)': True, 
                                   'Monto Adjudicado': ':,.0f'},
                               mapbox_style="open-street-map",
                               center={"lat": -10.753947, "lon": -74.7179037},
                               zoom=3.5)
map_fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})


navbar = dbc.NavbarSimple(
    children=[
        dbc.DropdownMenu(
            children=[
                dbc.DropdownMenuItem("Fuente de Datos", href="https://www.datosabiertos.gob.pe/dataset/contrataciones-ante-la-emergencia-sanitaria-por-la-existencia-del-coronavirus-organismo"),
                dbc.DropdownMenuItem("Codigo Fuente", href="#"),
                dbc.DropdownMenuItem("Autor", href="#"),
            ],
            nav=True,
            in_navbar=True,
            label="More",
        ),
    ],
    brand="Análisis de Contrataciones de Emergencia por COVID-19",
    color="primary",
    dark=True,
    className='mb-3'
)

controls = dbc.Card(
    [
        dbc.FormGroup(
            [
                dbc.Label("Tipo de Entidad del Estado"),
                dcc.Dropdown(
                    id='dropdown-entidad',
                    options=TIPO_ENTIDAD_OPTIONS,
                    multi=True,
                    value=[opt['value'] for opt in TIPO_ENTIDAD_OPTIONS]
                ),
            ]
        ),
        dbc.FormGroup(
            [
                dbc.Label("Tipo de Proveedor"),
                dcc.Dropdown(
                    id='dropdown-proveedor',
                    options=TIPO_PROVEEDOR_OPTIONS,
                    multi=True,
                    value=[opt['value'] for opt in TIPO_PROVEEDOR_OPTIONS]
                ),
            ]
        ),
        dbc.FormGroup(
            [
                dbc.Label("Rubros"),
                dcc.Dropdown(
                    id='dropdown-rubros',
                    options=RUBROS_OPTIONS,
                    multi=True,
                    value=[opt['value'] for opt in RUBROS_OPTIONS]
                ),
            ]
        ),
    ],
    body=True,
)

content = dbc.Container(
    [
        dbc.Row([dbc.Col(controls, className="mb-3")], align="center"),
        dbc.Row(
            [
                dbc.Col(dbc.CardDeck(
                    [
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    dcc.Graph(id='departamento-map', figure=map_fig)
                                ]
                            )
                        ),
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    dcc.Loading(
                                        id="loading-1",
                                        type="default",
                                        children=html.Div(
                                            [
                                                cyto.Cytoscape(
                                                    id='cytoscape-graph',
                                                    layout={'name': 'cose'},
                                                    zoom=1,
                                                    style={'width': '100%', 'height': '45vh'},
                                                    responsive=True,
                                                    elements=elements,
                                                    stylesheet=stylesheet
                                                ), 
                                                dbc.Button('Reset Graph', id='bt-reset', color="primary", className='mr-1', block=True),
                                            ],
                                        ),
                                    )
                                ]
                            )
                        ),
                    ]
                ), className='mb-3'),
            ],
            align="center",
        ),
        dbc.Row([dbc.Col(dbc.Card([dcc.Graph(id='bar-chart')], body=True), className='mb-3')], align="center"),
    ],
    fluid=True,
)


app.layout = html.Div([navbar, content])

@app.callback(Output('bar-chart', 'figure'),
              [Input('cytoscape-graph', 'tapNodeData')])
def displayTapNodeData(data):
    labels={"MONTOADJUDICADOSOLES":'Monto Adjudicado'}
    if data:
        if data['type'] == 'entidad':
            filtered_df = df[df['RUC_ENTIDAD'] == int(data['id'])]
            fig = px.bar(filtered_df, x="PROVEEDOR", y="MONTOADJUDICADOSOLES", title=f"Proovedores contratados por {data['label-complete']}", labels=labels)
        else:
            filtered_df = df[df['RUCPROVEEDOR'] == int(data['id'])]
            fig = px.bar(filtered_df, x="ENTIDAD", y="MONTOADJUDICADOSOLES", title=f"Entidades que contraron a {data['label-complete']}", labels=labels)
        
    else:
        fig = px.bar(df, x="PROVEEDOR", y="MONTOADJUDICADOSOLES", title='Proovedores Contratados por Entidades del Estado', labels=labels)
    
    fig.update_layout(xaxis={'categoryorder':'total descending', 'title':{'text':''}})
    
    return fig
    
@app.callback(Output('cytoscape-graph', 'elements'),
              [Input(f'dropdown-{filtr}', 'value')
               for filtr in ['entidad', 'proveedor', 'rubros']] +
              [Input('cytoscape-graph', 'tapNodeData'),
               Input('departamento-map', 'clickData'),
               Input('bt-reset', 'n_clicks')],
              [State('cytoscape-graph', 'elements')])
def filtrDataFrame(entidad, proveedor, rubros, data, map_click, n_clicks, current_elements):
    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
    if 'bt-reset' in changed_id:
        return elements
    
    entidad_filter = df['TIPOENTIDADOEE'].isin(entidad)
    proveedor_filter = df['TIPOPROVEEDOR'].isin(proveedor)
    rubros_filter = df['RUBROS'].isin(rubros)
    
    # Apply filters
    filtered_df = df[entidad_filter & proveedor_filter & rubros_filter]
    
    if map_click:
        departamento_selected = map_click['points'][0]['hovertext']
        filtered_df = filtered_df[filtered_df['ENTIDAD_DEPARTAMENTO'] == departamento_selected]
    
    if data:
        if data['type'] == 'entidad':
            filtered_df = filtered_df[filtered_df['RUC_ENTIDAD'] == int(data['id'])]
        elif data['type'] == 'proveedor':
            filtered_df = filtered_df[filtered_df['RUCPROVEEDOR'] == int(data['id'])]
    
    # Nodes
    source_nodes = filtered_df[['RUC_ENTIDAD', 'ENTIDAD']].drop_duplicates()
    target_nodes = filtered_df[['RUCPROVEEDOR', 'PROVEEDOR']].drop_duplicates()

    source_nodes['id'] = source_nodes['RUC_ENTIDAD']
    target_nodes['id'] = target_nodes['RUCPROVEEDOR']
    source_nodes['label'] = source_nodes['ENTIDAD'].str.title().str[:15] + '...'
    target_nodes['label'] = target_nodes['PROVEEDOR'].str.title().str[:15] + '...'
    source_nodes['type'] = 'entidad'
    target_nodes['type'] = 'proveedor'

    nodes_df = pd.concat([source_nodes, target_nodes])
    nodes = [{'data': data} for data in nodes_df.to_dict(orient='records')]
    # Edges
    edges = filtered_df.apply(
        lambda x: {'data': {'source': x['RUC_ENTIDAD'], 'target': x['RUCPROVEEDOR'], **x}},
        axis=1
    ).tolist()
    # Cytoscope elements
    new_elements = nodes + edges
    return new_elements

if __name__ == '__main__':
    app.run_server(debug=True)
import pandas as pd
import numpy as np
import geopandas as gpd
import dash
import dash_bootstrap_components as dbc
import dash_cytoscape as cyto
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import plotly.express as px

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP],
                meta_tags=[{"name": "viewport", "content": "width=device-width"}])
app.title = 'Peru Contratos COVID-19'
server = app.server

# Load Data
df = pd.read_csv('inputs/dashboard_data.csv', parse_dates=True)
geo_df = gpd.read_file('inputs/departamentos.geojson')

# Vars
URL_proceso = "http://prodapp2.seace.gob.pe/seacebus-uiwd-pub/fichaSeleccion/fichaSeleccion.xhtml?idSistema=3&ongei=1&idConvocatoria="

# SEARCH OPTIONS
ruc_name = pd.DataFrame(
    np.concatenate(
        [df[['RUC_ENTIDAD', 'Entidad_clean']].values,
        df[['RUCPROVEEDOR', 'Proveedor_clean']].values])
).drop_duplicates([0]).values.tolist()
SEARCH_OPTIONS = [{'label': f"{x[0]}: {x[1]}", 'value': x[0]} for x in ruc_name]

# Helper functions
def create_options(df):
    # Data filters
    TIPO_ENTIDAD_OPTIONS = [{'label': x.title(), 'value': x} for x in df['TIPOENTIDADOEE'].unique()]
    TIPO_PROVEEDOR_OPTIONS = [{'label': x.title(), 'value': x} for x in df['TIPOPROVEEDOR'].unique()]
    RUBROS_OPTIONS = [{'label': x.title(), 'value': x} for x in df['RUBROS'].unique()]

    return TIPO_ENTIDAD_OPTIONS, TIPO_PROVEEDOR_OPTIONS, RUBROS_OPTIONS

def create_cytoscape_elements(df):
    # Nodes
    source_nodes = df[['RUC_ENTIDAD', 'Entidad_truncated']].drop_duplicates()
    target_nodes = df[['RUCPROVEEDOR', 'Proveedor_truncated']].drop_duplicates()

    rename_sources = {'RUC_ENTIDAD': 'id', 'Entidad_truncated': 'label'}
    source_nodes = source_nodes.rename(columns=rename_sources)

    rename_targets = {'RUCPROVEEDOR': 'id', 'Proveedor_truncated': 'label'}
    target_nodes = target_nodes.rename(columns=rename_targets)

    source_nodes['type'] = 'entidad'
    target_nodes['type'] = 'proveedor'

    nodes_df = pd.concat([source_nodes, target_nodes])
    nodes = [{'data': data} for data in nodes_df.to_dict(orient='records')]
    # Edges
    edges = df.apply(
        lambda x: {'data': {'source': x['RUC_ENTIDAD'], 'target': x['RUCPROVEEDOR'], 'edgeWidth': x['edgeWidth']}},
        axis=1
    ).values.tolist()
    # Cytoscope elements
    elements = nodes + edges

    return elements

# Cityscope stylesheet
stylesheet = [
    {
        'selector': 'edge',
        'style': {
            'width': '3',
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
                               zoom=3.5,
                               labels={"Monto Per Capita": "Monto Adj.\n\nper Cápita"})
map_fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, title={'text':"Mapa de Provincias"})


navbar = dbc.NavbarSimple(
    children=[
        dbc.NavItem(dbc.NavLink("Fuente de Datos", href="https://www.datosabiertos.gob.pe/dataset/contrataciones-ante-la-emergencia-sanitaria-por-la-existencia-del-coronavirus-organismo")),
        dbc.NavItem(dbc.NavLink("Código Fuente", href="https://github.com/Claudio9701/peru-contratos-covid")),
        dbc.NavItem(dbc.NavLink("Autor", href="https://github.com/Claudio9701")),
    ],
    brand="colatics.",
    brand_href="http://www.colatics.com/",
    color="primary",
    dark=True,
    className='mb-3',
    fluid=True
)

about = html.Div(
    [
        dbc.Alert(
            """
                El presente dashboard contiene un breve análisis de
                datos de contrataciones de emergencia del estado peruano
                durante el tiempo de la pandemia del COVID-19. El objetivo de
                este MVP motivar el uso de herramientas basadas en datos abiertos
                para transparentar procesos políticos, administrativos, entre otros.
            """,
            id="alert-fade",
            dismissable=True,
            is_open=True,
            color="primary"
        ),
    ]
)

controls = dbc.Card(
    [
        html.H5('Búsqueda Múltiple'),
        dbc.FormGroup(
            [
                dbc.Label("Selecciona el Número de Contratos a visualizar"),
                dcc.Slider(
                    id='slider-sample-size',
                    min=0,
                    max=1000,
                    marks={i: str(i) for i in range(1001) if i % 100 == 0},
                    value=100,
                )
            ]
        ),
        # TODO: Add date filter support
        # dbc.FormGroup(
        #     [
        #         dbc.Label("Selecciona un Rango de Fechas"),
        #         html.Br(),
        #         dcc.DatePickerRange(
        #             id='date-picker-range',
        #             start_date=df['FECHACONVOCATORIA'].min(),
        #             end_date_placeholder_text=df['FECHACONVOCATORIA'].min(),
        #         )
        #     ]
        # ),
        dbc.FormGroup(
            [
                dbc.Label("Tipo de Entidad del Estado"),
                dcc.Dropdown(
                    id='dropdown-entidad',
                    multi=True,
                    searchable=True,
                    value=['GOBIERNO NACIONAL'],
                    clearable=False
                ),
            ]
        ),
        dbc.FormGroup(
            [
                dbc.Label("Tipo de Proveedor"),
                dcc.Dropdown(
                    id='dropdown-proveedor',
                    multi=True,
                    searchable=True,
                    value=['Persona Juridica'],
                    clearable=False
                ),
            ]
        ),
        dbc.FormGroup(
            [
                dbc.Label("Rubros"),
                dcc.Dropdown(
                    id='dropdown-rubros',
                    multi=True,
                    searchable=True,
                    value=[
                        'MATERIAL Y EQUIPO MEDICO',
                    ],
                    clearable=False
                ),
            ]
        ),
        html.Hr(),
        html.H5('Búsqueda Individual'),
        dbc.FormGroup(
            [
                dcc.Dropdown(
                    id='dropdown-search',
                    searchable=True,
                    options=SEARCH_OPTIONS,
                    placeholder="Busqueda por RUC o Nombre",
                ),
            ]
        ),
    ],
    body=True,
)

content = dbc.Container(
    [
        dbc.Row([dbc.Col(html.Div(
            [
                html.H4("Análisis de Contrataciones de Emergencia por COVID-19"),
                dbc.Button("Información", id="alert-toggle-fade", color="secondary"),
            ]
        ), className="mb-3")], align="center"),
        dbc.Row([dbc.Col(about, className="mb-3")], align="center"),
        dbc.Row([dbc.Col(controls, className="mb-3")], align="center"),
        dbc.Row(
            [
                dbc.Col(dbc.CardDeck(
                    [
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    dcc.Loading(
                                        id="loading-map",
                                        type="default",
                                        children=html.Div(
                                            [
                                                html.H5("Mapa de Provincias"),
                                                dcc.Graph(id='departamento-map', figure=map_fig)
                                            ],
                                        ),
                                    )
                                ]
                            )
                        ),
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    dcc.Loading(
                                        id="loading-graph",
                                        type="default",
                                        children=html.Div(
                                            [
                                                html.H5("Contratos entre Entidades y Proveedores"),
                                                cyto.Cytoscape(
                                                    id='cytoscape-graph',
                                                    layout={'name': 'cose'},
                                                    zoom=5,
                                                    style={'width': '100%', 'height': '45vh'},
                                                    responsive=True,
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

@app.callback(
    Output("alert-fade", "is_open"),
    [Input("alert-toggle-fade", "n_clicks")],
    [State("alert-fade", "is_open")],
)
def toggle_alert(n, is_open):
    if n:
        return not is_open
    return is_open

@app.callback(Output('bar-chart', 'figure'),
              [Input('cytoscape-graph', 'tapNodeData')])
def displayTapNodeData(data):
    labels={"MONTOADJUDICADOSOLES":'Monto Adjudicado', "RUCPROVEEDOR": "RUC", "RUC_ENTIDAD": "RUC"}
    if data:
        if data['type'] == 'entidad':
            filtered_df = df[df['RUC_ENTIDAD'] == int(data['id'])]
            name = filtered_df['Entidad_clean'].iloc[0]
            fig = px.bar(filtered_df, x="RUCPROVEEDOR", y="MONTOADJUDICADOSOLES", title=f"Proovedores contratados por {name}, RUC: {data['id']}", labels=labels, hover_name="Proveedor_clean")
        else:
            filtered_df = df[df['RUCPROVEEDOR'] == int(data['id'])]
            name = filtered_df['Proveedor_clean'].iloc[0]
            fig = px.bar(filtered_df, x="RUC_ENTIDAD", y="MONTOADJUDICADOSOLES", title=f"Entidades que contraron a {name}, RUC: {data['id']}", labels=labels, hover_name="Entidad_clean")

    else:
        top20 = df.sort_values('MONTOADJUDICADOSOLES').tail(20)
        fig = px.bar(top20, x="RUCPROVEEDOR", y="MONTOADJUDICADOSOLES", title='Proovedores Contratados por Entidades del Estado (Top 20 por Monto Adjudicado)', labels=labels, hover_name="Proveedor_clean")

    fig.update_layout(xaxis={'categoryorder':'total descending', 'title':{'text':''}, 'type':'category'}, barmode='stack')

    return fig

@app.callback([Output('cytoscape-graph', 'elements'),
               Output('dropdown-entidad', 'options'),
               Output('dropdown-proveedor', 'options'),
               Output('dropdown-rubros', 'options')],
              [Input(f'dropdown-{filtr}', 'value')
               for filtr in ['entidad', 'proveedor', 'rubros', 'search']] +
              [Input('slider-sample-size', 'value'),
               Input('cytoscape-graph', 'tapNodeData'),
               Input('departamento-map', 'clickData'),
               Input('bt-reset', 'n_clicks')],
              [State('cytoscape-graph', 'elements')])
def filtrDataFrame(entidad, proveedor, rubros, search, sample_size, data, map_click, n_clicks, current_elements):
    sample_df = df.sample(n=sample_size, random_state=0)

    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
    if 'bt-reset' in changed_id:
        elements = create_cytoscape_elements(sample_df)
        TIPO_ENTIDAD_OPTIONS, TIPO_PROVEEDOR_OPTIONS, RUBROS_OPTIONS = create_options(sample_df)
        return elements, TIPO_ENTIDAD_OPTIONS, TIPO_PROVEEDOR_OPTIONS, RUBROS_OPTIONS

    # Update filters options
    TIPO_ENTIDAD_OPTIONS, TIPO_PROVEEDOR_OPTIONS, RUBROS_OPTIONS = create_options(sample_df)

    entidad_filter = sample_df['TIPOENTIDADOEE'].isin(entidad)
    proveedor_filter = sample_df['TIPOPROVEEDOR'].isin(proveedor)
    rubros_filter = sample_df['RUBROS'].isin(rubros)

    # Apply filters
    filtered_df = sample_df[entidad_filter & proveedor_filter & rubros_filter]

    if map_click:
        departamento_selected = map_click['points'][0]['hovertext']
        filtered_df = filtered_df[filtered_df['ENTIDAD_DEPARTAMENTO'] == departamento_selected]

    if data:
        if data['type'] == 'entidad':
            filtered_df = filtered_df[filtered_df['RUC_ENTIDAD'] == int(data['id'])]
        elif data['type'] == 'proveedor':
            filtered_df = filtered_df[filtered_df['RUCPROVEEDOR'] == int(data['id'])]

    if search:
        is_entity = df['RUC_ENTIDAD'] == search
        is_supplier = df['RUCPROVEEDOR'] == search

        filtered_df = df[is_entity | is_supplier]

    # Cytoscope elements
    new_elements = create_cytoscape_elements(filtered_df)

    print(TIPO_ENTIDAD_OPTIONS)

    return new_elements, TIPO_ENTIDAD_OPTIONS, TIPO_PROVEEDOR_OPTIONS, RUBROS_OPTIONS

if __name__ == '__main__':
    app.run_server(debug=True)

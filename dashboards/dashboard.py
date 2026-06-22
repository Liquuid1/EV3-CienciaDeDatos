import os
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
from sqlalchemy import create_engine

# 1. CARGAR CONFIGURACIÓN Y ENTORNO
load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_DATABASE")

# Conexión a TiDB Cloud
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
connect_args = {"ssl": {"fake_user_to_enable_ssl": True}}
engine = create_engine(DATABASE_URL, connect_args=connect_args)

# 2. FUNCIÓN PARA TRAER LA DATA LIMPIA DESDE LA NUBE
def cargar_datos_dw():
    query = "SELECT * FROM dw_peliculas_analitica;"
    df = pd.read_sql(query, con=engine)
    # Asegurar tipos de datos correctos en Pandas
    df['reproducciones_mensuales'] = df['reproducciones_mensuales'].fillna(0).astype(int)
    df['popularidad_api'] = df['popularidad_api'].fillna(0.0).astype(float)
    df['votos_promedio_api'] = df['votos_promedio_api'].fillna(0.0).astype(float)
    return df

# Carga inicial de datos
df_inicial = cargar_datos_dw()

# 3. INICIALIZAR LA APP EN DASH
app = dash.Dash(__name__, title="Dashboard de Streaming")

# 4. DISEÑO DE LA INTERFAZ (LAYOUT)
app.layout = html.Div(style={'fontFamily': 'Arial, sans-serif', 'backgroundColor': '#f8f9fa', 'margin': '0', 'padding': '20px'}, children=[
    
    # Encabezado Principal
    html.Div(style={'backgroundColor': '#1f3a52', 'padding': '20px', 'borderRadius': '8px', 'marginBottom': '20px', 'color': 'white'}, children=[
        html.H1("🎬 Plataforma de Streaming - Panel de Analítica e Integración", style={'margin': '0', 'fontSize': '28px'}),
        html.P("Datos unificados en tiempo real desde TiDB Cloud y TMDB API", style={'margin': '5px 0 0 0', 'opacity': '0.8'})
    ]),
    
    # Filtro Global Estático (Requisito de Interactividad)
    html.Div(style={'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.05)', 'marginBottom': '20px'}, children=[
        html.Label("🔍 Filtrar por Clasificación de Edad (Chile):", style={'fontWeight': 'bold', 'color': '#2c3e50'}),
        dcc.Dropdown(
            id='filtro-clasificacion',
            options=[{'label': i, 'value': i} for i in sorted(df_inicial['clasificacion_edad_local'].unique())],
            value=None,
            placeholder="Todas las clasificaciones",
            style={'marginTop': '5px'}
        )
    ]),
    
    # PESTAÑAS PARA LAS DIFERENTES AUDIENCIAS (Multi-audiencia exigido en la pauta)
    dcc.Tabs(id="tabs-audiencias", value='tab-ejecutiva', children=[
        
        # --- PESTAÑA 1: VISTA EJECUTIVA (Para toma de decisiones de Gerencia) ---
        dcc.Tab(label='📊 Vista Ejecutiva (Negocio)', value='tab-ejecutiva', children=[
            html.Div(style={'padding': '20px', 'backgroundColor': 'white', 'border': '1px solid #dee2e6', 'borderTop': 'none', 'borderRadius': '0 0 8px 8px'}, children=[
                
                # Tarjetas KPI (Letras grandes)
                html.Div(style={'display': 'flex', 'justifyContent': 'space-between', 'marginBottom': '25px', 'gap': '15px'}, children=[
                    html.Div(style={'flex': '1', 'backgroundColor': '#e1f5fe', 'padding': '20px', 'borderRadius': '6px', 'textAlign': 'center'}, children=[
                        html.H3("Total Películas en Catálogo", style={'margin': '0', 'fontSize': '14px', 'color': '#0288d1'}),
                        html.H2(id="kpi-total-peliculas", style={'margin': '10px 0 0 0', 'fontSize': '28px', 'color': '#01579b'})
                    ]),
                    html.Div(style={'flex': '1', 'backgroundColor': '#e8f5e9', 'padding': '20px', 'borderRadius': '6px', 'textAlign': 'center'}, children=[
                        html.H3("Total Reproducciones Plataforma", style={'margin': '0', 'fontSize': '14px', 'color': '#388e3c'}),
                        html.H2(id="kpi-total-reproducciones", style={'margin': '10px 0 0 0', 'fontSize': '28px', 'color': '#1b5e20'})
                    ]),
                    html.Div(style={'flex': '1', 'backgroundColor': '#ffebee', 'padding': '20px', 'borderRadius': '6px', 'textAlign': 'center'}, children=[
                        html.H3("Películas con Alerta Crítica", style={'margin': '0', 'fontSize': '14px', 'color': '#d32f2f'}),
                        html.H2(id="kpi-alertas-criticas", style={'margin': '10px 0 0 0', 'fontSize': '28px', 'color': '#b71c1c'})
                    ]),
                ]),
                
                # Gráfico Ejecutivo: Relación Popularidad Global vs Consumo Local
                html.Div(children=[
                    html.H4("Análisis de Demanda: Popularidad en TMDB vs Reproducciones Locales", style={'color': '#2c3e50', 'marginBottom': '10px'}),
                    dcc.Graph(id='grafico-ejecutivo-dispersion')
                ])
            ])
        ]),
        
        # --- PESTAÑA 2: VISTA OPERATIVA (Para el equipo técnico/operadores de contenido) ---
        dcc.Tab(label='⚙️ Vista Operativa (Monitoreo)', value='tab-operativa', children=[
            html.Div(style={'padding': '20px', 'backgroundColor': 'white', 'border': '1px solid #dee2e6', 'borderTop': 'none', 'borderRadius': '0 0 8px 8px'}, children=[
                
                html.Div(style={'display': 'flex', 'gap': '20px', 'marginBottom': '20px'}, children=[
                    # Gráfico de barras operativo
                    html.Div(style={'flex': '1'}, children=[
                        html.H4("Top 10 Películas por Calificación Promedio (API)", style={'color': '#2c3e50'}),
                        dcc.Graph(id='grafico-operativo-barras')
                    ]),
                ]),
                
                # Tabla Operativa con las Reglas de Negocio Calculadas (Alerta Acción)
                html.H4("Listado de Control y Acciones Operativas Requeridas", style={'color': '#2c3e50', 'marginTop': '20px'}),
                html.P("Esta tabla interactiva muestra las alertas generadas automáticamente por el motor ETL para la moderación del catálogo:", style={'fontSize': '13px', 'color': '#7f8c8d'}),
                dash_table.DataTable(
                    id='tabla-operativa-alertas',
                    columns=[
                        {"name": "ID", "id": "id_pelicula"},
                        {"name": "Título de la Película", "id": "titulo"},
                        {"name": "Clasificación CL", "id": "clasificacion_edad_local"},
                        {"name": "Reproducciones", "id": "reproducciones_mensuales"},
                        {"name": "Popularidad API", "id": "popularidad_api"},
                        {"name": "Acción Recomendada (ETL)", "id": "alerta_accion"}
                    ],
                    page_size=10,
                    style_table={'overflowX': 'auto'},
                    style_header={'backgroundColor': '#1f3a52', 'color': 'white', 'fontWeight': 'bold'},
                    style_cell={'textAlign': 'left', 'padding': '10px', 'fontSize': '12px'},
                    style_data_conditional=[
                        {
                            'if': {'filter_query': '{alerta_accion} contains "Control Parental"'},
                            'backgroundColor': '#ffebee', 'color': '#b71c1c'
                        },
                        {
                            'if': {'filter_query': '{alerta_accion} contains "Oportunidad de Marketing"'},
                            'backgroundColor': '#e8f5e9', 'color': '#1b5e20'
                        }
                    ]
                )
            ])
        ])
    ])
])

# 5. CALLBACK INTERACTIVO (El motor que reacciona a los filtros del usuario)
@app.callback(
    [Output('kpi-total-peliculas', 'children'),
     Output('kpi-total-reproducciones', 'children'),
     Output('kpi-alertas-criticas', 'children'),
     Output('grafico-ejecutivo-dispersion', 'figure'),
     Output('grafico-operativo-barras', 'figure'),
     Output('tabla-operativa-alertas', 'data')],
    [Input('filtro-clasificacion', 'value')]
)
def actualizar_dashboard(clasificacion_seleccionada):
    # Volver a leer la data en la nube para asegurar datos frescos
    df = cargar_datos_dw()
    
    # Aplicar el filtro dinámico si el usuario seleccionó una opción
    if clasificacion_seleccionada:
        df_filtrado = df[df['clasificacion_edad_local'] == clasificacion_seleccionada]
    else:
        df_filtrado = df
        
    # Calcular métricas para las Tarjetas KPI
    total_pelis = len(df_filtrado)
    total_repros = f"{df_filtrado['reproducciones_mensuales'].sum():,}".replace(",", ".")
    total_alertas = len(df_filtrado[df_filtrado['alerta_accion'].str.contains("Control Parental|Alerta", regex=True, na=False)])
    
    # GRAFICO VISTA EJECUTIVA: Dispersión interactiva
    fig_dispersion = px.scatter(
        df_filtrado, 
        x="popularidad_api", 
        y="reproducciones_mensuales",
        hover_name="titulo",
        color="clasificacion_edad_local",
        labels={'popularidad_api': 'Popularidad Global (TMDB API)', 'reproducciones_mensuales': 'Reproducciones Locales (Plataforma)'},
        template="plotly_white"
    )
    fig_dispersion.update_layout(margin={'l': 40, 'b': 40, 't': 10, 'r': 10})
    
    # GRAFICO VISTA OPERATIVA: Top 10 mejor votadas
    df_top10 = df_filtrado.nlargest(10, 'votos_promedio_api')
    fig_barras = px.bar(
        df_top10,
        x="votos_promedio_api",
        y="titulo",
        orientation='h',
        labels={'votos_promedio_api': 'Calificación de la Crítica (0-10)', 'titulo': 'Película'},
        color="votos_promedio_api",
        color_continuous_scale="Viridis",
        template="plotly_white"
    )
    fig_barras.update_layout(yaxis={'categoryorder':'total ascending'}, margin={'l': 150, 'b': 40, 't': 10, 'r': 10})
    
    # Datos para la tabla operativa
    tabla_datos = df_filtrado.to_dict('records')
    
    return total_pelis, total_repros, total_alertas, fig_dispersion, fig_barras, tabla_datos

# Ejecutar el servidor local
if __name__ == '__main__':
    app.run(debug=True, port=8050)
import json
import streamlit as st
import pandas as pd
import numpy as np
from matplotlib.patches import Arc
import matplotlib.pyplot as plt
from mplsoccer import Pitch, VerticalPitch
from scipy.stats import gaussian_kde
import requests
import os
import plotly.express as px
import plotly.graph_objects as go

# Configuración de la página
st.set_page_config(page_title="CoolStat", page_icon="logo.png", layout="wide")

# Cargar datos
@st.cache_data
def load_data():
    try:
        eurocopa = pd.read_csv("data/eurocopa_datos.csv")
        copa_america = pd.read_csv("data/copa_america_datos.csv")
        return eurocopa, copa_america
    
    except FileNotFoundError as e:
        st.error("Error al cargar los datos: {e}")
        st.stop()

# Cargar alineaciones
@st.cache_data
def lineups():
    try:
        euro_lineups = pd.read_csv("data/euro_lineups.csv")
        copa_america_lineups = pd.read_csv("data/copa_america_lineups.csv")
        return euro_lineups, copa_america_lineups

    except FileNotFoundError as e:
        st.error("Error al cargar los datos: {e}")
        st.stop()

@st.cache_data
def load_events():
    try:
        euro_all_matches = pd.read_csv("data/euro_all_events.csv")
        copa_america_all_matches = pd.read_csv("data/copa_america_all_events.csv")
        return euro_all_matches, copa_america_all_matches
    
    except FileNotFoundError as e:
        st.error(f"Error al cargar los eventos: {e}")
        st.stop()

# Menú lateral
with st.sidebar.header("🏆 Campeonatos de fútbol"):

    eurocopa, copa_america = load_data()

    # Renombrar competiciones
    eurocopa["competition"] = eurocopa["competition"].replace("Europe - UEFA Euro", "Eurocopa")
    copa_america["competition"] = copa_america["competition"].replace("South America - Copa America", "Copa América")
    
    # Lista de competiciones disponibles
    competition_list = (
        eurocopa["competition"].unique().tolist() + copa_america["competition"].unique().tolist()
    )
    selected_competition = st.sidebar.selectbox("Selecciona una competición", competition_list)

    # Selección de equipos según la competición elegida
    df_selected = eurocopa if selected_competition in eurocopa["competition"].unique() else copa_america
    
    # Lista de equipos ordenada alfabéticamente
    team_list = sorted(df_selected["home_team"].unique().tolist())
    selected_team = st.sidebar.selectbox("Selecciona un equipo", team_list)

    # Crear nueva columna con los equipos del partido
    eurocopa["match_teams"] = "(" + eurocopa['competition_stage'] + ") " + eurocopa["home_team"] + " " + eurocopa['home_score'].astype(str) + " - " + eurocopa['away_score'].astype(str) + " " + eurocopa["away_team"]
    copa_america["match_teams"] = "(" + copa_america['competition_stage'] + ") " + copa_america["home_team"] + " " + copa_america['home_score'].astype(str) + " - " + copa_america['away_score'].astype(str) + " " + copa_america["away_team"]

    # Filtrar partidos donde el equipo haya jugado
    team_matches = df_selected.loc[(df_selected["home_team"] == selected_team) | (df_selected["away_team"] == selected_team)]

    # Ver partidos del equipo seleccionado
    df_selected_match = st.sidebar.selectbox("Selecciona un partido", team_matches["match_teams"].unique())
    match_details = team_matches[team_matches["match_teams"] == df_selected_match]


def filter_passes(player, match_id):
    euro_all_events_df, copa_america_all_events_df = load_events()
    
    # Combinar DataFrames de eventos
    all_events_df = pd.concat([euro_all_events_df, copa_america_all_events_df], ignore_index=True)
    
    # Filtrar eventos de tipo "Pass"
    passes = all_events_df[(all_events_df["type"] == "Pass") & (all_events_df["match_id"] == match_id)]

    # Convertir 'location' y 'pass_end_location' a listas si vienen como string
    passes.loc[:, 'location'] = passes['location'].apply(lambda loc: eval(loc) if isinstance(loc, str) else loc)
    passes.loc[:, 'pass_end_location'] = passes['pass_end_location'].apply(lambda loc: eval(loc) if isinstance(loc, str) else loc)

    # Filtrar filas con valores válidos en 'location' y 'pass_end_location'
    passes = passes[passes['location'].notnull() & passes['pass_end_location'].notnull()]

    # Separar coordenadas
    passes[['x', 'y']] = pd.DataFrame(passes['location'].tolist(), index=passes.index)
    passes[['pass_end_x', 'pass_end_y']] = pd.DataFrame(passes['pass_end_location'].tolist(), index=passes.index)

    # Filtrar los pases del jugador
    player_passes = passes[passes["player"] == player]

    # Dividir en exitosos y fallidos
    successful_passes = player_passes[player_passes["pass_outcome"].isnull()]  # Exitosos no tienen "outcome"
    unsuccessful_passes = player_passes[player_passes["pass_outcome"].notnull()]  # Fallidos sí tienen "outcome"

    return successful_passes, unsuccessful_passes


def filter_shots(player, match_id):
    euro_all_events_df, copa_america_all_events_df = load_events()
    
    # Combinar DataFrames de eventos
    all_events_df = pd.concat([euro_all_events_df, copa_america_all_events_df], ignore_index=True)
    
    # Filtrar eventos de tipo "Shot"
    shots = all_events_df[(all_events_df["type"] == "Shot")].reset_index(drop=True)

    shots['location'] = shots['location'].apply(json.loads)
    
    # Filtrar los tiros del jugador
    player_shots = shots[shots["player"] == player]
    
    return player_shots


def passMap(player, match_id):
    # Obtener los pases del jugador
    successful_passes, unsuccessful_passes = filter_passes(player, match_id)

    # Dibujar el campo de fútbol
    pitch = Pitch(pitch_type='statsbomb', pitch_color='white')
    fig, ax = pitch.draw(figsize=(14, 9), constrained_layout=True, tight_layout=False)
    fig.set_facecolor('white')

    # Dibujar flechas para los pases exitosos
    pitch.arrows(successful_passes["x"], successful_passes["y"],
                 successful_passes["pass_end_x"], successful_passes["pass_end_y"],
                 width=3, headwidth=5, headlength=5, color="green", ax=ax, label='Pases completados')

    # Dibujar flechas para los pases fallidos
    pitch.arrows(unsuccessful_passes["x"], unsuccessful_passes["y"],
                 unsuccessful_passes["pass_end_x"], unsuccessful_passes["pass_end_y"],
                 width=3, headwidth=5, headlength=5, color="red", ax=ax, label='Pases fallidos')

    # Leyenda
    ax.legend(facecolor='white', handlelength=4, edgecolor='black', fontsize=11, loc='upper left')

    # Título
    ax.set_title(f"Pases de {player}", fontsize=22, color='black')

    # Subtítulo
    ax.text(0.5, 0.975, "Vista detallada de pases completados y fallidos",
            transform=ax.transAxes, ha='center', fontsize=12, color='grey')

    st.pyplot(fig)


def shot_map(player, match_id):
    # Cargar los eventos del partido seleccionado
    euro_all_events_df, copa_america_all_events_df = load_events()
    all_events_df = pd.concat([euro_all_events_df, copa_america_all_events_df], ignore_index=True)

    # Filtrar eventos del partido seleccionado
    match_events = all_events_df[all_events_df["match_id"] == match_id]

    # Filtrar tiros
    shots = match_events[match_events["type"] == "Shot"].reset_index(drop=True)

    # Convertir 'location' a listas si vienen como string
    shots['location'] = shots['location'].apply(lambda loc: eval(loc) if isinstance(loc, str) else loc)

    # Filtrar por jugador
    if player:
        shots = shots[shots['player'] == player]

    # Crear el campo de fútbol en orientación vertical
    pitch = VerticalPitch(pitch_type='statsbomb', pitch_color='white', half=True)
    fig, ax = pitch.draw(figsize=(9, 9), constrained_layout=True, tight_layout=False)

    # Dibujar los tiros
    for shot in shots.to_dict(orient='records'):
        pitch.scatter(
            x=float(shot['location'][0]),
            y=float(shot['location'][1]),
            ax=ax,
            s=2500 * shot['shot_statsbomb_xg'],  # Tamaño proporcional al xG
            color='green' if shot['shot_outcome'] == 'Goal' else 'red',  # Verde si es gol, cruz roja si no
            edgecolors='black',
            alpha=1 if shot['shot_outcome'] == 'Goal' else 0.5,  # Opacidad mayor si es gol
            zorder=2 if shot['shot_outcome'] == 'Goal' else 1  # Z-order para superposición
        )

    ax.set_title(f"Tiros de {player}", fontsize=18, color='black')

    # Mostrar el gráfico
    st.pyplot(fig)


def main():
    st.title("⚽ CoolStat Streamlit App")
    
    st.markdown("##### Página web interactiva para visualizar datos de partidos de la Eurocopa y la Copa América")

    st.subheader(f"📊 Estadísticas de la {selected_competition}")

    # Obtener los eventos del partido seleccionado
    euro_all_events_df, copa_america_all_events_df = load_events()
    all_events_df = pd.concat([euro_all_events_df, copa_america_all_events_df], ignore_index=True)

    # Filtrar eventos del partido seleccionado
    match_id = match_details["match_id"].values[0]
    match_events = all_events_df[all_events_df["match_id"] == match_id]

    match_report, data_tab, heatmap_tab, pass_map_tab, shot_map_tab = st.tabs(['Informe del partido', 
                                                                                'Alineaciones',
                                                                                'Mapa de calor',
                                                                                'Mapa de pases',
                                                                                'Mapa de tiros'])

    # Primera pestaña
    with match_report:
        st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            # Local
            st.markdown(f"<h4 style='text-align: center;'>{match_details.iloc[0]['home_team']}</h4>", unsafe_allow_html=True)
            
        with col2:
            # Resultado
            st.markdown(f"<h3 style='text-align: center;'>{match_details.iloc[0]['home_score']} - {match_details.iloc[0]['away_score']}</h3>", unsafe_allow_html=True)
            
        with col3:
            # Visitante
            st.markdown(f"<h4 style='text-align: center;'>{match_details.iloc[0]["away_team"]}</h4>", unsafe_allow_html=True)

        # Separador
        st.divider()

        st.write("🧍Entrenador local: ", match_details.iloc[0]["home_managers"])
        st.write("🧍Entrenador visitante: ", match_details.iloc[0]["away_managers"])
        st.write("📅 Fecha: ", match_details.iloc[0]["match_date"])
        st.write("📣 Árbitro: ", match_details.iloc[0]["referee"])
        st.write("🏟️ Estadio: ", match_details.iloc[0]["stadium"])
        

    # Segunda pestaña
    with data_tab:
        # Cargar las alineaciones
        euro_lineups, copa_america_lineups = lineups()
        all_lineups = euro_lineups if selected_competition == "Eurocopa" else copa_america_lineups

        # Filtrar por el partido seleccionado usando match_id y quitar el índice
        match_id = match_details["match_id"].values[0]
        match_lineups = all_lineups[all_lineups["match_id"] == match_id]

        # Obtener los nombres de los equipos en el partido
        home_team = match_details["home_team"].values[0]
        away_team = match_details["away_team"].values[0]

        # Separar las alineaciones por equipo
        home_team_lineup = match_lineups[match_lineups["country"] == home_team].sort_values(by="jersey_number")
        away_team_lineup = match_lineups[match_lineups["country"] == away_team].sort_values(by="jersey_number")

        # Jugadores que salieron de inicio
        home_team_starting = home_team_lineup[
            home_team_lineup["positions"].apply(lambda pos: any(d.get("from") == "00:00" for d in eval(pos)))].reset_index(drop=True)

        away_team_starting = away_team_lineup[
            away_team_lineup["positions"].apply(lambda pos: any(d.get("from") == "00:00" for d in eval(pos)))].reset_index(drop=True)

        # Jugadores restantes
        # El símbolo ~ es un operador de negación en Pandas 
        home_team_subs = home_team_lineup[
            home_team_lineup["positions"].apply(lambda pos: not any(d.get("from") == "00:00" for d in eval(pos)))].reset_index(drop=True)
        
        away_team_subs = away_team_lineup[
            away_team_lineup["positions"].apply(lambda pos: not any(d.get("from") == "00:00" for d in eval(pos)))].reset_index(drop=True)

        # Mostrar en columnas
        col1, col2 = st.columns(2)

        with col1:
            st.html(f"<h2 style='text-align: center;'>{home_team}</h2>")
            st.write("Titulares")
            st.write(home_team_starting[["jersey_number", "player_name"]])

            st.divider()

            st.write("Suplentes")
            st.write(home_team_subs[["jersey_number", "player_name"]])

        with col2:
            st.html(f"<h2 style='text-align: center;'>{away_team}</h2>")
            st.write("Titulares")
            st.write(away_team_starting[["jersey_number", "player_name"]])

            st.divider()

            st.write("Suplentes")
            st.write(away_team_subs[["jersey_number", "player_name"]])

    
    # Tercera pestaña
    with heatmap_tab:
        st.subheader("Mapa de calor de pases")
        
        # Seleccionar equipo para el mapa de calor
        selected_team_for_heatmap = st.radio("Seleccionar equipo:", [home_team, away_team])
        
        # Filtrar pases del equipo seleccionado
        team_passes = match_events[
            (match_events["type"] == "Pass") & 
            (match_events["team"] == selected_team_for_heatmap)
        ]
        
        # Convertir 'location' a listas si vienen como string
        team_passes.loc[:, 'location'] = team_passes['location'].apply(lambda loc: eval(loc) if isinstance(loc, str) else loc)
        
        # Filtrar filas con valores válidos en 'location'
        team_passes = team_passes[team_passes['location'].notnull()]
        
        # Separar coordenadas
        team_passes[['x', 'y']] = pd.DataFrame(team_passes['location'].tolist(), index=team_passes.index)
        
        # Crear el mapa de calor
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Dibujar el campo de fútbol
        pitch = Pitch(pitch_type='statsbomb', pitch_color='white', line_color='black')
        pitch.draw(ax=ax)
        
        # Crear kernel density estimate para los pases
        kde = gaussian_kde([team_passes['x'], team_passes['y']])
        xi, yi = np.mgrid[0:120:100j, 0:80:100j]
        zi = kde(np.vstack([xi.flatten(), yi.flatten()]))
        
        # Dibujar el mapa de calor
        ax.pcolormesh(xi, yi, zi.reshape(xi.shape), cmap='hot', alpha=0.6)
        
        st.pyplot(fig)


    # Cuarta pestaña
    with pass_map_tab:

        home_team_played = home_team_lineup[
            home_team_lineup["positions"].apply(lambda pos: len(eval(pos)) > 0)
        ]
        
        away_team_played = away_team_lineup[
            away_team_lineup["positions"].apply(lambda pos: len(eval(pos)) > 0)
        ]   

        col1, col2 = st.columns(2)

        with col1:
            local_player_selected = st.selectbox("Jugador del equipo local", home_team_played["player_name"].tolist())
            st.write("")
            st.write("")

            # Mostrar el mapa de pases del jugador local seleccionado
            passMap(local_player_selected, home_team_played["match_id"].iloc[0])

        with col2:
            away_player_selected = st.selectbox("Jugador del equipo visitante", away_team_played["player_name"].tolist())
            st.write("")
            st.write("")
            
            # Mostrar el mapa de pases del jugador visitante seleccionado
            passMap(away_player_selected, away_team_played["match_id"].iloc[0])
            

    # Quinta pestaña
    with shot_map_tab:
        home_team_played = home_team_lineup[
            home_team_lineup["positions"].apply(lambda pos: len(eval(pos)) > 0)
        ]
        
        away_team_played = away_team_lineup[
            away_team_lineup["positions"].apply(lambda pos: len(eval(pos)) > 0)
        ]   

        col1, col2 = st.columns(2)

        with col1:
            local_player_selected = st.selectbox("Jugador del equipo local", home_team_played["player_name"].tolist(), key="local_shot_player")
            st.write("")
            st.write("")
            shot_map(local_player_selected, home_team_played["match_id"].iloc[0])
    
        with col2:
            away_player_selected = st.selectbox("Jugador del equipo visitante", away_team_played["player_name"].tolist(), key="away_shot_player")
            st.write("")
            st.write("")
            shot_map(away_player_selected, away_team_played["match_id"].iloc[0])




    # st.divider()
    with st.expander('ℹ️ Disclaimer & Info'):
        st.write('''
       - Todos los datos en esta app provienen del repositorio de datos abiertos de StatsBomb.
       - Esta app es solo para fines educativos.
    ''')


if __name__ == "__main__":
    main()

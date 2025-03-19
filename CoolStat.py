import streamlit as st
import pandas as pd
import numpy as np
from matplotlib.patches import Arc
import matplotlib.pyplot as plt
from scipy.stats import kde
import requests
import os

# Configuración de la página
st.set_page_config(page_title="CoolStat", page_icon="⚽", layout="wide")

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
    copa_america["match_teams"] = copa_america["home_team"] + " " + copa_america['home_score'].astype(str) + " - " + copa_america['away_score'].astype(str) + " " + copa_america["away_team"]

    # Filtrar partidos donde el equipo haya jugado
    team_matches = df_selected.loc[(df_selected["home_team"] == selected_team) | (df_selected["away_team"] == selected_team)]

    # Ver partidos del equipo seleccionado
    df_selected_match = st.sidebar.selectbox("Selecciona un partido", team_matches["match_teams"].unique())
    match_details = team_matches[team_matches["match_teams"] == df_selected_match]
    

def main():
    st.title("⚽ CoolStat Streamlit App")
    st.markdown("##### Página web interactiva para visualizar datos de partidos de la Eurocopa y la Copa América")

    st.subheader(f"📊 Estadísticas de la {selected_competition}")
    "\n"

    match_report, data_tab, heatmap_tab, passing_network_tab = st.tabs(['Informe del partido', 
                                                         'Alineaciones',
                                                         'Mapa de calor',
                                                         'Red de pases',])

    # Primera pestaña
    with match_report:
        # st.write(f"Partidos de {selected_team}:")
        # st.header(f"📊 Informe del partido: {match_details['home_team'].values[0]} vs {match_details['away_team'].values[0]}")
        st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)
        # st.write(team_matches)

        col1, col2, col3 = st.columns(3)
        with col1:
            # st.markdown("Local")
            st.markdown(f"<h4 style='text-align: center;'>{match_details.iloc[0]['home_team']}</h4>", unsafe_allow_html=True)
            
        with col2:
            # st.markdown("Resultado")
            st.markdown(f"<h4 style='text-align: center;'>{match_details.iloc[0]['home_score']} - {match_details.iloc[0]['away_score']}</h4>", unsafe_allow_html=True)
            
        with col3:
            # st.markdown("Visitante")
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

        # Borrar el índice y reorganizar (no hace nada)
        match_lineups.reset_index(drop=True, inplace=True)

        # Obtener los nombres de los equipos en el partido
        home_team = match_details["home_team"].values[0]
        away_team = match_details["away_team"].values[0]

        # Separar las alineaciones por equipo
        home_team_lineup = match_lineups[match_lineups["country"] == home_team].sort_values(by="jersey_number")
        away_team_lineup = match_lineups[match_lineups["country"] == away_team].sort_values(by="jersey_number")

        # Mostrar en columnas
        col1, col2 = st.columns(2)

        with col1:
            st.subheader(f"{home_team}")
            st.write(home_team_lineup[["jersey_number", "player_name"]])

        with col2:
            st.subheader(f"{away_team}")
            st.write(away_team_lineup[["jersey_number", "player_name"]])

    # Tercera pestaña
    with heatmap_tab:
        st.subheader("Mapa de calor")
        
        # Placeholder for heatmap data - you'll need to load/process this
        if 'events' not in st.session_state:
            st.session_state.events = {}  # Add your event data processing here
        
        # Select player for heatmap
        selected_team_for_heatmap = st.radio("Seleccionar equipo:", [home_team, away_team])
        
        # Get players for selected team
        players_df = home_team_lineup if selected_team_for_heatmap == home_team else away_team_lineup
        selected_player = st.selectbox("Seleccionar jugador:", players_df["player_name"].tolist())
        
        # Create heatmap (placeholder)
        fig, ax = plt.subplots(figsize=(10, 7))
        
        # Draw football pitch (simplified)
        ax.set_xlim(0, 120)
        ax.set_ylim(0, 80)
        
        # Draw pitch lines
        ax.plot([0, 0, 120, 120, 0], [0, 80, 80, 0, 0], 'black')
        ax.plot([60, 60], [0, 80], 'black')  # Half-way line
        
        # Draw center circle
        center_circle = plt.Circle((60, 40), 9.15, fill=False, color='black')
        ax.add_patch(center_circle)
        
        # Example data points (replace with actual player positions)
        x = np.random.normal(60, 20, 100)
        y = np.random.normal(40, 15, 100)
        
        # Create kernel density estimate
        k = kde.gaussian_kde([x, y])
        xi, yi = np.mgrid[0:120:100j, 0:80:100j]
        zi = k(np.vstack([xi.flatten(), yi.flatten()]))
        
        # Plot heatmap
        ax.pcolormesh(xi, yi, zi.reshape(xi.shape), cmap='hot', alpha=0.7)
        
        ax.set_aspect('equal')
        ax.set_title(f"{selected_player}")
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        # No mostrar los ejes
        ax.axis('off')
        
        st.pyplot(fig)

    # Cuarta pestaña
    with passing_network_tab:
        st.write("Red de pases")

    # st.divider()
    with st.expander('ℹ️ Disclaimer & Info'):
        st.write('''
       - Todos los datos en esta app provienen del repositorio de datos abiertos de StatsBomb.
       - Esta app es solo para fines educativos.
    ''')


if __name__ == "__main__":
    main()

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

# ============================================================
# MICROALGAL BIOREACTOR SIMULATOR
# Conceptual process model for interactive experimentation
# ============================================================

st.set_page_config(
    page_title="Microalgal Bioreactor Simulator",
    page_icon="🦠",
    layout="wide"
)

# ------------------------------------------------------------
# TITLE
# ------------------------------------------------------------

st.title("🦠 Microalgal Bioreactor Simulator")

st.markdown(
    """
    **Interactive conceptual model for microalgal cultivation using
    nutrient-containing wastewater.**

    Adjust the operating conditions and observe their predicted effects
    on biomass growth, nutrient removal, CO₂ utilization and biomass
    composition.
    """
)

st.info(
    "This is a research/educational process simulation. "
    "The equations are simplified engineering assumptions and should "
    "not be treated as experimentally validated reactor predictions."
)

# ============================================================
# SIDEBAR - INPUT PARAMETERS
# ============================================================

st.sidebar.header("⚙️ Reactor Parameters")

reactor_volume = st.sidebar.slider(
    "Working volume (L)",
    min_value=1.0,
    max_value=1000.0,
    value=100.0,
    step=1.0
)

initial_biomass = st.sidebar.slider(
    "Initial biomass concentration (g/L)",
    min_value=0.05,
    max_value=5.0,
    value=0.30,
    step=0.05
)

cultivation_time = st.sidebar.slider(
    "Cultivation time (days)",
    min_value=1,
    max_value=30,
    value=15,
    step=1
)

st.sidebar.header("🌡️ Environmental Conditions")

temperature = st.sidebar.slider(
    "Temperature (°C)",
    min_value=15.0,
    max_value=40.0,
    value=28.0,
    step=0.5
)

pH = st.sidebar.slider(
    "pH",
    min_value=5.0,
    max_value=10.0,
    value=7.5,
    step=0.1
)

light_intensity = st.sidebar.slider(
    "Light intensity (µmol photons/m²/s)",
    min_value=50,
    max_value=1200,
    value=400,
    step=10
)

light_hours = st.sidebar.slider(
    "Light period (hours/day)",
    min_value=4,
    max_value=24,
    value=16,
    step=1
)

st.sidebar.header("🫧 Gas & Mixing")

co2_flow = st.sidebar.slider(
    "CO₂ supply (L/min)",
    min_value=0.0,
    max_value=5.0,
    value=0.8,
    step=0.1
)

mixing = st.sidebar.slider(
    "Mixing/agitation (%)",
    min_value=10,
    max_value=100,
    value=70,
    step=5
)

st.sidebar.header("💧 Wastewater Characteristics")

wastewater_fraction = st.sidebar.slider(
    "Wastewater fraction (%)",
    min_value=10,
    max_value=100,
    value=70,
    step=5
)

nitrogen = st.sidebar.slider(
    "Initial nitrogen (mg/L)",
    min_value=5.0,
    max_value=200.0,
    value=60.0,
    step=5.0
)

phosphorus = st.sidebar.slider(
    "Initial phosphorus (mg/L)",
    min_value=1.0,
    max_value=50.0,
    value=10.0,
    step=1.0
)

organic_carbon = st.sidebar.slider(
    "Organic carbon/COD (mg/L)",
    min_value=20.0,
    max_value=1000.0,
    value=300.0,
    step=10.0
)

# ============================================================
# MODEL FUNCTIONS
# ============================================================

def gaussian_factor(value, optimum, width):
    """Environmental response factor between approximately 0 and 1."""
    return np.exp(-((value - optimum) ** 2) / (2 * width ** 2))


def light_response(I):
    """
    Simplified photosynthetic light response.
    Includes light saturation and photoinhibition.
    """
    Ik = 220.0
    I_inhibition = 900.0

    saturation = I / (I + Ik)
    inhibition = np.exp(-max(I - I_inhibition, 0) / 600)

    return saturation * inhibition


def calculate_simulation():

    # --------------------------------------------------------
    # Time
    # --------------------------------------------------------

    days = np.linspace(0, cultivation_time, cultivation_time * 24 + 1)

    dt = days[1] - days[0]

    # --------------------------------------------------------
    # Environmental factors
    # --------------------------------------------------------

    temperature_factor = gaussian_factor(
        temperature,
        optimum=28,
        width=6
    )

    pH_factor = gaussian_factor(
        pH,
        optimum=7.5,
        width=1.2
    )

    light_factor = light_response(light_intensity)

    mixing_factor = 0.65 + 0.35 * (mixing / 100)

    photoperiod_factor = light_hours / 24

    # CO₂ availability factor
    co2_factor = co2_flow / (co2_flow + 0.5)

    # Wastewater dilution factor
    wastewater_factor = 0.5 + 0.5 * (wastewater_fraction / 100)

    # --------------------------------------------------------
    # Maximum specific growth rate
    # --------------------------------------------------------

    mu_max = 0.075  # per hour

    environmental_factor = (
        temperature_factor
        * pH_factor
        * light_factor
        * mixing_factor
        * wastewater_factor
    )

    # Convert hourly growth into effective daily growth
    mu_effective = (
        mu_max
        * environmental_factor
        * photoperiod_factor
        * (0.55 + 0.45 * co2_factor)
    )

    # --------------------------------------------------------
    # Nutrient limitation
    # --------------------------------------------------------

    N_K = 20.0
    P_K = 3.0
    COD_K = 150.0

    nitrogen_factor = nitrogen / (nitrogen + N_K)
    phosphorus_factor = phosphorus / (phosphorus + P_K)
    carbon_factor = organic_carbon / (organic_carbon + COD_K)

    nutrient_factor = min(
        nitrogen_factor,
        phosphorus_factor,
        0.7 + 0.3 * carbon_factor
    )

    mu_effective *= nutrient_factor

    # --------------------------------------------------------
    # Arrays
    # --------------------------------------------------------

    biomass = np.zeros(len(days))
    nitrogen_remaining = np.zeros(len(days))
    phosphorus_remaining = np.zeros(len(days))
    cod_remaining = np.zeros(len(days))

    co2_fixed = np.zeros(len(days))
    oxygen_generated = np.zeros(len(days))

    biomass[0] = initial_biomass
    nitrogen_remaining[0] = nitrogen
    phosphorus_remaining[0] = phosphorus
    cod_remaining[0] = organic_carbon

    # --------------------------------------------------------
    # Dynamic simulation
    # --------------------------------------------------------

    for i in range(1, len(days)):

        # Current concentrations
        X = biomass[i - 1]

        N = nitrogen_remaining[i - 1]
        P = phosphorus_remaining[i - 1]
        COD = cod_remaining[i - 1]

        # Dynamic nutrient limitation
        N_lim = N / (N + N_K)
        P_lim = P / (P + P_K)
        COD_lim = COD / (COD + COD_K)

        dynamic_nutrient_factor = min(
            N_lim,
            P_lim,
            0.7 + 0.3 * COD_lim
        )

        # Growth rate
        mu = mu_effective * dynamic_nutrient_factor

        # Carrying capacity influenced by nutrient availability
        nutrient_capacity = (
            2.5
            + 0.015 * nitrogen
            + 0.04 * phosphorus
            + 0.002 * organic_carbon
        )

        # Logistic growth
        growth = (
            mu
            * X
            * (1 - X / nutrient_capacity)
        )

        # Prevent negative growth
        growth = max(growth, 0)

        # Biomass change
        biomass[i] = X + growth * dt * 24

        # ----------------------------------------------------
        # Nutrient uptake
        # ----------------------------------------------------

        biomass_gain = growth * dt * 24

        # Approximate uptake coefficients
        N_uptake = biomass_gain * 70.0
        P_uptake = biomass_gain * 10.0

        # COD removal
        COD_removal = biomass_gain * 180.0

        nitrogen_remaining[i] = max(
            N - N_uptake * 0.015,
            0
        )

        phosphorus_remaining[i] = max(
            P - P_uptake * 0.003,
            0
        )

        cod_remaining[i] = max(
            COD - COD_removal * 0.015,
            0
        )

        # ----------------------------------------------------
        # CO₂ fixation
        # ----------------------------------------------------

        co2_productivity_factor = (
            1.6
            * light_factor
            * co2_factor
            * mixing_factor
        )

        co2_fixed[i] = (
            co2_fixed[i - 1]
            + max(biomass_gain, 0)
            * co2_productivity_factor
            * 1.8
        )

        # ----------------------------------------------------
        # Oxygen generation
        # ----------------------------------------------------

        oxygen_generated[i] = (
            oxygen_generated[i - 1]
            + max(biomass_gain, 0)
            * light_factor
            * 1.4
        )

    # ========================================================
    # FINAL RESULTS
    # ========================================================

    final_biomass = biomass[-1]

    initial_total_biomass = (
        initial_biomass * reactor_volume
    )

    final_total_biomass = (
        final_biomass * reactor_volume
    )

    biomass_productivity = (
        (final_biomass - initial_biomass)
        / cultivation_time
    )

    total_biomass_produced = (
        final_total_biomass
        - initial_total_biomass
    )

    # Nutrient removal
    N_removal_percent = (
        (nitrogen - nitrogen_remaining[-1])
        / nitrogen
        * 100
        if nitrogen > 0 else 0
    )

    P_removal_percent = (
        (phosphorus - phosphorus_remaining[-1])
        / phosphorus
        * 100
        if phosphorus > 0 else 0
    )

    COD_removal_percent = (
        (organic_carbon - cod_remaining[-1])
        / organic_carbon
        * 100
        if organic_carbon > 0 else 0
    )

    # ========================================================
    # BIOMASS COMPOSITION
    # ========================================================

    # Environmental conditions influence composition
    protein_fraction = (
        0.30
        + 0.08 * nutrient_factor
        + 0.04 * nitrogen_factor
    )

    lipid_fraction = (
        0.18
        + 0.10 * (1 - nitrogen_factor)
        + 0.04 * max(light_factor - 0.5, 0)
    )

    carbohydrate_fraction = (
        1
        - protein_fraction
        - lipid_fraction
    )

    # Normalize
    total_fraction = (
        protein_fraction
        + lipid_fraction
        + carbohydrate_fraction
    )

    protein_fraction /= total_fraction
    lipid_fraction /= total_fraction
    carbohydrate_fraction /= total_fraction

    protein_mass = (
        final_total_biomass
        * protein_fraction
    )

    lipid_mass = (
        final_total_biomass
        * lipid_fraction
    )

    carbohydrate_mass = (
        final_total_biomass
        * carbohydrate_fraction
    )

    # ========================================================
    # WATER & RESOURCE ESTIMATION
    # ========================================================

    water_processed = reactor_volume * wastewater_fraction / 100

    co2_supplied = (
        co2_flow
        * 60
        * 24
        * cultivation_time
    )

    co2_utilization = (
        min(
            co2_fixed[-1] / max(co2_supplied, 0.001) * 100,
            100
        )
        if co2_supplied > 0
        else 0
    )

    # ========================================================
    # RETURN DATA
    # ========================================================

    results = {
        "days": days,
        "biomass": biomass,
        "nitrogen": nitrogen_remaining,
        "phosphorus": phosphorus_remaining,
        "cod": cod_remaining,
        "co2_fixed": co2_fixed,
        "oxygen": oxygen_generated,
        "final_biomass": final_biomass,
        "total_biomass": final_total_biomass,
        "biomass_productivity": biomass_productivity,
        "total_biomass_produced": total_biomass_produced,
        "N_removal": N_removal_percent,
        "P_removal": P_removal_percent,
        "COD_removal": COD_removal_percent,
        "protein_fraction": protein_fraction,
        "lipid_fraction": lipid_fraction,
        "carbohydrate_fraction": carbohydrate_fraction,
        "protein_mass": protein_mass,
        "lipid_mass": lipid_mass,
        "carbohydrate_mass": carbohydrate_mass,
        "water_processed": water_processed,
        "co2_supplied": co2_supplied,
        "co2_utilization": co2_utilization,
        "temperature_factor": temperature_factor,
        "pH_factor": pH_factor,
        "light_factor": light_factor,
        "nutrient_factor": nutrient_factor
    }

    return results


# ============================================================
# RUN SIMULATION
# ============================================================

results = calculate_simulation()

# ============================================================
# PERFORMANCE SUMMARY
# ============================================================

st.header("📊 Simulation Results")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Final Biomass",
        f"{results['final_biomass']:.2f} g/L"
    )

with col2:
    st.metric(
        "Total Biomass",
        f"{results['total_biomass']:.1f} g"
    )

with col3:
    st.metric(
        "Biomass Productivity",
        f"{results['biomass_productivity']:.3f} g/L/day"
    )

with col4:
    st.metric(
        "Biomass Produced",
        f"{results['total_biomass_produced']:.1f} g"
    )

# ============================================================
# ENVIRONMENTAL PERFORMANCE
# ============================================================

st.subheader("💧 Wastewater Treatment Performance")

c1, c2, c3 = st.columns(3)

with c1:
    st.metric(
        "Nitrogen Removal",
        f"{results['N_removal']:.1f}%"
    )

with c2:
    st.metric(
        "Phosphorus Removal",
        f"{results['P_removal']:.1f}%"
    )

with c3:
    st.metric(
        "COD Removal",
        f"{results['COD_removal']:.1f}%"
    )

# ============================================================
# BIOMASS COMPOSITION
# ============================================================

st.subheader("🧪 Predicted Biomass Composition")

c1, c2, c3 = st.columns(3)

with c1:
    st.metric(
        "Protein",
        f"{results['protein_fraction'] * 100:.1f}%",
        f"{results['protein_mass']:.1f} g"
    )

with c2:
    st.metric(
        "Lipids",
        f"{results['lipid_fraction'] * 100:.1f}%",
        f"{results['lipid_mass']:.1f} g"
    )

with c3:
    st.metric(
        "Carbohydrates",
        f"{results['carbohydrate_fraction'] * 100:.1f}%",
        f"{results['carbohydrate_mass']:.1f} g"
    )

# ============================================================
# RESOURCE BALANCE
# ============================================================

st.subheader("♻️ Resource & Carbon Balance")

r1, r2, r3 = st.columns(3)

with r1:
    st.metric(
        "Wastewater Processed",
        f"{results['water_processed']:.1f} L"
    )

with r2:
    st.metric(
        "Estimated CO₂ Supplied",
        f"{results['co2_supplied']:.1f} L"
    )

with r3:
    st.metric(
        "CO₂ Utilization",
        f"{results['co2_utilization']:.1f}%"
    )

# ============================================================
# BIOMASS GROWTH GRAPH
# ============================================================

st.header("📈 Biomass Growth")

fig_growth = go.Figure()

fig_growth.add_trace(
    go.Scatter(
        x=results["days"],
        y=results["biomass"],
        mode="lines",
        name="Biomass"
    )
)

fig_growth.update_layout(
    xaxis_title="Cultivation Time (days)",
    yaxis_title="Biomass Concentration (g/L)",
    hovermode="x unified"
)

st.plotly_chart(
    fig_growth,
    use_container_width=True
)

# ============================================================
# NUTRIENT REMOVAL GRAPH
# ============================================================

st.header("💧 Nutrient Dynamics")

fig_nutrients = go.Figure()

fig_nutrients.add_trace(
    go.Scatter(
        x=results["days"],
        y=results["nitrogen"],
        mode="lines",
        name="Nitrogen"
    )
)

fig_nutrients.add_trace(
    go.Scatter(
        x=results["days"],
        y=results["phosphorus"],
        mode="lines",
        name="Phosphorus"
    )

)

fig_nutrients.add_trace(
    go.Scatter(
        x=results["days"],
        y=results["cod"],
        mode="lines",
        name="COD"
    )
)

fig_nutrients.update_layout(
    xaxis_title="Cultivation Time (days)",
    yaxis_title="Remaining Concentration (mg/L)",
    hovermode="x unified"
)

st.plotly_chart(
    fig_nutrients,
    use_container_width=True
)

# ============================================================
# CO2 / OXYGEN GRAPH
# ============================================================

st.header("🌱 Carbon & Oxygen Dynamics")

fig_gas = go.Figure()

fig_gas.add_trace(
    go.Scatter(
        x=results["days"],
        y=results["co2_fixed"],
        mode="lines",
        name="CO₂ Fixed"
    )
)

fig_gas.add_trace(
    go.Scatter(
        x=results["days"],
        y=results["oxygen"],
        mode="lines",
        name="O₂ Generated"
    )
)

fig_gas.update_layout(
    xaxis_title="Cultivation Time (days)",
    yaxis_title="Cumulative Amount",
    hovermode="x unified"
)

st.plotly_chart(
    fig_gas,
    use_container_width=True
)

# ============================================================
# FACTOR RESPONSE SUMMARY
# ============================================================

st.header("⚙️ Process Factor Performance")

factor_df = pd.DataFrame({
    "Factor": [
        "Temperature",
        "pH",
        "Light",
        "Nutrients"
    ],
    "Relative Factor": [
        results["temperature_factor"],
        results["pH_factor"],
        results["light_factor"],
        results["nutrient_factor"]
    ]
})

factor_df["Relative Factor (%)"] = (
    factor_df["Relative Factor"] * 100
)

st.dataframe(
    factor_df[
        ["Factor", "Relative Factor (%)"]
    ].round(2),
    use_container_width=True,
    hide_index=True
)

# ============================================================
# DETAILED RESULTS TABLE
# ============================================================

st.header("📋 Final Simulation Summary")

summary_df = pd.DataFrame({
    "Parameter": [
        "Working volume",
        "Cultivation time",
        "Temperature",
        "pH",
        "Light intensity",
        "Light period",
        "CO₂ flow",
        "Mixing",
        "Wastewater fraction",
        "Initial nitrogen",
        "Initial phosphorus",
        "Initial COD",
        "Final biomass concentration",
        "Total biomass",
        "Biomass productivity",
        "Nitrogen removal",
        "Phosphorus removal",
        "COD removal",
        "Protein mass",
        "Lipid mass",
        "Carbohydrate mass",
        "Water processed",
        "CO₂ supplied",
        "CO₂ utilization"
    ],
    "Value": [
        f"{reactor_volume:.1f} L",
        f"{cultivation_time} days",
        f"{temperature:.1f} °C",
        f"{pH:.1f}",
        f"{light_intensity} µmol/m²/s",
        f"{light_hours} h/day",
        f"{co2_flow:.1f} L/min",
        f"{mixing}%",
        f"{wastewater_fraction}%",
        f"{nitrogen:.1f} mg/L",
        f"{phosphorus:.1f} mg/L",
        f"{organic_carbon:.1f} mg/L",
        f"{results['final_biomass']:.3f} g/L",
        f"{results['total_biomass']:.2f} g",
        f"{results['biomass_productivity']:.4f} g/L/day",
        f"{results['N_removal']:.2f}%",
        f"{results['P_removal']:.2f}%",
        f"{results['COD_removal']:.2f}%",
        f"{results['protein_mass']:.2f} g",
        f"{results['lipid_mass']:.2f} g",
        f"{results['carbohydrate_mass']:.2f} g",
        f"{results['water_processed']:.2f} L",
        f"{results['co2_supplied']:.2f} L",
        f"{results['co2_utilization']:.2f}%"
    ]
})

st.dataframe(
    summary_df,
    use_container_width=True,
    hide_index=True
)

# ============================================================
# DOWNLOAD DATA
# ============================================================

st.header("⬇️ Export Simulation Data")

export_df = pd.DataFrame({
    "Day": results["days"],
    "Biomass_g_L": results["biomass"],
    "Nitrogen_mg_L": results["nitrogen"],
    "Phosphorus_mg_L": results["phosphorus"],
    "COD_mg_L": results["cod"],
    "CO2_fixed": results["co2_fixed"],
    "Oxygen_generated": results["oxygen"]
})

csv = export_df.to_csv(index=False)

st.download_button(
    label="Download simulation data (CSV)",
    data=csv,
    file_name="microalgal_bioreactor_simulation.csv",
    mime="text/csv"
)

# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Microalgal Bioreactor Simulator | Conceptual research model | "
    "Adjust parameters in the sidebar to explore process sensitivity."
)

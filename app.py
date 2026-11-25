"""Aplikacja webowa Plotly Dash: Symulator regulacji temperatury w szklarni."""

from dash import Dash, dcc, html, Input, Output, State
import numpy as np
import plotly.graph_objects as go

from greenhouse_model import (
    GREENHOUSES,
    WEATHER_LABELS,
    simulate_greenhouse,
)

app = Dash(__name__)
app.title = "Symulator szklarni – Podstawy Automatyki"

CARD_STYLE = {
    "backgroundColor": "#ffffff",
    "borderRadius": "10px",
    "padding": "16px 20px",
    "boxShadow": "0 2px 8px rgba(0, 0, 0, 0.08)",
    "marginBottom": "16px",
}

LABEL_STYLE = {
    "fontWeight": "600",
    "fontSize": "13px",
    "color": "#2c3e50",
    "marginTop": "10px",
    "marginBottom": "4px",
    "display": "block",
}


def make_slider(
    slider_id: str,
    min_val: float,
    max_val: float,
    step: float,
    default_val: float,
    unit: str = "",
) -> dcc.Slider:
    marks = {
        min_val: f"{min_val}{unit}",
        max_val: f"{max_val}{unit}",
    }
    return dcc.Slider(
        id=slider_id,
        min=min_val,
        max=max_val,
        step=step,
        value=default_val,
        marks=marks,
        tooltip={"placement": "bottom", "always_visible": True},
    )


app.layout = html.Div(
    style={
        "fontFamily": "Segoe UI, Roboto, Arial, sans-serif",
        "backgroundColor": "#f4f6f9",
        "minHeight": "100vh",
        "padding": "20px 28px",
        "color": "#1f2937",
    },
    children=[
        html.Div(
            style={"maxWidth": "1400px", "margin": "0 auto"},
            children=[
                html.H2(
                    "Symulator układu automatycznej regulacji temperatury w szklarni",
                    style={"margin": "0 0 4px 0", "color": "#1e293b"},
                ),
                html.P(
                    "Podstawy Automatyki – Sara Rachmańczuk, Maria Linkowska",
                    style={"margin": "0 0 18px 0", "color": "#64748b", "fontSize": "14px"},
                ),
                html.Div(
                    style={
                        "display": "grid",
                        "gridTemplateColumns": "360px 1fr",
                        "gap": "20px",
                        "alignItems": "start",
                    },
                    children=[
                        # Panel sterowania (lewa kolumna)
                        html.Div(
                            style=CARD_STYLE,
                            children=[
                                html.H4(
                                    "Parametry symulacji",
                                    style={"margin": "0 0 12px 0", "color": "#0f172a"},
                                ),
                                html.Label("Wybór szklarni:", style=LABEL_STYLE),
                                dcc.Dropdown(
                                    id="greenhouse-select",
                                    options=[
                                        {"label": gh.name, "value": key}
                                        for key, gh in GREENHOUSES.items()
                                    ],
                                    value="mala",
                                    clearable=False,
                                ),
                                html.Div(
                                    id="greenhouse-info",
                                    style={
                                        "fontSize": "12px",
                                        "color": "#475569",
                                        "backgroundColor": "#f8fafc",
                                        "padding": "8px 10px",
                                        "borderRadius": "6px",
                                        "marginTop": "8px",
                                        "border": "1px solid #e2e8f0",
                                    },
                                ),
                                html.Label("Warunki pogodowe:", style=LABEL_STYLE),
                                dcc.Dropdown(
                                    id="weather-select",
                                    options=[
                                        {"label": label, "value": key}
                                        for key, label in WEATHER_LABELS.items()
                                    ],
                                    value="sloneczny",
                                    clearable=False,
                                ),
                                html.Label("Temperatura zadana T_zad [°C]:", style=LABEL_STYLE),
                                make_slider("slider-tzad", 10, 35, 0.5, 24, "°C"),
                                html.Label("Temperatura początkowa T_0 [°C]:", style=LABEL_STYLE),
                                make_slider("slider-t0", -10, 40, 0.5, 12, "°C"),
                                html.Div(
                                    id="const-weather-box",
                                    children=[
                                        html.Label(
                                            "Temperatura zewnętrzna T_zew (stałe warunki) [°C]:",
                                            style=LABEL_STYLE,
                                        ),
                                        make_slider("slider-tzew", -20, 35, 1, 10, "°C"),
                                        html.Label(
                                            "Nasłonecznienie E (stałe warunki) [W/m²]:",
                                            style=LABEL_STYLE,
                                        ),
                                        make_slider("slider-e", 0, 1000, 25, 500, ""),
                                    ],
                                ),
                                html.Hr(style={"margin": "14px 0", "borderColor": "#e2e8f0"}),
                                html.Label("Wzmocnienie regulatora Kp [1/°C]:", style=LABEL_STYLE),
                                make_slider("slider-kp", 0.5, 20, 0.5, 5.0, ""),
                                html.Label("Czas zdwojenia Ti [s]:", style=LABEL_STYLE),
                                make_slider("slider-ti", 60, 1800, 30, 300, "s"),
                                html.Label("Okres próbkowania Tp [s]:", style=LABEL_STYLE),
                                make_slider("slider-tp", 1, 60, 1, 10, "s"),
                                html.Label("Czas symulacji [h]:", style=LABEL_STYLE),
                                make_slider("slider-hours", 1, 24, 1, 12, "h"),
                                html.Button(
                                    "wykonaj obliczenia",
                                    id="run-btn",
                                    n_clicks=0,
                                    style={
                                        "width": "100%",
                                        "marginTop": "16px",
                                        "padding": "12px",
                                        "backgroundColor": "#2563eb",
                                        "color": "#ffffff",
                                        "border": "none",
                                        "borderRadius": "8px",
                                        "fontSize": "15px",
                                        "fontWeight": "600",
                                        "cursor": "pointer",
                                    },
                                ),
                            ],
                        ),
                        # Wykresy (prawa kolumna)
                        html.Div(
                            children=[
                                html.Div(
                                    id="summary-bar",
                                    style={
                                        **CARD_STYLE,
                                        "display": "flex",
                                        "justifyContent": "space-between",
                                        "flexWrap": "wrap",
                                        "gap": "12px",
                                        "fontSize": "13px",
                                    },
                                ),
                                html.Div(
                                    style=CARD_STYLE,
                                    children=[dcc.Graph(id="graph-temp", style={"height": "340px"})],
                                ),
                                html.Div(
                                    style=CARD_STYLE,
                                    children=[dcc.Graph(id="graph-energy", style={"height": "340px"})],
                                ),
                                html.Div(
                                    style=CARD_STYLE,
                                    children=[dcc.Graph(id="graph-control", style={"height": "300px"})],
                                ),
                            ]
                        ),
                    ],
                ),
            ],
        )
    ],
)


@app.callback(
    Output("greenhouse-info", "children"),
    Output("slider-kp", "value"),
    Output("slider-ti", "value"),
    Input("greenhouse-select", "value"),
)
def update_greenhouse_defaults(gh_key: str):
    gh = GREENHOUSES[gh_key]
    info = (
        f"Powierzchnia podłogi Ap = {gh.A_p:.0f} m², obudowy Aob = {gh.A_ob:.1f} m², "
        f"pojemność C = {gh.C / 1000:.0f} kJ/K | "
        f"Grzałka max: {gh.P_grz_max / 1000:.0f} kW, wentylator max: {gh.Q_went_max:.1f} m³/s"
    )
    return info, gh.default_kp, gh.default_ti


@app.callback(
    Output("const-weather-box", "style"),
    Input("weather-select", "value"),
)
def toggle_const_weather(weather_key: str):
    if weather_key == "stale":
        return {"display": "block"}
    return {"display": "none"}


@app.callback(
    Output("summary-bar", "children"),
    Output("graph-temp", "figure"),
    Output("graph-energy", "figure"),
    Output("graph-control", "figure"),
    Input("run-btn", "n_clicks"),
    State("greenhouse-select", "value"),
    State("weather-select", "value"),
    State("slider-tzad", "value"),
    State("slider-t0", "value"),
    State("slider-tzew", "value"),
    State("slider-e", "value"),
    State("slider-kp", "value"),
    State("slider-ti", "value"),
    State("slider-tp", "value"),
    State("slider-hours", "value"),
)
def run_simulation(
    n_clicks: int,
    gh_key: str,
    weather_key: str,
    T_zad: float,
    T_0: float,
    T_zew: float,
    E_const: float,
    Kp: float,
    Ti: float,
    Tp: float,
    sim_hours: float,
):
    res = simulate_greenhouse(
        greenhouse_key=gh_key,
        weather_key=weather_key,
        T_zad=T_zad,
        T_0=T_0,
        Kp=Kp,
        Ti=Ti,
        Tp=Tp,
        sim_hours=sim_hours,
        T_zew_const=T_zew,
        E_const=E_const,
    )

    t_h = res["t_hours"]
    T = res["T"]
    T_m = res["T_m"]
    T_zad_arr = res["T_zad"]
    T_zew_arr = res["T_zew"]

    # Metryki podsumowujące
    t_max = float(np.max(T))
    t_min = float(np.min(T))
    t_end = float(T[-1])
    iae = float(np.sum(np.abs(res["e"])) * Tp)

    summary = [
        html.Span([html.B("temperatura końcowa: "), f"{t_end:.2f} °C"]),
        html.Span([html.B("zakres T(t): "), f"{t_min:.2f} … {t_max:.2f} °C"]),
        html.Span([html.B("całka |e| (IAE): "), f"{iae:.1f} °C·s"]),
        html.Span([html.B("nastawy: "), f"Kp = {Kp}, Ti = {Ti} s, Tp = {Tp} s"]),
    ]

    # Wykres a) temperatura w szklarni i temperatura zadana
    fig_temp = go.Figure()
    fig_temp.add_trace(
        go.Scatter(x=t_h, y=T, mode="lines", name="temperatura w szklarni T(t)", line=dict(color="#ef4444", width=2.5))
    )
    fig_temp.add_trace(
        go.Scatter(x=t_h, y=T_m, mode="lines", name="temperatura zmierzona Tm(t)", line=dict(color="#f97316", width=1.5, dash="dot"))
    )
    fig_temp.add_trace(
        go.Scatter(x=t_h, y=T_zad_arr, mode="lines", name="temperatura zadana Tzad", line=dict(color="#16a34a", width=2, dash="dash"))
    )
    fig_temp.add_trace(
        go.Scatter(x=t_h, y=T_zew_arr, mode="lines", name="temperatura zewnętrzna Tzew(t)", line=dict(color="#3b82f6", width=1.5, dash="dashdot"))
    )
    fig_temp.update_layout(
        title="a) temperatura w szklarni i temperatura zadana",
        xaxis_title="czas [h]",
        yaxis_title="temperatura [°C]",
        template="plotly_white",
        margin=dict(l=50, r=20, t=45, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    # Wykres b) bilans energii – dopływy (+) i odpływy (-) ciepła w kW
    fig_energy = go.Figure()
    fig_energy.add_trace(
        go.Scatter(x=t_h, y=res["P_sl"] / 1000.0, mode="lines", name="dopływ ze słońca (+Psł)", line=dict(color="#eab308", width=2))
    )
    fig_energy.add_trace(
        go.Scatter(x=t_h, y=res["P_grz"] / 1000.0, mode="lines", name="dopływ z grzałki (+Pgrz)", line=dict(color="#ef4444", width=2))
    )
    fig_energy.add_trace(
        go.Scatter(x=t_h, y=-res["P_ob"] / 1000.0, mode="lines", name="straty przez obudowę (-Pob)", line=dict(color="#3b82f6", width=2))
    )
    fig_energy.add_trace(
        go.Scatter(x=t_h, y=-res["P_went"] / 1000.0, mode="lines", name="odpływ przez wentylację (-Pwent)", line=dict(color="#06b6d4", width=2))
    )
    fig_energy.add_trace(
        go.Scatter(x=t_h, y=-res["P_drzwi"] / 1000.0, mode="lines", name="odpływ przez drzwi (-Pdrzwi)", line=dict(color="#8b5cf6", width=1.8, dash="dash"))
    )
    fig_energy.update_layout(
        title="b) bilans energii – dopływy i odpływy ciepła",
        xaxis_title="czas [h]",
        yaxis_title="moc cieplna [kW]",
        template="plotly_white",
        margin=dict(l=50, r=20, t=45, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    # Wykres c) sygnał sterujący u(n)
    fig_control = go.Figure()
    fig_control.add_trace(
        go.Scatter(x=t_h, y=res["u"], mode="lines", name="sygnał sterujący u(n)", line=dict(color="#0f172a", width=2))
    )
    fig_control.add_hline(y=10, line_dash="dash", line_color="#ef4444", annotation_text="maks. grzanie (+10)")
    fig_control.add_hline(y=-10, line_dash="dash", line_color="#3b82f6", annotation_text="maks. wentylacja (-10)")
    fig_control.add_hline(y=0, line_dash="dot", line_color="#94a3b8")
    fig_control.update_layout(
        title="c) sygnał sterujący u(n)",
        xaxis_title="czas [h]",
        yaxis_title="sygnał u(n) [-]",
        yaxis=dict(range=[-11.5, 11.5]),
        template="plotly_white",
        margin=dict(l=50, r=20, t=45, b=40),
        showlegend=False,
    )

    return summary, fig_temp, fig_energy, fig_control


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)

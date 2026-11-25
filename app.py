"""
Symulator regulacji temperatury w szklarni - interfejs Plotly Dash.

Uruchomienie:
    pip install -r requirements.txt
    python app.py
    -> otworzyć http://127.0.0.1:8050 w przeglądarce
"""

from dash import Dash, dcc, html, Input, Output, State
import plotly.graph_objects as go

from model_szklarni import (
    SZKLARNIE, STEROWANIE_MINIMALNE, STEROWANIE_MAKSYMALNE,
    warunki_sloneczny_dzien, warunki_zachmurzenie, warunki_drzwi_i_wiatr, warunki_stale, symuluj,
)

# ---------------------------------------------------------------------------
# Kolory - każda wielkość ma zawsze ten sam kolor
# ---------------------------------------------------------------------------
KOLOR_TEMPERATURA_WEWNETRZNA = "#2a78d6"
KOLOR_BEZ_REGULACJI = "#eb6834"
KOLOR_TEMPERATURA_ZEWNETRZNA = "#1baf7a"
KOLOR_WARTOSC_ZADANA = "#52514e"
KOLOR_SLONCE = "#eda100"
KOLOR_GRZALKA = "#e34948"
KOLOR_OBUDOWA = "#008300"
KOLOR_WENTYLACJA = "#6250d6"
KOLOR_DRZWI = "#e87ba4"
KOLOR_STEROWANIE = "#2a78d6"
KOLOR_SIATKI = "#e6e5e1"

WARUNKI = {
    "sloneczny_dzien": {"etykieta": "słoneczny dzień (6:00–18:00)", "czas": 12, "temperatura_poczatkowa": 12},
    "zachmurzenie": {"etykieta": "nagłe zachmurzenie", "czas": 5, "temperatura_poczatkowa": 23},
    "drzwi_i_wiatr": {"etykieta": "otwarte drzwi i silny wiatr", "czas": 5, "temperatura_poczatkowa": 22},
    "stale": {"etykieta": "stałe warunki (suwaki poniżej)", "czas": 5, "temperatura_poczatkowa": 18},
}


def zbuduj_warunki(klucz_warunkow, naslonecznienie, temperatura_zewnetrzna):
    if klucz_warunkow == "sloneczny_dzien":
        return warunki_sloneczny_dzien()
    if klucz_warunkow == "zachmurzenie":
        return warunki_zachmurzenie()
    if klucz_warunkow == "drzwi_i_wiatr":
        return warunki_drzwi_i_wiatr()
    return warunki_stale(naslonecznienie, temperatura_zewnetrzna)


# ---------------------------------------------------------------------------
# Elementy interfejsu. Suwaki mają stałe minimum i maksimum, więc
# użytkownik nie ustawi wartości bez sensu fizycznego.
# ---------------------------------------------------------------------------
def suwak(identyfikator, etykieta, jednostka, minimum, maksimum, krok, wartosc):
    return html.Div(className="suwak", children=[
        html.Label(f"{etykieta} [{jednostka}]", htmlFor=identyfikator),
        dcc.Slider(id=identyfikator, min=minimum, max=maksimum, step=krok, value=wartosc,
                   marks={minimum: str(minimum), maksimum: str(maksimum)},
                   tooltip={"placement": "bottom", "always_visible": True}),
    ])


def sekcja(tytul, *elementy):
    return html.Fieldset(className="sekcja", children=[html.Legend(tytul), *elementy])


szklarnia_domyslna = SZKLARNIE["ogrodnicza"]

panel_sterowania = html.Div(className="panel-sterowania", children=[
    sekcja("obiekt i warunki",
           html.Label("szklarnia", htmlFor="wybor_szklarni"),
           dcc.Dropdown(id="wybor_szklarni", clearable=False, value="ogrodnicza",
                        options=[{"label": szklarnia.nazwa, "value": klucz}
                                 for klucz, szklarnia in SZKLARNIE.items()]),
           html.P(id="opis_szklarni", className="opis"),
           html.Label("warunki pogodowe", htmlFor="wybor_warunkow"),
           dcc.Dropdown(id="wybor_warunkow", clearable=False, value="sloneczny_dzien",
                        options=[{"label": opis["etykieta"], "value": klucz} for klucz, opis in WARUNKI.items()]),
           html.P(id="opis_warunkow", className="opis")),

    sekcja("cel regulacji",
           suwak("temperatura_zadana", "temperatura zadana", "°C", 10, 35, 0.5, 24),
           suwak("temperatura_poczatkowa", "temperatura początkowa", "°C", -10, 40, 0.5, 12)),

    sekcja("regulator PI",
           dcc.Checklist(id="regulacja_wlaczona", value=["wlaczona"],
                         options=[{"label": " regulacja włączona", "value": "wlaczona"}]),
           suwak("wzmocnienie", "wzmocnienie Kp", "1/°C", 0.5, 20, 0.5, szklarnia_domyslna.dobrane_wzmocnienie),
           suwak("czas_zdwojenia", "czas zdwojenia Ti", "s", 60, 1800, 30, szklarnia_domyslna.dobrany_czas_zdwojenia),
           html.P("Po wybraniu szklarni suwaki ustawiają się na nastawy z doboru (dobor_nastaw.py).",
                  className="opis")),

    sekcja("stałe warunki",
           suwak("naslonecznienie", "nasłonecznienie", "W/m²", 0, 1000, 10, 500),
           suwak("temperatura_zewnetrzna", "temperatura zewnętrzna", "°C", -20, 35, 0.5, 10)),

    sekcja("symulacja",
           suwak("czas_symulacji", "czas symulacji", "h", 1, 24, 0.5, 12),
           suwak("okres_probkowania", "okres próbkowania Tp", "s", 1, 60, 1, 10)),

    html.Button("wykonaj obliczenia", id="przycisk_obliczen", n_clicks=0, className="przycisk"),
])


def kafelek(identyfikator, tytul):
    return html.Div(className="kafelek", children=[
        html.Div(tytul, className="kafelek-tytul"),
        html.Div(id=identyfikator, className="kafelek-wartosc"),
    ])


def wykres(identyfikator):
    return dcc.Graph(id=identyfikator, config={"displaylogo": False}, className="wykres")


panel_wynikow = html.Div(className="panel-wynikow", children=[
    html.Div(className="kafelki", children=[
        kafelek("wskaznik_przekroczenie", "maks. przekroczenie T_zad"),
        kafelek("wskaznik_czas_regulacji", "czas regulacji (±0,5 °C)"),
        kafelek("wskaznik_uchyb_koncowy", "uchyb na końcu"),
        kafelek("wskaznik_calka_uchybu", "całka |uchybu| (IAE)"),
        kafelek("wskaznik_energia", "energia grzania"),
    ]),
    dcc.Loading(type="dot", children=[
        wykres("wykres_temperatury"),
        wykres("wykres_bilansu"),
        wykres("wykres_sterowania"),
    ]),
])

aplikacja = Dash(__name__, title="symulator szklarni")
aplikacja.layout = html.Div(className="strona", children=[
    html.Header(children=[
        html.H1("regulacja temperatury w szklarni"),
        html.P("Regulator PI liczy sygnał sterujący u(n) z zakresu −10…10: dla u > 0 pracuje grzałka, "
               "dla u < 0 wentylator wtłaczający chłodniejsze powietrze z zewnątrz. "
               "Ustaw parametry i kliknij „wykonaj obliczenia”."),
    ]),
    html.Main(className="uklad", children=[panel_sterowania, panel_wynikow]),
])


# ---------------------------------------------------------------------------
# Callback 1: wybór szklarni -> nastawy z doboru
# ---------------------------------------------------------------------------
@aplikacja.callback(
    Output("wzmocnienie", "value"),
    Output("czas_zdwojenia", "value"),
    Output("opis_szklarni", "children"),
    Input("wybor_szklarni", "value"),
)
def ustaw_nastawy_dla_szklarni(klucz_szklarni):
    szklarnia = SZKLARNIE[klucz_szklarni]
    opis = (f"{szklarnia.powierzchnia_podlogi:.0f} m² podłogi, U = {szklarnia.wspolczynnik_przenikania_ciepla} W/(m²·K), "
            f"grzałka {szklarnia.maksymalna_moc_grzalki / 1000:.0f} kW, "
            f"wentylator {szklarnia.maksymalny_przeplyw_wentylatora} m³/s")
    return szklarnia.dobrane_wzmocnienie, szklarnia.dobrany_czas_zdwojenia, opis


# ---------------------------------------------------------------------------
# Callback 2: wybór warunków -> zalecany czas i temperatura początkowa
# ---------------------------------------------------------------------------
@aplikacja.callback(
    Output("czas_symulacji", "value"),
    Output("temperatura_poczatkowa", "value"),
    Output("naslonecznienie", "disabled"),
    Output("temperatura_zewnetrzna", "disabled"),
    Output("opis_warunkow", "children"),
    Input("wybor_warunkow", "value"),
)
def ustaw_suwaki_dla_warunkow(klucz_warunkow):
    opis = WARUNKI[klucz_warunkow]
    warunki_z_suwakow = klucz_warunkow == "stale"
    warunki = zbuduj_warunki(klucz_warunkow, 0.0, 0.0)
    return (opis["czas"], opis["temperatura_poczatkowa"],
            not warunki_z_suwakow, not warunki_z_suwakow, warunki.opis)


# ---------------------------------------------------------------------------
# Callback 3: przycisk "wykonaj obliczenia" -> symulacja i wykresy
# ---------------------------------------------------------------------------
@aplikacja.callback(
    Output("wykres_temperatury", "figure"),
    Output("wykres_bilansu", "figure"),
    Output("wykres_sterowania", "figure"),
    Output("wskaznik_przekroczenie", "children"),
    Output("wskaznik_czas_regulacji", "children"),
    Output("wskaznik_uchyb_koncowy", "children"),
    Output("wskaznik_calka_uchybu", "children"),
    Output("wskaznik_energia", "children"),
    Input("przycisk_obliczen", "n_clicks"),
    State("wybor_szklarni", "value"),
    State("wybor_warunkow", "value"),
    State("temperatura_zadana", "value"),
    State("temperatura_poczatkowa", "value"),
    State("regulacja_wlaczona", "value"),
    State("wzmocnienie", "value"),
    State("czas_zdwojenia", "value"),
    State("naslonecznienie", "value"),
    State("temperatura_zewnetrzna", "value"),
    State("czas_symulacji", "value"),
    State("okres_probkowania", "value"),
)
def wykonaj_obliczenia(liczba_klikniec, klucz_szklarni, klucz_warunkow, temperatura_zadana,
                       temperatura_poczatkowa, regulacja_wlaczona, wzmocnienie, czas_zdwojenia,
                       naslonecznienie, temperatura_zewnetrzna, czas_symulacji, okres_probkowania):
    szklarnia = SZKLARNIE[klucz_szklarni]
    warunki = zbuduj_warunki(klucz_warunkow, naslonecznienie, temperatura_zewnetrzna)
    wyniki = symuluj(
        szklarnia, warunki,
        temperatura_zadana=temperatura_zadana,
        temperatura_poczatkowa=temperatura_poczatkowa,
        wzmocnienie=wzmocnienie,
        czas_zdwojenia=czas_zdwojenia,
        okres_probkowania=okres_probkowania,
        czas_symulacji_godziny=czas_symulacji,
        regulacja_wlaczona="wlaczona" in (regulacja_wlaczona or []),
    )
    wskazniki = wyniki["wskazniki_jakosci"]
    return (
        wykres_temperatury(wyniki),
        wykres_bilansu(wyniki),
        wykres_sterowania(wyniki),
        f"{wskazniki['przeregulowanie']:.2f} °C",
        f"{wskazniki['czas_regulacji_minuty']:.0f} min",
        f"{wskazniki['uchyb_koncowy']:+.2f} °C",
        f"{wskazniki['calka_modulu_uchybu']:.2f} °C·h",
        f"{wskazniki['energia_grzania_kWh']:.1f} kWh",
    )


# ---------------------------------------------------------------------------
# Wykresy: a) temperatura, b) bilans energii, c) sygnał sterujący.
# Opisy małymi literami, tytuł mówi co widać (a nie "x vs czas").
# ---------------------------------------------------------------------------
def linia(figura, czas, wartosci, nazwa, kolor, jednostka, styl="solid"):
    figura.add_trace(go.Scatter(
        x=czas, y=wartosci, name=nazwa, mode="lines",
        line={"color": kolor, "width": 2, "dash": styl},
        hovertemplate=f"%{{y:.2f}} {jednostka}<extra>{nazwa}</extra>",
    ))


def wyglad(figura, tytul, opis_osi_y):
    figura.update_layout(
        title={"text": tytul, "x": 0, "xanchor": "left", "font": {"size": 15}},
        template="plotly_white", hovermode="x unified", height=330,
        margin={"l": 60, "r": 20, "t": 70, "b": 45},
        legend={"orientation": "h", "y": 1.13, "x": 0},
        font={"family": "system-ui, sans-serif", "size": 13, "color": "#0b0b0b"},
        xaxis_title="czas [h]", yaxis_title=opis_osi_y,
    )
    figura.update_xaxes(gridcolor=KOLOR_SIATKI)
    figura.update_yaxes(gridcolor=KOLOR_SIATKI, zeroline=False)
    return figura


def wykres_temperatury(wyniki):
    czas = wyniki["czas_godziny"]
    figura = go.Figure()
    linia(figura, czas, wyniki["temperatura_zadana"], "temperatura zadana", KOLOR_WARTOSC_ZADANA, "°C", "dash")
    linia(figura, czas, wyniki["temperatura_wewnetrzna"], "temperatura w szklarni", KOLOR_TEMPERATURA_WEWNETRZNA, "°C")
    linia(figura, czas, wyniki["temperatura_bez_regulacji"], "bez regulacji", KOLOR_BEZ_REGULACJI, "°C", "dot")
    linia(figura, czas, wyniki["temperatura_zewnetrzna"], "temperatura zewnętrzna", KOLOR_TEMPERATURA_ZEWNETRZNA, "°C")
    return wyglad(figura, "a) temperatura w szklarni dąży do temperatury zadanej", "temperatura [°C]")


def wykres_bilansu(wyniki):
    czas = wyniki["czas_godziny"]
    figura = go.Figure()
    linia(figura, czas, wyniki["moc_slonca_kW"], "dopływ: słońce", KOLOR_SLONCE, "kW")
    linia(figura, czas, wyniki["moc_grzalki_kW"], "dopływ: grzałka", KOLOR_GRZALKA, "kW")
    linia(figura, czas, [-moc for moc in wyniki["straty_obudowa_kW"]], "odpływ: przez szkło", KOLOR_OBUDOWA, "kW")
    linia(figura, czas, [-moc for moc in wyniki["straty_wentylacja_kW"]], "odpływ: wentylacja", KOLOR_WENTYLACJA, "kW")
    if any(wyniki["straty_drzwi_kW"]):
        linia(figura, czas, [-moc for moc in wyniki["straty_drzwi_kW"]], "odpływ: otwarte drzwi", KOLOR_DRZWI, "kW")
    figura.add_hline(y=0, line={"color": "#9a9994", "width": 1})
    return wyglad(figura, "b) bilans energii: dopływy ciepła (+) i odpływy (−)", "moc [kW]")


def wykres_sterowania(wyniki):
    czas = wyniki["czas_godziny"]
    figura = go.Figure()
    linia(figura, czas, wyniki["sterowanie"], "sygnał sterujący u(n)", KOLOR_STEROWANIE, "")
    figura.add_hline(y=0, line={"color": "#9a9994", "width": 1})
    figura.add_annotation(x=0, y=STEROWANIE_MAKSYMALNE, xref="paper", text="u > 0: grzałka",
                          showarrow=False, xanchor="left", yanchor="top", font={"color": KOLOR_GRZALKA, "size": 12})
    figura.add_annotation(x=0, y=STEROWANIE_MINIMALNE, xref="paper", text="u < 0: wentylator",
                          showarrow=False, xanchor="left", yanchor="bottom", font={"color": KOLOR_WENTYLACJA, "size": 12})
    figura = wyglad(figura, "c) sygnał sterujący regulatora PI", "u [–]")
    figura.update_yaxes(range=[STEROWANIE_MINIMALNE - 0.5, STEROWANIE_MAKSYMALNE + 0.5])
    figura.update_layout(showlegend=False)
    return figura


if __name__ == "__main__":
    aplikacja.run(debug=True)

"""
Model matematyczny szklarni i układu automatycznej regulacji temperatury.

Proces: szklarnia nagrzewana przez słońce i grzałkę, chłodzona przez
wentylator, który wtłacza chłodniejsze powietrze z zewnątrz.

Równanie różniczkowe (bilans energii):

    C * dT(t)/dt = P_slonce(t) + P_grzalka(t) - P_obudowa(t) - P_wentylacja(t) - P_drzwi(t)

    P_slonce     = tau * A_podlogi * E(t)
    P_obudowa    = k_w(t) * U * A_obudowy * (T(t) - T_zew(t))     k_w - mnożnik od wiatru (1 = brak wiatru)
    P_wentylacja = rho * c_p * Q_went(t) * (T(t) - T_zew(t))
    P_drzwi      = rho * c_p * Q_drzwi(t) * (T(t) - T_zew(t))     Q_drzwi - wymiana powietrza przez otwarte drzwi

Równanie różnicowe (krok Tp) i rekurencja:

    T(n+1) = T(n) + Tp/C * [P_slonce(n) + P_grzalka(n) - P_obudowa(n) - P_wentylacja(n) - P_drzwi(n)]

Urządzenie pomiarowe (czujnik z inercją I rzędu):

    T_cz * dT_m(t)/dt = T(t) - T_m(t)   ->   T_m(n+1) = T_m(n) + Tp/T_cz * (T(n) - T_m(n))

Regulator PI:

    e(n) = T_zad(n) - T_m(n)
    u(n) = Kp * (e(n) + Tp/Ti * suma e(k) dla k = 0..n)

    u ograniczone do [-10, 10]:  u > 0 -> grzałka,  u < 0 -> wentylator
"""

from dataclasses import dataclass, field
import math


# ---------------------------------------------------------------------------
# Stałe fizyczne
# ---------------------------------------------------------------------------
GESTOSC_POWIETRZA = 1.2               # rho [kg/m^3]
CIEPLO_WLASCIWE_POWIETRZA = 1005.0    # c_p [J/(kg*K)]
SEKUND_W_GODZINIE = 3600.0

STALA_CZASOWA_CZUJNIKA = 90.0        # T_cz [s] - czujnik w osłonie nie pokazuje temperatury od razu

STEROWANIE_MINIMALNE = -10.0          # u_min [-]
STEROWANIE_MAKSYMALNE = 10.0          # u_max [-]


# ---------------------------------------------------------------------------
# Obiekt regulacji: trzy szklarnie do wyboru z listy rozwijanej
# ---------------------------------------------------------------------------
@dataclass
class Szklarnia:
    nazwa: str
    dlugosc: float                            # [m]
    szerokosc: float                          # [m]
    wysokosc: float                           # [m]
    wspolczynnik_przenikania_ciepla: float    # U [W/(m^2*K)]
    przepuszczalnosc_promieniowania: float    # tau [-]
    pojemnosc_cieplna_na_metr_kwadratowy: float  # rośliny, gleba, konstrukcja [J/(K*m^2)]
    maksymalna_moc_grzalki: float             # [W]
    maksymalny_przeplyw_wentylatora: float    # [m^3/s]
    dobrane_wzmocnienie: float                # Kp z doboru nastaw [1/°C]
    dobrany_czas_zdwojenia: float             # Ti z doboru nastaw [s]

    @property
    def powierzchnia_podlogi(self):
        return self.dlugosc * self.szerokosc

    @property
    def powierzchnia_obudowy(self):
        """Dach + cztery ściany (dach uproszczony do płaskiego)."""
        return self.powierzchnia_podlogi + 2 * (self.dlugosc + self.szerokosc) * self.wysokosc

    @property
    def objetosc_powietrza(self):
        return self.powierzchnia_podlogi * self.wysokosc

    @property
    def pojemnosc_cieplna(self):
        """C [J/K] = powietrze + wnętrze."""
        pojemnosc_powietrza = self.objetosc_powietrza * GESTOSC_POWIETRZA * CIEPLO_WLASCIWE_POWIETRZA
        return pojemnosc_powietrza + self.pojemnosc_cieplna_na_metr_kwadratowy * self.powierzchnia_podlogi


SZKLARNIE = {
    "mala": Szklarnia(
        nazwa="mała szklarnia przydomowa (szkło, 3 × 4 m)",
        dlugosc=4.0, szerokosc=3.0, wysokosc=2.2,
        wspolczynnik_przenikania_ciepla=6.0, przepuszczalnosc_promieniowania=0.75,
        pojemnosc_cieplna_na_metr_kwadratowy=15_000.0,
        maksymalna_moc_grzalki=6_000.0, maksymalny_przeplyw_wentylatora=1.2,
        dobrane_wzmocnienie=5.0, dobrany_czas_zdwojenia=300.0,
    ),
    "ogrodnicza": Szklarnia(
        nazwa="szklarnia ogrodnicza (szkło, 10 × 10 m)",
        dlugosc=10.0, szerokosc=10.0, wysokosc=3.0,
        wspolczynnik_przenikania_ciepla=6.0, przepuszczalnosc_promieniowania=0.7,
        pojemnosc_cieplna_na_metr_kwadratowy=15_000.0,
        maksymalna_moc_grzalki=30_000.0, maksymalny_przeplyw_wentylatora=6.0,
        dobrane_wzmocnienie=8.0, dobrany_czas_zdwojenia=300.0,
    ),
    "tunel": Szklarnia(
        nazwa="tunel foliowy (folia podwójna, 8 × 30 m)",
        dlugosc=30.0, szerokosc=8.0, wysokosc=3.5,
        wspolczynnik_przenikania_ciepla=4.0, przepuszczalnosc_promieniowania=0.8,
        pojemnosc_cieplna_na_metr_kwadratowy=15_000.0,
        maksymalna_moc_grzalki=60_000.0, maksymalny_przeplyw_wentylatora=25.0,
        dobrane_wzmocnienie=5.0, dobrany_czas_zdwojenia=300.0,
    ),
}


# ---------------------------------------------------------------------------
# Warunki pogodowe (zakłócenia) - druga lista rozwijana
# ---------------------------------------------------------------------------
@dataclass
class WarunkiPogodowe:
    nazwa: str
    opis: str
    naslonecznienie: callable          # E(t) [W/m^2], t w sekundach
    temperatura_zewnetrzna: callable   # T_zew(t) [°C]
    mnoznik_wiatru: callable = field(default=lambda czas: 1.0)     # k_w(t) [-]
    przeplyw_przez_drzwi: callable = field(default=lambda czas: 0.0)  # Q_drzwi(t) [m^3/s]


def _profil_dzienny(czas, godzina_startu, minimum, maksimum, godzina_maksimum, polowa_okresu_godziny):
    """Gładka 'górka' (półokres cosinusa) - przebieg słońca i temperatury w ciągu dnia."""
    godzina = godzina_startu + czas / SEKUND_W_GODZINIE
    przesuniecie = (godzina - godzina_maksimum) / polowa_okresu_godziny
    if abs(przesuniecie) >= 1.0:
        return minimum
    return minimum + (maksimum - minimum) * math.cos(przesuniecie * math.pi / 2)


def warunki_sloneczny_dzien():
    return WarunkiPogodowe(
        nazwa="słoneczny dzień (6:00–18:00)",
        opis="rano chłodno i ciemno, w południe do 850 W/m² i 19 °C na zewnątrz",
        naslonecznienie=lambda czas: _profil_dzienny(czas, 6.0, 0.0, 850.0, 13.0, 7.0),
        temperatura_zewnetrzna=lambda czas: _profil_dzienny(czas, 6.0, 8.0, 19.0, 15.0, 10.0),
    )


def warunki_zachmurzenie():
    def naslonecznienie(czas):
        if 1.5 * SEKUND_W_GODZINIE <= czas < 3.5 * SEKUND_W_GODZINIE:
            return 80.0
        return 750.0

    return WarunkiPogodowe(
        nazwa="nagłe zachmurzenie",
        opis="750 W/m², od 1,5 h do 3,5 h chmury (80 W/m²), na zewnątrz stale 15 °C",
        naslonecznienie=naslonecznienie,
        temperatura_zewnetrzna=lambda czas: 15.0,
    )


def warunki_drzwi_i_wiatr():
    """Pochmurny chłodny dzień i dwa zakłócenia, których nie ma w pogodzie 'z definicji':
    - 1:00-1:10 otwarte drzwi (wymiana powietrza 1,5 m^3/s),
    - 2:00-3:30 silny wiatr: straty przez obudowę rosną o 80 % (k_w = 1,8)."""
    def przeplyw_przez_drzwi(czas):
        return 1.5 if 1.0 * SEKUND_W_GODZINIE <= czas < (1.0 + 10 / 60) * SEKUND_W_GODZINIE else 0.0

    def mnoznik_wiatru(czas):
        return 1.8 if 2.0 * SEKUND_W_GODZINIE <= czas < 3.5 * SEKUND_W_GODZINIE else 1.0

    return WarunkiPogodowe(
        nazwa="otwarte drzwi i silny wiatr",
        opis="pochmurno (150 W/m²), 8 °C na zewnątrz; drzwi otwarte 1:00–1:10, silny wiatr 2:00–3:30",
        naslonecznienie=lambda czas: 150.0,
        temperatura_zewnetrzna=lambda czas: 8.0,
        mnoznik_wiatru=mnoznik_wiatru,
        przeplyw_przez_drzwi=przeplyw_przez_drzwi,
    )


def warunki_stale(naslonecznienie_stale, temperatura_zewnetrzna_stala):
    return WarunkiPogodowe(
        nazwa="stałe warunki",
        opis="stałe nasłonecznienie i temperatura zewnętrzna z suwaków",
        naslonecznienie=lambda czas: naslonecznienie_stale,
        temperatura_zewnetrzna=lambda czas: temperatura_zewnetrzna_stala,
    )


# ---------------------------------------------------------------------------
# Regulator PI
# ---------------------------------------------------------------------------
class RegulatorPI:
    """u(n) = Kp * (e(n) + Tp/Ti * suma e(k)), ograniczone do [u_min, u_max].
    Gdy u jest w nasyceniu, suma uchybów nie rośnie dalej (anti-windup) -
    inaczej regulator 'pamiętałby' za dużo i mocno przeregulowywał."""

    def __init__(self, wzmocnienie, czas_zdwojenia, okres_probkowania):
        self.wzmocnienie = wzmocnienie
        self.czas_zdwojenia = czas_zdwojenia
        self.okres_probkowania = okres_probkowania
        self.suma_uchybow = 0.0

    def oblicz_sterowanie(self, uchyb):
        suma_z_biezacym = self.suma_uchybow + uchyb
        sterowanie = self.wzmocnienie * (uchyb + self.okres_probkowania / self.czas_zdwojenia * suma_z_biezacym)
        sterowanie_ograniczone = min(max(sterowanie, STEROWANIE_MINIMALNE), STEROWANIE_MAKSYMALNE)
        if sterowanie == sterowanie_ograniczone:
            self.suma_uchybow = suma_z_biezacym
        return sterowanie_ograniczone


def zamien_sterowanie_na_urzadzenia(sterowanie, szklarnia):
    """u > 0 -> grzałka, u < 0 -> wentylator (liniowo, prosta przez 2 punkty jak Qd(alfa) w zbiorniku)."""
    if sterowanie >= 0:
        moc_grzalki = szklarnia.maksymalna_moc_grzalki * sterowanie / STEROWANIE_MAKSYMALNE
        return moc_grzalki, 0.0
    przeplyw_wentylatora = szklarnia.maksymalny_przeplyw_wentylatora * sterowanie / STEROWANIE_MINIMALNE
    return 0.0, przeplyw_wentylatora


# ---------------------------------------------------------------------------
# Symulacja
# ---------------------------------------------------------------------------
def skladniki_bilansu(temperatura_wewnetrzna, temperatura_zewnetrzna, naslonecznienie,
                      moc_grzalki, przeplyw_wentylatora, mnoznik_wiatru, przeplyw_przez_drzwi, szklarnia):
    """Zwraca moce [W]: (słońce, grzałka, straty przez obudowę, straty przez wentylację, straty przez drzwi)."""
    roznica_temperatur = temperatura_wewnetrzna - temperatura_zewnetrzna
    moc_slonca = szklarnia.przepuszczalnosc_promieniowania * szklarnia.powierzchnia_podlogi * naslonecznienie
    straty_obudowa = (mnoznik_wiatru * szklarnia.wspolczynnik_przenikania_ciepla
                      * szklarnia.powierzchnia_obudowy * roznica_temperatur)
    straty_wentylacja = GESTOSC_POWIETRZA * CIEPLO_WLASCIWE_POWIETRZA * przeplyw_wentylatora * roznica_temperatur
    straty_drzwi = GESTOSC_POWIETRZA * CIEPLO_WLASCIWE_POWIETRZA * przeplyw_przez_drzwi * roznica_temperatur
    return moc_slonca, moc_grzalki, straty_obudowa, straty_wentylacja, straty_drzwi


def symuluj(szklarnia, warunki, temperatura_zadana, temperatura_poczatkowa,
            wzmocnienie, czas_zdwojenia, okres_probkowania, czas_symulacji_godziny,
            regulacja_wlaczona=True):
    liczba_krokow = int(czas_symulacji_godziny * SEKUND_W_GODZINIE / okres_probkowania)
    regulator = RegulatorPI(wzmocnienie, czas_zdwojenia, okres_probkowania)
    pojemnosc_cieplna = szklarnia.pojemnosc_cieplna

    wyniki = {klucz: [] for klucz in (
        "czas_godziny", "temperatura_wewnetrzna", "temperatura_bez_regulacji", "temperatura_zadana",
        "temperatura_zewnetrzna", "temperatura_zmierzona", "naslonecznienie", "uchyb", "sterowanie",
        "moc_slonca_kW", "moc_grzalki_kW", "straty_obudowa_kW", "straty_wentylacja_kW", "straty_drzwi_kW",
        "przeplyw_wentylatora")}

    temperatura_wewnetrzna = temperatura_poczatkowa
    temperatura_bez_regulacji = temperatura_poczatkowa
    temperatura_zmierzona = temperatura_poczatkowa

    for numer_kroku in range(liczba_krokow + 1):
        czas = numer_kroku * okres_probkowania
        naslonecznienie = warunki.naslonecznienie(czas)
        temperatura_zewnetrzna = warunki.temperatura_zewnetrzna(czas)
        mnoznik_wiatru = warunki.mnoznik_wiatru(czas)
        przeplyw_przez_drzwi = warunki.przeplyw_przez_drzwi(czas)

        uchyb = temperatura_zadana - temperatura_zmierzona
        sterowanie = regulator.oblicz_sterowanie(uchyb) if regulacja_wlaczona else 0.0
        moc_grzalki, przeplyw_wentylatora = zamien_sterowanie_na_urzadzenia(sterowanie, szklarnia)

        moc_slonca, moc_grzalki, straty_obudowa, straty_wentylacja, straty_drzwi = skladniki_bilansu(
            temperatura_wewnetrzna, temperatura_zewnetrzna, naslonecznienie,
            moc_grzalki, przeplyw_wentylatora, mnoznik_wiatru, przeplyw_przez_drzwi, szklarnia)

        wyniki["czas_godziny"].append(czas / SEKUND_W_GODZINIE)
        wyniki["temperatura_wewnetrzna"].append(temperatura_wewnetrzna)
        wyniki["temperatura_bez_regulacji"].append(temperatura_bez_regulacji)
        wyniki["temperatura_zadana"].append(temperatura_zadana)
        wyniki["temperatura_zewnetrzna"].append(temperatura_zewnetrzna)
        wyniki["temperatura_zmierzona"].append(temperatura_zmierzona)
        wyniki["naslonecznienie"].append(naslonecznienie)
        wyniki["uchyb"].append(uchyb)
        wyniki["sterowanie"].append(sterowanie)
        wyniki["moc_slonca_kW"].append(moc_slonca / 1000.0)
        wyniki["moc_grzalki_kW"].append(moc_grzalki / 1000.0)
        wyniki["straty_obudowa_kW"].append(straty_obudowa / 1000.0)
        wyniki["straty_wentylacja_kW"].append(straty_wentylacja / 1000.0)
        wyniki["straty_drzwi_kW"].append(straty_drzwi / 1000.0)
        wyniki["przeplyw_wentylatora"].append(przeplyw_wentylatora)

        # czujnik: T_m(n+1) = T_m(n) + Tp/T_cz * (T(n) - T_m(n))
        temperatura_zmierzona += okres_probkowania / STALA_CZASOWA_CZUJNIKA * (temperatura_wewnetrzna - temperatura_zmierzona)

        # rekurencja: T(n+1) = T(n) + Tp/C * [bilans mocy]
        bilans_mocy = moc_slonca + moc_grzalki - straty_obudowa - straty_wentylacja - straty_drzwi
        temperatura_wewnetrzna += okres_probkowania / pojemnosc_cieplna * bilans_mocy

        # ten sam obiekt bez regulacji (grzałka i wentylator wyłączone) - do porównania
        slonce, _, obudowa, _, drzwi = skladniki_bilansu(
            temperatura_bez_regulacji, temperatura_zewnetrzna, naslonecznienie,
            0.0, 0.0, mnoznik_wiatru, przeplyw_przez_drzwi, szklarnia)
        temperatura_bez_regulacji += okres_probkowania / pojemnosc_cieplna * (slonce - obudowa - drzwi)

    wyniki["wskazniki_jakosci"] = oblicz_wskazniki_jakosci(wyniki, okres_probkowania)
    return wyniki


def oblicz_wskazniki_jakosci(wyniki, okres_probkowania):
    uchyby = [zadana - rzeczywista for zadana, rzeczywista
              in zip(wyniki["temperatura_zadana"], wyniki["temperatura_wewnetrzna"])]
    czasy = wyniki["czas_godziny"]
    temperatura_zadana = wyniki["temperatura_zadana"][0]
    temperatura_poczatkowa = wyniki["temperatura_wewnetrzna"][0]
    wielkosc_skoku = temperatura_zadana - temperatura_poczatkowa

    # przeregulowanie: o ile temperatura przekroczyła zadaną po stronie, w którą szła
    if wielkosc_skoku >= 0:
        przeregulowanie = max(0.0, max(wyniki["temperatura_wewnetrzna"]) - temperatura_zadana)
    else:
        przeregulowanie = max(0.0, temperatura_zadana - min(wyniki["temperatura_wewnetrzna"]))

    # czas regulacji: ostatnia chwila, w której |e| > 0.5 °C
    tolerancja = 0.5
    poza_pasmem = [czas for czas, uchyb in zip(czasy, uchyby) if abs(uchyb) > tolerancja]
    czas_regulacji_minuty = (poza_pasmem[-1] * 60.0) if poza_pasmem else 0.0

    ostatnie_probki = max(1, len(uchyby) // 20)
    return {
        "przeregulowanie": przeregulowanie,
        "czas_regulacji_minuty": czas_regulacji_minuty,
        "uchyb_koncowy": sum(uchyby[-ostatnie_probki:]) / ostatnie_probki,
        "calka_modulu_uchybu": sum(abs(uchyb) for uchyb in uchyby) * okres_probkowania / SEKUND_W_GODZINIE,
        "energia_grzania_kWh": sum(wyniki["moc_grzalki_kW"]) * okres_probkowania / SEKUND_W_GODZINIE,
        "maksymalna_temperatura_bez_regulacji": max(wyniki["temperatura_bez_regulacji"]),
    }

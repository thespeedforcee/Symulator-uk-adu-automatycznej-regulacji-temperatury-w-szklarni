"""
Wykresy PNG do sprawozdania (matplotlib, bez Dasha).
Uruchomienie: python wykresy_do_sprawozdania.py  -> pliki w katalogu wykresy/
"""

from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from model_szklarni import (
    SZKLARNIE, STEROWANIE_MINIMALNE, STEROWANIE_MAKSYMALNE,
    warunki_sloneczny_dzien, warunki_zachmurzenie, warunki_drzwi_i_wiatr, warunki_stale, symuluj,
)

KATALOG_WYKRESOW = Path(__file__).parent / "wykresy"


def wyglad_osi(os_wykresu, tytul, opis_y):
    os_wykresu.set_title(tytul, loc="left", fontsize=11)
    os_wykresu.set_ylabel(opis_y)
    os_wykresu.grid(color="#e6e5e1")
    for krawedz in ("top", "right"):
        os_wykresu.spines[krawedz].set_visible(False)
    os_wykresu.legend(fontsize=8.5, loc="upper left", bbox_to_anchor=(1.01, 1.0), frameon=False)


def narysuj_sytuacje(klucz_szklarni, warunki, temperatura_zadana, temperatura_poczatkowa,
                     czas_symulacji_godziny, tytul, nazwa_pliku):
    szklarnia = SZKLARNIE[klucz_szklarni]
    wyniki = symuluj(szklarnia, warunki, temperatura_zadana, temperatura_poczatkowa,
                     szklarnia.dobrane_wzmocnienie, szklarnia.dobrany_czas_zdwojenia,
                     okres_probkowania=10.0, czas_symulacji_godziny=czas_symulacji_godziny)
    czas = wyniki["czas_godziny"]

    figura, (os_a, os_b, os_c) = plt.subplots(3, 1, figsize=(12, 10), sharex=True)

    os_a.plot(czas, wyniki["temperatura_zadana"], "--", color="#52514e", lw=2, label="temperatura zadana")
    os_a.plot(czas, wyniki["temperatura_wewnetrzna"], color="#2a78d6", lw=2, label="temperatura w szklarni")
    os_a.plot(czas, wyniki["temperatura_bez_regulacji"], ":", color="#eb6834", lw=2, label="bez regulacji")
    os_a.plot(czas, wyniki["temperatura_zewnetrzna"], color="#1baf7a", lw=2, label="temperatura zewnętrzna")
    wyglad_osi(os_a, "a) temperatura w szklarni dąży do temperatury zadanej", "temperatura [°C]")

    os_b.plot(czas, wyniki["moc_slonca_kW"], color="#eda100", lw=2, label="dopływ: słońce")
    os_b.plot(czas, wyniki["moc_grzalki_kW"], color="#e34948", lw=2, label="dopływ: grzałka")
    os_b.plot(czas, [-m for m in wyniki["straty_obudowa_kW"]], color="#008300", lw=2, label="odpływ: przez szkło")
    os_b.plot(czas, [-m for m in wyniki["straty_wentylacja_kW"]], color="#6250d6", lw=2, label="odpływ: wentylacja")
    if any(wyniki["straty_drzwi_kW"]):
        os_b.plot(czas, [-m for m in wyniki["straty_drzwi_kW"]], color="#e87ba4", lw=2, label="odpływ: otwarte drzwi")
    os_b.axhline(0, color="#9a9994", lw=1)
    wyglad_osi(os_b, "b) bilans energii: dopływy ciepła (+) i odpływy (−)", "moc [kW]")

    os_c.plot(czas, wyniki["sterowanie"], color="#2a78d6", lw=2, label="sygnał sterujący u(n)")
    os_c.axhline(0, color="#9a9994", lw=1)
    os_c.set_ylim(STEROWANIE_MINIMALNE - 0.5, STEROWANIE_MAKSYMALNE + 0.5)
    os_c.text(0.005, 0.97, "u > 0: grzałka", transform=os_c.transAxes, va="top", color="#e34948", fontsize=9)
    os_c.text(0.005, 0.03, "u < 0: wentylator", transform=os_c.transAxes, va="bottom", color="#6250d6", fontsize=9)
    wyglad_osi(os_c, "c) sygnał sterujący regulatora PI", "u [–]")
    os_c.set_xlabel("czas [h]")

    figura.suptitle(f"{tytul} – {szklarnia.nazwa}", fontsize=13, fontweight="bold")
    figura.tight_layout()
    figura.savefig(KATALOG_WYKRESOW / nazwa_pliku, dpi=150)
    plt.close(figura)
    return wyniki["wskazniki_jakosci"]


def narysuj_wplyw_nastaw(klucz_szklarni, nazwa_pliku):
    """Odpowiedź na skok wartości zadanej (noc, 15 -> 22 °C) dla różnych Kp i Ti."""
    szklarnia = SZKLARNIE[klucz_szklarni]
    warunki = warunki_stale(0.0, 5.0)
    figura, (os_kp, os_ti) = plt.subplots(1, 2, figsize=(14, 4.5), sharey=True)
    kolory = ["#86b6ef", "#2a78d6", "#104281"]

    for kolor, wzmocnienie in zip(kolory, [1.0, szklarnia.dobrane_wzmocnienie, 20.0]):
        wyniki = symuluj(szklarnia, warunki, 22.0, 15.0, wzmocnienie, szklarnia.dobrany_czas_zdwojenia, 10.0, 1.5)
        os_kp.plot(wyniki["czas_godziny"], wyniki["temperatura_wewnetrzna"], color=kolor, lw=2,
                   label=f"Kp = {wzmocnienie:g}")
    for kolor, czas_zdwojenia in zip(kolory, [60, szklarnia.dobrany_czas_zdwojenia, 1800]):
        wyniki = symuluj(szklarnia, warunki, 22.0, 15.0, szklarnia.dobrane_wzmocnienie, czas_zdwojenia, 10.0, 1.5)
        os_ti.plot(wyniki["czas_godziny"], wyniki["temperatura_wewnetrzna"], color=kolor, lw=2,
                   label=f"Ti = {czas_zdwojenia:g} s")

    for os_wykresu, tytul in ((os_kp, f"wpływ Kp (Ti = {szklarnia.dobrany_czas_zdwojenia:g} s)"),
                              (os_ti, f"wpływ Ti (Kp = {szklarnia.dobrane_wzmocnienie:g})")):
        os_wykresu.axhline(22.0, color="#52514e", ls="--", lw=1.5, label="temperatura zadana")
        os_wykresu.set_xlabel("czas [h]")
        wyglad_osi(os_wykresu, tytul, "temperatura [°C]")
    figura.suptitle(f"dobór nastaw – odpowiedź na skok 15 → 22 °C, {szklarnia.nazwa}", fontsize=12, fontweight="bold")
    figura.tight_layout()
    figura.savefig(KATALOG_WYKRESOW / nazwa_pliku, dpi=150)
    plt.close(figura)


if __name__ == "__main__":
    KATALOG_WYKRESOW.mkdir(exist_ok=True)
    for stary_plik in KATALOG_WYKRESOW.glob("*.png"):
        stary_plik.unlink()

    sytuacje = [
        ("ogrodnicza", warunki_sloneczny_dzien(), 24.0, 12.0, 12.0, "sytuacja 1: słoneczny dzień",
         "sytuacja_1_sloneczny_dzien.png"),
        ("ogrodnicza", warunki_zachmurzenie(), 23.0, 23.0, 5.0, "sytuacja 2: nagłe zachmurzenie",
         "sytuacja_2_zachmurzenie.png"),
        ("tunel", warunki_stale(0.0, -5.0), 18.0, 5.0, 4.0, "sytuacja 3: mroźna noc",
         "sytuacja_3_mrozna_noc.png"),
        ("ogrodnicza", warunki_drzwi_i_wiatr(), 22.0, 22.0, 5.0, "sytuacja 4: otwarte drzwi i silny wiatr",
         "sytuacja_4_drzwi_i_wiatr.png"),
    ]
    for argumenty in sytuacje:
        wskazniki = narysuj_sytuacje(*argumenty)
        print(argumenty[-1], {klucz: round(wartosc, 2) for klucz, wartosc in wskazniki.items()})

    narysuj_wplyw_nastaw("ogrodnicza", "dobor_nastaw_szklarnia_ogrodnicza.png")
    print("dobor_nastaw_szklarnia_ogrodnicza.png")

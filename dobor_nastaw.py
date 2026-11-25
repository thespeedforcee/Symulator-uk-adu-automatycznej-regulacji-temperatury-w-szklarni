"""
Dobór nastaw regulatora PI (Kp, Ti) dla każdej z trzech szklarni.

Metoda: przegląd siatki nastaw i ocena każdej pary na dwóch próbach:
  próba 1 - nagrzewanie w nocy: T0 = 15 °C -> T_zad = 22 °C, brak słońca, na zewnątrz 5 °C
            (odpowiedź na skok wartości zadanej, pracuje grzałka),
  próba 2 - nagłe zachmurzenie przy T_zad = 23 °C
            (tłumienie zakłócenia, przełączanie wentylator -> grzałka -> wentylator).

Kryterium:
  1. odrzucamy nastawy z przeregulowaniem w próbie 1 większym niż 0,5 °C,
  2. szukamy najmniejszej sumy całek z modułu uchybu (IAE) z obu prób,
  3. spośród nastaw nie więcej niż 10 % gorszych od najlepszej wybieramy te
     z najmniejszym Kp (a potem największym Ti) - są łagodniejsze, regulator mniej
     "szarpie" grzałką i wentylatorem i jest odporniejszy na błędy modelu.

Uruchomienie: python dobor_nastaw.py
"""

from model_szklarni import SZKLARNIE, warunki_stale, warunki_zachmurzenie, symuluj

WZMOCNIENIA = [0.5, 1.0, 2.0, 3.0, 5.0, 8.0, 12.0, 20.0]          # Kp [1/°C]
CZASY_ZDWOJENIA = [60, 120, 300, 600, 900, 1200, 1800]     # Ti [s]
OKRES_PROBKOWANIA = 10.0
DOPUSZCZALNE_PRZEREGULOWANIE = 0.5
ZAPAS_WZGLEDEM_NAJLEPSZYCH = 1.10


def ocen_nastawy(szklarnia, wzmocnienie, czas_zdwojenia):
    proba_nagrzewania = symuluj(
        szklarnia, warunki_stale(0.0, 5.0), temperatura_zadana=22.0, temperatura_poczatkowa=15.0,
        wzmocnienie=wzmocnienie, czas_zdwojenia=czas_zdwojenia,
        okres_probkowania=OKRES_PROBKOWANIA, czas_symulacji_godziny=4.0)["wskazniki_jakosci"]
    proba_zachmurzenia = symuluj(
        szklarnia, warunki_zachmurzenie(), temperatura_zadana=23.0, temperatura_poczatkowa=23.0,
        wzmocnienie=wzmocnienie, czas_zdwojenia=czas_zdwojenia,
        okres_probkowania=OKRES_PROBKOWANIA, czas_symulacji_godziny=5.0)["wskazniki_jakosci"]
    return {
        "wzmocnienie": wzmocnienie,
        "czas_zdwojenia": czas_zdwojenia,
        "przeregulowanie": proba_nagrzewania["przeregulowanie"],
        "czas_regulacji_minuty": proba_nagrzewania["czas_regulacji_minuty"],
        "calka_uchybu_nagrzewanie": proba_nagrzewania["calka_modulu_uchybu"],
        "calka_uchybu_zachmurzenie": proba_zachmurzenia["calka_modulu_uchybu"],
        "calka_uchybu_suma": proba_nagrzewania["calka_modulu_uchybu"] + proba_zachmurzenia["calka_modulu_uchybu"],
    }


def dobierz_nastawy(szklarnia):
    wszystkie_wyniki = [ocen_nastawy(szklarnia, kp, ti) for kp in WZMOCNIENIA for ti in CZASY_ZDWOJENIA]
    dopuszczalne = [w for w in wszystkie_wyniki if w["przeregulowanie"] <= DOPUSZCZALNE_PRZEREGULOWANIE]
    najmniejsza_calka = min(w["calka_uchybu_suma"] for w in dopuszczalne)
    prawie_najlepsze = [w for w in dopuszczalne
                        if w["calka_uchybu_suma"] <= ZAPAS_WZGLEDEM_NAJLEPSZYCH * najmniejsza_calka]
    wybrane = min(prawie_najlepsze, key=lambda w: (w["wzmocnienie"], -w["czas_zdwojenia"]))
    return wybrane, wszystkie_wyniki


def wypisz_tabele(nazwa, wszystkie_wyniki, najlepsze):
    print(f"\n=== {nazwa} ===")
    print("całka |e| z obu prób [°C·h]  (* = przeregulowanie > 0,5 °C, [ ] = wybrane)")
    print("Kp \\ Ti " + "".join(f"{ti:>9}" for ti in CZASY_ZDWOJENIA))
    for kp in WZMOCNIENIA:
        wiersz = f"{kp:>7} "
        for ti in CZASY_ZDWOJENIA:
            wynik = next(w for w in wszystkie_wyniki if w["wzmocnienie"] == kp and w["czas_zdwojenia"] == ti)
            znacznik = "*" if wynik["przeregulowanie"] > DOPUSZCZALNE_PRZEREGULOWANIE else " "
            if wynik is najlepsze:
                wiersz += f"  [{wynik['calka_uchybu_suma']:.2f}]"
            else:
                wiersz += f"{wynik['calka_uchybu_suma']:>8.2f}{znacznik}"
        print(wiersz)
    print(f"wybrane: Kp = {najlepsze['wzmocnienie']}, Ti = {najlepsze['czas_zdwojenia']} s | "
          f"przeregulowanie {najlepsze['przeregulowanie']:.2f} °C, "
          f"czas regulacji {najlepsze['czas_regulacji_minuty']:.0f} min, "
          f"IAE nagrzewanie {najlepsze['calka_uchybu_nagrzewanie']:.2f}, "
          f"IAE zachmurzenie {najlepsze['calka_uchybu_zachmurzenie']:.2f} °C·h")


if __name__ == "__main__":
    for klucz, szklarnia in SZKLARNIE.items():
        najlepsze, wszystkie_wyniki = dobierz_nastawy(szklarnia)
        wypisz_tabele(szklarnia.nazwa, wszystkie_wyniki, najlepsze)

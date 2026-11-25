# Symulator regulacji temperatury w szklarni

Projekt z Podstaw Automatyki (Politechnika Poznańska). Symulator układu automatycznej
regulacji temperatury w szklarni z interfejsem w **Plotly Dash**.

## Uruchomienie

```bash
pip install -r requirements.txt
python app.py                      # potem http://127.0.0.1:8050
python dobor_nastaw.py             # tabele doboru nastaw Kp, Ti
python wykresy_do_sprawozdania.py  # wykresy PNG do katalogu wykresy/
```

## Pliki

| Plik | Zawartość |
|---|---|
| `model_szklarni.py` | model, czujnik, regulator PI, 3 szklarnie, warunki pogodowe, symulacja |
| `app.py` | interfejs: listy rozwijane, suwaki, przycisk „wykonaj obliczenia”, wykresy a/b/c |
| `dobor_nastaw.py` | dobór nastaw Kp i Ti dla każdej szklarni |
| `wykresy_do_sprawozdania.py` | wykresy PNG do sprawozdania |

## Model

Wielkość regulowana: temperatura w szklarni T(t). Wielkość sterująca: sygnał u(n) z regulatora
(u > 0 → moc grzałki, u < 0 → przepływ wentylatora). Zakłócenia: nasłonecznienie E(t),
temperatura zewnętrzna T_zew(t), wiatr k_w(t) (mnożnik strat przez obudowę) i otwarte drzwi
Q_drzwi(t) (dodatkowa wymiana powietrza).

Równanie różniczkowe (bilans energii):

```
C·dT/dt = τ·A_p·E + P_grz − k_w·U·A_ob·(T − T_zew) − ρ·c_p·(Q_went + Q_drzwi)·(T − T_zew)
```

Równanie różnicowe → rekurencja:

```
T(n+1) = T(n) + Tp/C · [τ·A_p·E(n) + P_grz(n) − (k_w(n)·U·A_ob + ρ·c_p·(Q_went(n) + Q_drzwi(n)))·(T(n) − T_zew(n))]
```

Urządzenie pomiarowe (czujnik z inercją, T_cz = 90 s):

```
T_m(n+1) = T_m(n) + Tp/T_cz · (T(n) − T_m(n))
```

Regulator PI (u ograniczone do −10…10, całkowanie zatrzymane w nasyceniu):

```
e(n) = T_zad − T_m(n)
u(n) = Kp · (e(n) + Tp/Ti · Σ e(k))
P_grz = u/10 · P_max  (u > 0)        Q_went = |u|/10 · Q_max  (u < 0)
```

## Trzy szklarnie (lista rozwijana)

| Szklarnia | Podłoga | U [W/(m²·K)] | τ | Grzałka | Wentylator | Kp | Ti |
|---|---|---|---|---|---|---|---|
| mała przydomowa (szkło) | 3 × 4 m, h = 2,2 m | 6 | 0,75 | 6 kW | 1,2 m³/s | 5 | 300 s |
| ogrodnicza (szkło) | 10 × 10 m, h = 3 m | 6 | 0,7 | 30 kW | 6 m³/s | 8 | 300 s |
| tunel foliowy (folia podwójna) | 8 × 30 m, h = 3,5 m | 4 | 0,8 | 60 kW | 25 m³/s | 5 | 300 s |

## Dobór nastaw

Przegląd siatki Kp × Ti na dwóch próbach: skok wartości zadanej 15 → 22 °C w nocy
oraz nagłe zachmurzenie. Odrzucamy nastawy z przeregulowaniem > 0,5 °C, liczymy sumę całek
z modułu uchybu (IAE), a spośród nastaw najwyżej 10 % gorszych od najlepszej wybieramy
najłagodniejsze (najmniejsze Kp). Bez inercji czujnika najlepsze byłoby zawsze
„jak największe Kp” – dopiero opóźnienie pomiaru sprawia, że za duże Kp i za małe Ti
dają oscylacje (patrz `wykresy/dobor_nastaw_szklarnia_ogrodnicza.png`).

## Sytuacje w sprawozdaniu

1. Słoneczny dzień (szklarnia ogrodnicza): rano grzałka, w południe wentylacja w nasyceniu –
   temperatura przekracza zadaną o ok. 1,7 °C, bez regulacji byłoby 63 °C.
2. Nagłe zachmurzenie (szklarnia ogrodnicza): przełączenie wentylacja → grzałka → wentylacja,
   odchyłki do ok. 1,8 °C, powrót do pasma ±0,5 °C w ok. 5 min.
3. Mroźna noc (tunel foliowy, −5 °C): nagrzewanie z 5 do 18 °C w ok. 40 min, potem
   grzałka utrzymuje temperaturę.
4. Otwarte drzwi i silny wiatr (szklarnia ogrodnicza, pochmurno, 8 °C): przez 10 min otwartych drzwi
   grzałka pracuje na 100 % i nie nadąża – temperatura spada do 20,8 °C; po zamknięciu drzwi
   chwilowe przeregulowanie do 22,7 °C. Silny wiatr (straty przez szkło × 1,8) – grzałka rośnie
   z 8 do 23 kW, spadek temperatury tylko do 21,3 °C, powrót w ok. 4 min.

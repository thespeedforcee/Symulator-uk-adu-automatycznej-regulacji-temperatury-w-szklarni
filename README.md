# Symulator regulacji temperatury w szklarni

Projekt z przedmiotu **Podstawy Automatyki** (Politechnika Poznańska).  
**Autorzy:** Sara Rachmańczuk (167898), Maria Linkowska (167906)

Symulator układu automatycznej regulacji temperatury w szklarni z interfejsem webowym w **Plotly Dash**.

---

## Uruchomienie

### Windows (PowerShell)
```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe app.py                      # http://127.0.0.1:8050
.venv\Scripts\python.exe dobor_nastaw.py             # tabele doboru nastaw Kp, Ti
.venv\Scripts\python.exe wykresy_do_sprawozdania.py  # wykresy PNG do katalogu wykresy/
```

### macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
python dobor_nastaw.py
python wykresy_do_sprawozdania.py
```

---

## Struktura repozytorium

| Plik / Katalog | Zawartość |
|---|---|
| `app.py` | interfejs Plotly Dash: listy rozwijane, suwaki, przycisk „wykonaj obliczenia”, kafelki wskaźników jakości, wykresy a/b/c |
| `model_szklarni.py` | model matematyczny, czujnik z inercją I rzędu, regulator PI z anti-windup, 3 szklarnie, profile pogodowe, symulacja |
| `dobor_nastaw.py` | dobór nastaw $K_p$ i $T_i$ dla każdej szklarni |
| `wykresy_do_sprawozdania.py` | generator wykresów PNG do sprawozdania (`matplotlib`) |
| `assets/styl.css` | arkusz stylów dla aplikacji Dash |
| `wykresy/` | wygenerowane wykresy PNG do sprawozdania |
| `docs/` | szkic projektu i materiały robocze |
| `requirements.txt` | wymagane pakiety Pythona |

---

## Model matematyczny

Wielkość regulowana: temperatura w szklarni $T(t)$. Wielkość sterująca: sygnał $u(n) \in [-10, 10]$ z regulatora ($u > 0 \rightarrow$ moc grzałki, $u < 0 \rightarrow$ przepływ wentylatora). Zakłócenia: nasłonecznienie $E(t)$, temperatura zewnętrzna $T_{\text{zew}}(t)$, wiatr $k_w(t)$ (mnożnik strat przez obudowę) oraz otwarte drzwi $Q_{\text{drzwi}}(t)$ (dodatkowa wymiana powietrza).

Równanie różniczkowe (bilans energii):
```text
C·dT/dt = τ·A_p·E + P_grz − k_w·U·A_ob·(T − T_zew) − ρ·c_p·(Q_went + Q_drzwi)·(T − T_zew)
```

Równanie różnicowe $\rightarrow$ rekurencja:
```text
T(n+1) = T(n) + Tp/C · [τ·A_p·E(n) + P_grz(n) − (k_w(n)·U·A_ob + ρ·c_p·(Q_went(n) + Q_drzwi(n)))·(T(n) − T_zew(n))]
```

Urządzenie pomiarowe (czujnik z inercją I rzędu, $T_{\text{cz}} = 90\text{ s}$):
```text
T_m(n+1) = T_m(n) + Tp/T_cz · (T(n) − T_m(n))
```

Regulator PI ($u$ ograniczone do $-10\ldots 10$, całkowanie zatrzymane w nasyceniu):
```text
e(n) = T_zad − T_m(n)
u(n) = Kp · (e(n) + Tp/Ti · Σ e(k))
P_grz = u/10 · P_max  (u > 0)        Q_went = |u|/10 · Q_max  (u < 0)
```

---

## Trzy szklarnie (lista rozwijana)

| Szklarnia | Podłoga | $U$ [W/(m²·K)] | $\tau$ | Grzałka | Wentylator | $K_p$ | $T_i$ |
|---|---|---|---|---|---|---|---|
| mała przydomowa (szkło) | $3 \times 4\text{ m}$, $h = 2{,}2\text{ m}$ | 6 | 0,75 | 6 kW | 1,2 m³/s | 5 | 300 s |
| ogrodnicza (szkło) | $10 \times 10\text{ m}$, $h = 3\text{ m}$ | 6 | 0,7 | 30 kW | 6 m³/s | 8 | 300 s |
| tunel foliowy (folia podwójna) | $8 \times 30\text{ m}$, $h = 3{,}5\text{ m}$ | 4 | 0,8 | 60 kW | 25 m³/s | 5 | 300 s |

---

## Dobór nastaw

Przegląd siatki $K_p \times T_i$ na dwóch próbach: skok wartości zadanej $15 \to 22\,^\circ\text{C}$ w nocy oraz nagłe zachmurzenie. Odrzucamy nastawy z przeregulowaniem $> 0{,}5\,^\circ\text{C}$, liczymy sumę całek z modułu uchybu (IAE), a spośród nastaw najwyżej 10% gorszych od najlepszej wybieramy najłagodniejsze (najmniejsze $K_p$). Bez inercji czujnika najlepsze byłoby zawsze „jak największe $K_p$” – dopiero opóźnienie pomiaru sprawia, że za duże $K_p$ i za małe $T_i$ dają oscylacje (patrz `wykresy/dobor_nastaw_szklarnia_ogrodnicza.png`).

---

## Sytuacje w sprawozdaniu

1. **Słoneczny dzień** (szklarnia ogrodnicza): rano grzałka, w południe wentylacja w nasyceniu – temperatura przekracza zadaną o ok. $1{,}7\,^\circ\text{C}$, bez regulacji byłoby $63\,^\circ\text{C}$.
2. **Nagłe zachmurzenie** (szklarnia ogrodnicza): przełączenie wentylacja $\to$ grzałka $\to$ wentylacja, odchyłki do ok. $1{,}8\,^\circ\text{C}$, powrót do pasma $\pm 0{,}5\,^\circ\text{C}$ w ok. $5\text{ min}$.
3. **Mroźna noc** (tunel foliowy, $-5\,^\circ\text{C}$): nagrzewanie z $5$ do $18\,^\circ\text{C}$ w ok. $40\text{ min}$, potem grzałka utrzymuje temperaturę.
4. **Otwarte drzwi i silny wiatr** (szklarnia ogrodnicza, pochmurno, $8\,^\circ\text{C}$): przez $10\text{ min}$ otwartych drzwi grzałka pracuje na 100% i nie nadąża – temperatura spada do $20{,}8\,^\circ\text{C}$; po zamknięciu drzwi chwilowe przeregulowanie do $22{,}7\,^\circ\text{C}$. Silny wiatr (straty przez szkło $\times 1{,}8$) – grzałka rośnie z $8$ do $23\text{ kW}$, spadek temperatury tylko do $21{,}3\,^\circ\text{C}$, powrót w ok. $4\text{ min}$.

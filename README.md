# Symulator układu automatycznej regulacji temperatury w szklarni

Projekt z przedmiotu **Podstawy Automatyki** (Politechnika Poznańska).  
**Autorzy:** Sara Rachmańczuk (167898), Maria Linkowska (167906)

---

## Opis projektu

Aplikacja symuluje w czasie dyskretnym (metodą Eulera) zmiany temperatury wewnątrz szklarni sterowanej za pomocą **regulatora PI** z ograniczeniem sygnału sterującego $u(n) \in [-10, 10]$ i zabezpieczeniem *anti-windup*:
- **Grzanie ($u > 0$):** proporcjonalne sterowanie mocą grzałki $P_{\text{grz}}$.
- **Chłodzenie ($u < 0$):** proporcjonalne sterowanie przepływem wentylatora $Q_{\text{went}}$ wtłaczającego powietrze z zewnątrz.
- **Pomiar:** uwzględniono inercję I rzędu czujnika temperatury ($T_{\text{cz}} = 90\text{ s}$).
- **Zakłócenia:** nasłonecznienie $E(t)$, temperatura zewnętrzna $T_{\text{zew}}(t)$, wiatr $k_w(t)$ oraz otwarcie drzwi $Q_{\text{drzwi}}(t)$.

---

## Struktura repozytorium

- `app.py` – aplikacja webowa w **Plotly Dash** (suwaki, wybór szklarni i pogody, 3 wykresy: temperatura, bilans energii, sygnał sterujący).
- `greenhouse_model.py` – model matematyczny szklarni, profile pogodowe oraz pętla symulacyjna z regulatorem PI.
- `tune_pi.py` – skrypt doboru nastaw $(K_p, T_i)$ minimalizujący całkę z modułu uchybu (IAE) przy ograniczeniu przeregulowania do $\le 0{,}5\,^\circ\text{C}$.
- `requirements.txt` – wymagane pakiety Pythona (`numpy`, `plotly`, `dash`).
- `docs/` – szkic i dokumentacja projektu.

---

## Dobrane nastawy regulatora PI

| Szklarnia | Wymiary | $P_{\text{grz,max}}$ | $Q_{\text{went,max}}$ | $K_p$ [1/°C] | $T_i$ [s] |
| :--- | :--- | :---: | :---: | :---: | :---: |
| Mała przydomowa (szkło) | $3 \times 4\text{ m}$, wys. $2{,}2\text{ m}$ | $6\text{ kW}$ | $1{,}2\text{ m}^3/\text{s}$ | `3.0` | `240` |
| Ogrodnicza (szkło) | $10 \times 10\text{ m}$, wys. $3\text{ m}$ | $30\text{ kW}$ | $6{,}0\text{ m}^3/\text{s}$ | `8.0` | `240` |
| Tunel foliowy (folia podwójna) | $8 \times 30\text{ m}$, wys. $3{,}5\text{ m}$ | $60\text{ kW}$ | $25{,}0\text{ m}^3/\text{s}$ | `5.0` | `450` |

---

## Uruchomienie projektu

1. **Utwórz środowisko wirtualne i zainstaluj zależności:**
   ```powershell
   python -m venv .venv
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

2. **Uruchom aplikację Dash:**
   ```powershell
   .venv\Scripts\python.exe app.py
   ```
   Następnie otwórz w przeglądarce adres: `http://127.0.0.1:8050/`

3. *(Opcjonalnie)* **Ponowny dobór nastaw regulatora PI:**
   ```powershell
   .venv\Scripts\python.exe tune_pi.py
   ```

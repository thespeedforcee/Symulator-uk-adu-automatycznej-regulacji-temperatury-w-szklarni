"""Skrypt do doboru nastaw regulatora PI (Kp, Ti) dla trzech szklarni.

Kryteria zgodne ze szkicem projektu:
1. Próba nagrzewania (skok 15 -> 22 °C) oraz próba nagłego zachmurzenia.
2. Odrzucenie nastaw z przeregulowaniem powyżej 0,5 °C.
3. Wybór pary (Kp, Ti) z najmniejszą całką z modułu uchybu (IAE).
"""

import numpy as np
from greenhouse_model import GREENHOUSES, simulate_greenhouse


def evaluate_pair(gh_key: str, kp: float, ti: float, tp: float = 10.0) -> dict | None:
    # Próba 1: nagrzewanie 15 -> 22 °C (stałe warunki, np. T_zew = 10 °C, E = 50 W/m^2)
    res_step = simulate_greenhouse(
        greenhouse_key=gh_key,
        weather_key="stale",
        T_zad=22.0,
        T_0=15.0,
        Kp=kp,
        Ti=ti,
        Tp=tp,
        sim_hours=4.0,
        T_zew_const=10.0,
        E_const=50.0,
    )
    overshoot_step = float(np.max(res_step["T"]) - 22.0)
    if overshoot_step > 0.5:
        return None

    # Próba 2: nagłe zachmurzenie (T_zad = 22 °C, spadek E z 500 do 100 W/m^2 po 1.5 h)
    t_total = 4.0 * 3600.0
    n_steps = int(round(t_total / tp)) + 1
    t = np.arange(n_steps, dtype=float) * tp
    E_cloud = np.where(t < 1.5 * 3600.0, 500.0, 100.0)
    T_zew_cloud = np.where(t < 1.5 * 3600.0, 16.0, 10.0)
    k_w_cloud = np.where(t < 1.5 * 3600.0, 1.0, 1.2)
    Q_drzwi_cloud = np.zeros(n_steps)

    res_cloud = simulate_greenhouse(
        greenhouse_key=gh_key,
        T_zad=22.0,
        T_0=22.0,
        Kp=kp,
        Ti=ti,
        Tp=tp,
        sim_hours=4.0,
        custom_weather=(E_cloud, T_zew_cloud, k_w_cloud, Q_drzwi_cloud),
    )
    # Przeregulowanie po ustabilizowaniu (lub po nadejściu zachmurzenia)
    post_cloud_mask = t >= 1.5 * 3600.0
    overshoot_cloud = float(np.max(res_cloud["T"][post_cloud_mask]) - 22.0)
    if overshoot_cloud > 0.5:
        return None

    # Całka z modułu uchybu (IAE = sum(|e| * Tp))
    iae_step = float(np.sum(np.abs(res_step["e"])) * tp)
    iae_cloud = float(np.sum(np.abs(res_cloud["e"][post_cloud_mask])) * tp)

    return {
        "Kp": kp,
        "Ti": ti,
        "overshoot_step": overshoot_step,
        "overshoot_cloud": overshoot_cloud,
        "iae_step": iae_step,
        "iae_cloud": iae_cloud,
        "iae_total": iae_step + iae_cloud,
    }


def main() -> None:
    kp_values = [0.5, 1.0, 2.0, 3.0, 5.0, 8.0, 10.0, 12.0, 15.0, 20.0]
    ti_values = [60.0, 120.0, 180.0, 240.0, 300.0, 450.0, 600.0, 900.0, 1200.0, 1800.0]

    print("=== DOBÓR NASTAW REGULATORA PI ===\n")
    for gh_key, gh in GREENHOUSES.items():
        candidates = []
        for kp in kp_values:
            for ti in ti_values:
                result = evaluate_pair(gh_key, kp, ti)
                if result is not None:
                    candidates.append(result)

        candidates.sort(key=lambda r: r["iae_total"])
        print(f"Szklarnia: {gh.name}")
        if not candidates:
            print("  Brak nastaw spełniających warunek przeregulowania <= 0.5 °C!\n")
            continue

        best = candidates[0]
        print(
            f"  Najlepsze nastawy: Kp = {best['Kp']}, Ti = {best['Ti']} s | "
            f"IAE = {best['iae_total']:.1f} °C·s | "
            f"Przeregulowanie (skok): {best['overshoot_step']:.3f} °C, "
            f"(po zachmurzeniu): {best['overshoot_cloud']:.3f} °C"
        )
        print("  Top 3 kandydatów:")
        for c in candidates[:3]:
            print(
                f"    Kp={c['Kp']:>4.1f}, Ti={c['Ti']:>6.0f} s -> "
                f"IAE={c['iae_total']:>8.1f}, "
                f"over_step={c['overshoot_step']:.3f} °C, "
                f"over_cloud={c['overshoot_cloud']:.3f} °C"
            )
        print()


if __name__ == "__main__":
    main()

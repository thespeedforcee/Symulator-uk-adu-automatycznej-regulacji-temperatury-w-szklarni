"""Model matematyczny szklarni i symulator układu regulacji PI."""

from dataclasses import dataclass
import numpy as np


RHO = 1.2       # gęstość powietrza [kg/m^3]
CP = 1005.0     # ciepło właściwe powietrza [J/(kg*K)]
T_CZ = 90.0     # stała czasowa czujnika temperatury [s]
C_PER_M2 = 15000.0  # pojemność cieplna wnętrza na 1 m^2 podłogi [J/(K*m^2)]


@dataclass(frozen=True)
class GreenhouseParams:
    key: str
    name: str
    width: float       # [m]
    length: float      # [m]
    height: float      # [m]
    U: float           # współczynnik przenikania ciepła [W/(m^2*K)]
    tau: float         # przepuszczalność obudowy dla promieniowania [-]
    P_grz_max: float   # maksymalna moc grzałki [W]
    Q_went_max: float  # maksymalny przepływ wentylatora [m^3/s]
    default_kp: float  # domyślne wzmocnienie Kp [1/°C]
    default_ti: float  # domyślny czas zdwojenia Ti [s]

    @property
    def A_p(self) -> float:
        """Powierzchnia podłogi [m^2]."""
        return self.width * self.length

    @property
    def A_ob(self) -> float:
        """Powierzchnia obudowy (ściany + dach) [m^2]."""
        walls = 2.0 * (self.width + self.length) * self.height
        roof = self.width * self.length
        return walls + roof

    @property
    def C(self) -> float:
        """Pojemność cieplna szklarni [J/K]."""
        return C_PER_M2 * self.A_p


GREENHOUSES: dict[str, GreenhouseParams] = {
    "mala": GreenhouseParams(
        key="mala",
        name="Mała przydomowa (szkło, 3×4×2,2 m)",
        width=3.0,
        length=4.0,
        height=2.2,
        U=6.0,
        tau=0.75,
        P_grz_max=6000.0,
        Q_went_max=1.2,
        default_kp=3.0,
        default_ti=240.0,
    ),
    "ogrodnicza": GreenhouseParams(
        key="ogrodnicza",
        name="Ogrodnicza (szkło, 10×10×3 m)",
        width=10.0,
        length=10.0,
        height=3.0,
        U=6.0,
        tau=0.70,
        P_grz_max=30000.0,
        Q_went_max=6.0,
        default_kp=8.0,
        default_ti=240.0,
    ),
    "tunel": GreenhouseParams(
        key="tunel",
        name="Tunel foliowy (folia podwójna, 8×30×3,5 m)",
        width=8.0,
        length=30.0,
        height=3.5,
        U=4.0,
        tau=0.80,
        P_grz_max=60000.0,
        Q_went_max=25.0,
        default_kp=5.0,
        default_ti=450.0,
    ),
}

WEATHER_LABELS: dict[str, str] = {
    "sloneczny": "Słoneczny dzień",
    "zachmurzenie": "Nagłe zachmurzenie",
    "drzwi_wiatr": "Otwarte drzwi i silny wiatr",
    "stale": "Stałe warunki",
}


def generate_weather_profiles(
    weather_key: str,
    t: np.ndarray,
    T_zew_const: float = 10.0,
    E_const: float = 500.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Generuje przebiegi zakłóceń: E(t), T_zew(t), k_w(t), Q_drzwi(t)."""
    n = len(t)
    t_total = t[-1] if n > 1 else 1.0
    frac = t / t_total

    if weather_key == "sloneczny":
        # Płynny cykl dzienny: słońce świeci najmocniej w połowie symulacji
        E = 850.0 * np.maximum(0.0, np.sin(np.pi * frac))
        T_zew = 12.0 + 10.0 * np.sin(np.pi * frac)
        k_w = np.ones(n)
        Q_drzwi = np.zeros(n)

    elif weather_key == "zachmurzenie":
        # Najpierw słonecznie i ciepło, po 1/3 czasu nagłe zachmurzenie
        E = np.where(frac < 0.35, 800.0, 100.0)
        T_zew = np.where(frac < 0.35, 18.0, 11.0)
        k_w = np.where(frac < 0.35, 1.0, 1.2)
        Q_drzwi = np.zeros(n)

    elif weather_key == "drzwi_wiatr":
        # Chłodny dzień; w środkowej części symulacji otwarte drzwi i silny wiatr
        E = np.full(n, 400.0)
        T_zew = np.full(n, 8.0)
        disturbance = (frac >= 0.30) & (frac <= 0.65)
        k_w = np.where(disturbance, 1.8, 1.0)
        Q_drzwi = np.where(disturbance, 1.5, 0.0)

    elif weather_key == "stale":
        E = np.full(n, float(E_const))
        T_zew = np.full(n, float(T_zew_const))
        k_w = np.ones(n)
        Q_drzwi = np.zeros(n)

    else:
        raise ValueError(f"Nieznany profil pogodowy: {weather_key}")

    return E, T_zew, k_w, Q_drzwi


def simulate_greenhouse(
    greenhouse_key: str,
    weather_key: str = "stale",
    T_zad: float = 24.0,
    T_0: float = 12.0,
    Kp: float = 5.0,
    Ti: float = 300.0,
    Tp: float = 10.0,
    sim_hours: float = 12.0,
    T_zew_const: float = 10.0,
    E_const: float = 500.0,
    custom_weather: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray] | None = None,
) -> dict[str, np.ndarray]:
    """Przeprowadza symulację regulacji temperatury w szklarni metodą Eulera."""
    gh = GREENHOUSES[greenhouse_key]
    t_total = sim_hours * 3600.0
    n_steps = int(round(t_total / Tp)) + 1
    t = np.arange(n_steps, dtype=float) * Tp

    if custom_weather is not None:
        E, T_zew, k_w, Q_drzwi = custom_weather
    else:
        E, T_zew, k_w, Q_drzwi = generate_weather_profiles(
            weather_key, t, T_zew_const=T_zew_const, E_const=E_const
        )

    T = np.zeros(n_steps)
    T_m = np.zeros(n_steps)
    T[0] = T_0
    T_m[0] = T_0

    e = np.zeros(n_steps)
    u = np.zeros(n_steps)
    P_sl = np.zeros(n_steps)
    P_grz = np.zeros(n_steps)
    P_ob = np.zeros(n_steps)
    P_went = np.zeros(n_steps)
    P_drzwi = np.zeros(n_steps)

    integral_sum = 0.0

    for n in range(n_steps):
        e[n] = T_zad - T_m[n]

        # Regulator PI z zabezpieczeniem anti-windup (warunkowe całkowanie)
        candidate_integral = integral_sum + e[n]
        u_unsat = Kp * (e[n] + (Tp / Ti) * candidate_integral)
        u_sat = float(np.clip(u_unsat, -10.0, 10.0))

        if (
            u_unsat == u_sat
            or (u_unsat > 10.0 and e[n] < 0.0)
            or (u_unsat < -10.0 and e[n] > 0.0)
        ):
            integral_sum = candidate_integral

        u[n] = u_sat

        # Zamiana sygnału sterującego na moc grzałki lub przepływ wentylatora
        if u_sat > 0.0:
            p_grz_n = (u_sat / 10.0) * gh.P_grz_max
            q_went_n = 0.0
        else:
            p_grz_n = 0.0
            q_went_n = (-u_sat / 10.0) * gh.Q_went_max

        # Bilans energii [W]
        p_sl_n = gh.tau * gh.A_p * E[n]
        dT_ext = T[n] - T_zew[n]
        p_ob_n = k_w[n] * gh.U * gh.A_ob * dT_ext
        p_went_n = RHO * CP * q_went_n * dT_ext
        p_drzwi_n = RHO * CP * Q_drzwi[n] * dT_ext

        P_sl[n] = p_sl_n
        P_grz[n] = p_grz_n
        P_ob[n] = p_ob_n
        P_went[n] = p_went_n
        P_drzwi[n] = p_drzwi_n

        if n < n_steps - 1:
            # Równanie rekurencyjne szklarni
            T[n + 1] = T[n] + (Tp / gh.C) * (
                p_sl_n + p_grz_n - p_ob_n - p_went_n - p_drzwi_n
            )
            # Równanie rekurencyjne czujnika (inercja I rzędu)
            T_m[n + 1] = T_m[n] + (Tp / T_CZ) * (T[n] - T_m[n])

    return {
        "t": t,
        "t_hours": t / 3600.0,
        "T": T,
        "T_m": T_m,
        "T_zad": np.full(n_steps, T_zad),
        "e": e,
        "u": u,
        "P_sl": P_sl,
        "P_grz": P_grz,
        "P_ob": P_ob,
        "P_went": P_went,
        "P_drzwi": P_drzwi,
        "E": E,
        "T_zew": T_zew,
    }

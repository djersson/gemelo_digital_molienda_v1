import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import io

st.set_page_config(layout="wide")
st.title("🌀 Gemelo Digital del Circuito de Molienda")

st.markdown("""
### 📋 Descripción de variables ajustables
| Variable             | Equipo         | Descripción                                                     | Unidad         |
|----------------------|----------------|------------------------------------------------------------------|----------------|
| **RPM SAG**          | Molino SAG     | Revoluciones por minuto del molino SAG                         | rpm            |
| **RPM Bolas**        | Molino Bolas   | Revoluciones por minuto del molino de bolas                    | rpm            |
| **Llenado total**    | Molino SAG     | Fracción del volumen ocupado por carga                         | fracción (0–1) |
| **Carga bolas**      | Molino SAG     | Fracción del volumen ocupado por bolas                         | fracción (0–1) |
| **Tonelaje SAG**     | Molino SAG     | Alimentación fresca al molino SAG                              | TPH            |
| **Presión ciclones** | Ciclones       | Presión de alimentación al ciclón                              | psi            |
| **% Sólidos**        | Ciclones       | Densidad equivalente de pulpa                                  | t/m³           |
| **Ø Apex**           | Ciclones       | Diámetro del orificio inferior (apex)                          | mm             |
| **Ø Vortex**         | Ciclones       | Diámetro del vortex finder (salida central)                    | mm             |
""")

def calcular_modelo(rpm_sag, rpm_bolas, D_sag, L_sag, J_sag, Jb_sag, Wi_sag, T_sag, F80_sag,
                    Wi_mb, F80_mb, D_cyc, D_apex_mm, D_vortex_mm, P_psi, Q_m3h, rho_s):
    Vc = 42.3 / np.sqrt(D_sag)
    Nc_sag = rpm_sag / Vc * 100
    n_sag = rpm_sag
    k_morrell = 0.3
    Ecs_sag = k_morrell * (D_sag**0.3) * (L_sag/D_sag)**0.2 * (Nc_sag / 100)**1.5 * (J_sag**0.45) * (Jb_sag**0.1) * Wi_sag
    P80_sag = (1 / ((Ecs_sag / (10 * Wi_sag)) + (1 / np.sqrt(F80_sag))))**2
    P_sag = Ecs_sag * T_sag / 1000

    D_apex = D_apex_mm / 1000
    D_vortex = D_vortex_mm / 1000
    T_mb = T_sag * (1 + 0.6 * (D_apex + D_vortex))
    E_mb = Ecs_sag * 0.8
    P80_mb = (1 / ((E_mb / (10 * Wi_mb)) + (1 / np.sqrt(F80_mb))))**2
    P_mb_real = E_mb * T_mb / 1000

    Q_m3s = Q_m3h / 3600
    P_kPa = P_psi * 6.89476
    K_plitt = 0.5
    D50c = K_plitt * (D_cyc**0.46) * (D_apex**0.6) * (Q_m3s**-0.27) * (rho_s**0.5) * (P_kPa**-0.3)
    P80_final = D50c * 1.1 * 1e6

    carga_circulante = (T_mb / (T_sag + 1e-6) - 1) * 100
    eficiencia_ciclon = 100 * (1 - (P80_final / F80_mb)) if P80_final < F80_mb else 0
    tonelaje_overflow = T_mb * (1 - (D_apex / D_cyc)**2)

    resultados = pd.DataFrame({
        'Parámetro': ['Vc SAG', 'Vel. SAG', 'Ecs SAG', 'Potencia SAG', 'P80 SAG',
                      'Ecs Bolas', 'Potencia Bolas', 'P80 Bolas',
                      'D50c Ciclón', 'P80 Overflow', 'Carga Circulante', 'Eficiencia Ciclón', 'Ton. Overflow'],
        'Valor': [f'{Vc:.2f} rpm', f'{n_sag:.2f} rpm', f'{Ecs_sag:.2f} kWh/t', f'{P_sag:.2f} MW', f'{P80_sag:.1f} µm',
                  f'{E_mb:.2f} kWh/t', f'{P_mb_real:.2f} MW', f'{P80_mb:.1f} µm',
                  f'{D50c*1e6:.1f} µm', f'{P80_final:.1f} µm', f'{carga_circulante:.1f} %', f'{eficiencia_ciclon:.1f} %', f'{tonelaje_overflow:.1f} TPH']
    })

    return resultados, P80_sag, P80_mb, P80_final

def curva_ggs(p80, n=0.8):
    tamiz = np.array([2360, 2000, 1180, 850, 600, 425, 300, 212, 180, 150, 106, 75, 53, 44, 38])
    y = 100 * (tamiz / p80)**n
    return tamiz, np.clip(100 - y, 0, 100)

def crear_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, txt="Reporte de Resultados - Gemelo Digital", ln=1, align='C')
    for _, row in df.iterrows():
        pdf.cell(200, 8, txt=f"{row['Parámetro']}: {row['Valor']}", ln=1)
    output = io.BytesIO()
    pdf.output(output)
    return output.getvalue()

# === Controles ===
col1, col2 = st.columns(2)
with col1:
    rpm_sag = st.slider("RPM SAG", 5.0, 15.0, 9.0, 0.1)
    rpm_bolas = st.slider("RPM Bolas", 5.0, 20.0, 13.0, 0.1)
    J_sag = st.slider("Llenado total", 0.20, 0.40, 0.275, 0.005)
    Jb_sag = st.slider("Carga bolas", 0.05, 0.20, 0.12, 0.005)
    T_sag = st.slider("Tonelaje SAG (TPH)", 500, 4000, 2848, 50)

with col2:
    P_psi = st.slider("Presión ciclones (psi)", 10.0, 30.0, 14.2, 0.1)
    rho_s = st.slider("Densidad pulpa (t/m³)", 1.5, 3.5, 2.7, 0.1)
    D_apex = st.slider("Ø Apex (mm)", 50, 200, 120, 5)
    D_vortex = st.slider("Ø Vortex (mm)", 100, 300, 200, 5)

# === Simulación ===
resultados, P80_sag, P80_mb, P80_final = calcular_modelo(
    rpm_sag, rpm_bolas, 10.97, 5.28, J_sag, Jb_sag, 12.0, T_sag, 6000,
    14.5, 600,
    0.5, D_apex, D_vortex, P_psi, 4800, rho_s
)

st.subheader("📊 Resultados Técnicos")
st.dataframe(resultados, use_container_width=True)

# === Curva granulométrica ===
t, curva_sag = curva_ggs(P80_sag)
_, curva_mb = curva_ggs(P80_mb)
_, curva_final = curva_ggs(P80_final)

fig, ax = plt.subplots(figsize=(10,6))
ax.plot(t, curva_sag, label=f'SAG (P80={P80_sag:.1f} µm)', marker='o')
ax.plot(t, curva_mb, label=f'Bolas (P80={P80_mb:.1f} µm)', marker='s')
ax.plot(t, curva_final, label=f'Overflow (P80={P80_final:.1f} µm)', marker='^')
ax.axhline(80, color='red', linestyle='--')
ax.set_xscale('log')
ax.set_xlabel("Tamaño de partícula (µm)")
ax.set_ylabel("% Pasante acumulado")
ax.set_title("Curvas Granulométricas Simuladas")
ax.grid(True, which='both', linestyle='--', linewidth=0.5)
ax.legend()
st.pyplot(fig)

# === Exportar Excel ===
buffer = io.BytesIO()
resultados.to_excel(buffer, index=False, engine='openpyxl')
st.download_button("📥 Descargar Excel", data=buffer.getvalue(), file_name="reporte_resultados.xlsx", mime="application/vnd.ms-excel")

# === Exportar PDF ===
st.download_button("📄 Descargar PDF", data=crear_pdf(resultados), file_name="reporte_resultados.pdf", mime="application/pdf")

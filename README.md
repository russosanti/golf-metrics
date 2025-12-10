# Mevo+ Range Dashboard

Dashboard local para analizar **sesiones de driving range** usando datos exportados del FlightScope Mevo+.

- Corre en tu máquina usando **Streamlit**.
- No necesita hosting.
- Guarda las sesiones (CSV) en una carpeta local (`data/sessions`).
- Permite comparar **distintas sesiones y palos** y ver:
  - Indicadores de eficiencia (Smash vs ideal).
  - Índice de consistencia por palo/sesión.
  - Progreso de métricas (Carry, velocidad, spin, etc.).
  - Dispersión de tiros (Curve vs Carry).
  - Datos crudos filtrados.

## Requisitos

- Python 3.10+ recomendado  
- `pip`

## Instalación

1. Creá una carpeta para el proyecto, por ejemplo:

   ```text
   golf-mevo/
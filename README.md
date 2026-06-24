# The 15-Minute City in Buenos Aires

Final project for the course *Ciencia de Datos aplicada al Transporte* (Data Science Applied to Transport) at the University of Buenos Aires (FIUBA). It measures how much of Buenos Aires works as a "15-minute city" — whether people can reach essential services within a 15-minute walk — and whether that access depends on poverty or on urban density.

## The data

- **Street network** — the road graph of Buenos Aires (from OpenStreetMap), used to measure real walking distances along the streets.
- **Census tracts (2010)** — population and poverty (unmet basic needs) per small area, from the national census.
- **Essential services** — hospitals, clinics, pharmacies, schools, supermarkets and parks, downloaded from OpenStreetMap when the notebook runs (so an internet connection is needed for that step).

## Install and run

You need Python 3.11+ installed. From this folder:

```bash
# 1. create a virtual environment
python -m venv .venv

# 2. activate it
source .venv/bin/activate          # on Windows: .venv\Scripts\activate

# 3. install the dependencies
pip install -r requirements.txt

# 4. open the notebook
jupyter notebook Final_Project_15_Minute_City.ipynb
```

Then run the cells from top to bottom. The whole notebook takes about a minute.

## Files

- `Final_Project_15_Minute_City.ipynb` — the full analysis, with the maps and results.
- `data/` — the street network and the census tracts.
- `requirements.txt` — the Python packages.
- `export_figures.py` — optional helper that re-creates all the figures as PNG images (used for the slides).
- `exports/` — those PNG images.

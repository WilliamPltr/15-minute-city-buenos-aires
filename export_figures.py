"""Regenerate every figure of the notebook as a static PNG for the slides.
Run:  python export_figures.py   (the images land in exports/)
This is a helper for the presentation, it is not part of the notebook."""

import os
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import seaborn as sns
import contextily as ctx
import osmnx as ox
import networkx as nx
import h3
from shapely.geometry import Polygon
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

os.makedirs('exports', exist_ok=True)
data_folder = 'data/'

# ---- rebuild the same data as the notebook -------------------------------
street_network = ox.load_graphml(data_folder + 'grafos/buenos_aires_grafo.graphml.xml')
census_tracts = gpd.read_file(data_folder + 'censo_2010/caba_radios_censales_v2.geojson')

osm_tags = {'amenity': ['hospital', 'clinic', 'pharmacy', 'school', 'marketplace'],
            'shop': ['supermarket'], 'leisure': ['park']}
osm_places = ox.features_from_place('Ciudad Autónoma de Buenos Aires, Argentina', tags=osm_tags)
osm_places = osm_places[osm_places.geometry.notna()].copy()
osm_places['geometry'] = osm_places.geometry.centroid

def get_category(place):
    if place.get('leisure') == 'park': return 'recreation'
    if place.get('shop') == 'supermarket' or place.get('amenity') == 'marketplace': return 'shopping'
    if place.get('amenity') == 'school': return 'education'
    if place.get('amenity') in ['hospital', 'clinic', 'pharmacy']: return 'health'

osm_places['category'] = osm_places.apply(get_category, axis=1)
services = osm_places[osm_places.category.notna()][['category', 'geometry']].reset_index(drop=True)
services = gpd.GeoDataFrame(services, geometry='geometry', crs=4326)
service_categories = ['health', 'education', 'shopping', 'recreation']

nodes = ox.graph_to_gdfs(street_network, edges=False)
nodes['h3'] = nodes.apply(lambda node: h3.latlng_to_cell(node.y, node.x, 9), axis=1)
hexagon_ids = nodes['h3'].unique()
hexagons = gpd.GeoDataFrame({'h3': hexagon_ids}, crs=4326,
    geometry=[Polygon([(lng, lat) for lat, lng in h3.cell_to_boundary(h)]) for h in hexagon_ids])

services['node'] = ox.distance.nearest_nodes(street_network, X=services.geometry.x, Y=services.geometry.y)
nodes_by_category = {c: set(services[services.category == c].node) for c in service_categories}
hex_centers = [h3.cell_to_latlng(h) for h in hexagons.h3]
hexagons['node'] = ox.distance.nearest_nodes(street_network,
    X=[c[1] for c in hex_centers], Y=[c[0] for c in hex_centers])

def score_with_budget(start_node, max_meters):
    reachable = set(nx.single_source_dijkstra_path_length(street_network, start_node, cutoff=max_meters, weight='length'))
    return sum(1 for c in service_categories if reachable & nodes_by_category[c])

hexagons['score'] = hexagons.node.map(lambda n: score_with_budget(n, 1250))
hexagons['score_5min'] = hexagons.node.map(lambda n: score_with_budget(n, 417))
hexagons['score_10min'] = hexagons.node.map(lambda n: score_with_budget(n, 833))
hexagons['score_15min'] = hexagons['score']

census_tracts['poverty'] = (census_tracts.HOGARES_NBI / census_tracts.HOGARES * 100).fillna(0)
pairs = gpd.sjoin(hexagons, census_tracts[['poverty', 'geometry']], how='left', predicate='intersects')
hexagons = hexagons.merge(pairs.groupby('h3', as_index=False).poverty.mean(), on='h3')
hexagons['poverty'] = hexagons.poverty.fillna(0)

scaled = StandardScaler().fit_transform(hexagons[['score', 'poverty']].values)
hexagons['cluster'] = KMeans(n_clusters=3, random_state=0, n_init='auto').fit_predict(scaled)

hexagons_mercator = hexagons.to_crs(3857)

# ---- the six figures -----------------------------------------------------
# 1. census tracts
ax = census_tracts.plot(figsize=(7, 8), color='lightblue', edgecolor='white', linewidth=0.2)
ax.set_title('Census tracts of Buenos Aires')
ax.set_axis_off()
plt.savefig('exports/01_census_tracts.png', dpi=150, bbox_inches='tight')
plt.close()

# 2. services by category
ax = census_tracts.plot(figsize=(8, 9), color='whitesmoke', edgecolor='white', linewidth=0.2)
services.plot(ax=ax, column='category', markersize=3, legend=True, alpha=0.6, cmap='tab10')
ax.set_title('Essential services in Buenos Aires')
ax.set_axis_off()
plt.savefig('exports/02_services.png', dpi=150, bbox_inches='tight')
plt.close()

# 3. access map (static version of the interactive map)
fig, ax = plt.subplots(figsize=(9, 10))
hexagons_mercator.plot(column='score', cmap='RdYlGn', vmin=0, vmax=4, legend=True, ax=ax, alpha=0.7)
ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron, crs=hexagons_mercator.crs.to_string())
ax.set_title('15-minute access score (0 to 4)')
ax.set_axis_off()
plt.savefig('exports/03_access_map.png', dpi=150, bbox_inches='tight')
plt.close()

# 4. access vs poverty
plt.figure(figsize=(9, 6))
sns.scatterplot(data=hexagons, x='poverty', y='score', alpha=0.4, color='teal')
sns.regplot(data=hexagons, x='poverty', y='score', scatter=False, color='red')
plt.title('15-minute access vs poverty')
plt.xlabel('% poor households')
plt.ylabel('15-minute score')
plt.savefig('exports/04_access_vs_poverty.png', dpi=150, bbox_inches='tight')
plt.close()

# 5. cluster map (static version of the interactive map)
fig, ax = plt.subplots(figsize=(9, 10))
hexagons_mercator.plot(column='cluster', categorical=True, cmap='Set2', legend=True, ax=ax, alpha=0.7)
ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron, crs=hexagons_mercator.crs.to_string())
ax.set_title('Neighborhood types')
ax.set_axis_off()
plt.savefig('exports/05_cluster_map.png', dpi=150, bbox_inches='tight')
plt.close()

# 6. 5 / 10 / 15 minute comparison
fig, axes = plt.subplots(1, 3, figsize=(18, 7))
for ax, column, title in zip(axes, ['score_5min', 'score_10min', 'score_15min'],
                             ['5-minute city', '10-minute city', '15-minute city']):
    hexagons.plot(column=column, cmap='RdYlGn', vmin=0, vmax=4, legend=True, ax=ax)
    ax.set_title(title)
    ax.set_axis_off()
plt.tight_layout()
plt.savefig('exports/06_5_10_15_min.png', dpi=150, bbox_inches='tight')
plt.close()

print('Done. Six PNGs written to exports/')

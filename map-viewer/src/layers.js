// src/layers.js
import { PMTILES_URL, COG_TILES_URL } from './config.js';

export function addMeshBlockLayer(map) {
  map.addSource('mesh-blocks', {
    type: 'vector',
    url: PMTILES_URL,
  });

map.addLayer({
  id: 'mesh-blocks-fill',
  type: 'fill',
  source: 'mesh-blocks',
  'source-layer': 'mesh_blocks',
  filter: ['!=', ['get', 'mb_category_name_2021'], 'Water'],
  paint: {
    'fill-color': [
      'match', ['get', 'mb_category_name_2021'],
      'Residential',       '#a8c5e8',
      'Commercial',        '#f4a460',
      'Industrial',        '#b8a0c8',
      'Parkland',          '#90c490',
      'Education',         '#f7d080',
      'Hospital/Medical',  '#f08080',
      'Transport',         '#c0c0c0',
      'Primary Production','#d4b896',
      'Other',             '#e0e0e0',
      'SHIPPING',          '#80b4c8',
      /* default */        '#cccccc'
    ],
    'fill-opacity': 0.5,
  },
});

  map.addLayer({
    id: 'mesh-blocks-outline',
    type: 'line',
    source: 'mesh-blocks',
    'source-layer': 'mesh_blocks',
    paint: {
    'line-width': 1,
    'line-color': '#1a3a5c',
    },
  });
}

export function addCOGLayer(map) {
  map.addSource('cog-dtm', {
    type: 'raster',
    tiles: [
        COG_TILES_URL
    ],
    tileSize: 256,
    minzoom: 12,
    maxzoom: 14,
    bounds: [144.891, -37.854, 144.996, -37.771],
  });

  map.addLayer({
    id: 'cog-dtm-layer',
    type: 'raster',
    source: 'cog-dtm',
    paint: {
      'raster-opacity': 0.3,
    },
  });
}
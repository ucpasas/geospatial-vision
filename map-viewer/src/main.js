// src/main.js
import { initProtocol, createMap } from './map.js';
import { addMeshBlockLayer, addCOGLayer } from './layers.js';
import { initUI } from './ui.js';

initProtocol();
const map = createMap();
window._map = map;

map.on('load', () => {
  addCOGLayer(map);
  addMeshBlockLayer(map);
  initUI(map);
  console.log('map loaded');
});
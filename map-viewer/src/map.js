// src/map.js
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { Protocol } from 'pmtiles';
import { INITIAL_CENTER, INITIAL_ZOOM } from './config.js';

export function initProtocol() {
  const protocol = new Protocol();
  maplibregl.addProtocol('pmtiles', protocol.tile.bind(protocol));
}

export function createMap() {
  return new maplibregl.Map({
    container: 'map',
    style: 'https://tiles.openfreemap.org/styles/positron',
    center: INITIAL_CENTER,
    zoom: INITIAL_ZOOM,
  });
}

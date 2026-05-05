// src/ui.js
// DOM only. No renderer imports.
import { CATEGORIES, CATEGORY_COLOURS } from './config.js';

export function initUI(map) {
  _buildLayers(map);
  _buildCategories(map);
  _buildActions(map);
  _buildAttribution();
}

function _section(label, content) {
  return `
    <div class="section">
      <div class="section-label">${label}</div>
      ${content}
    </div>`;
}

function _toggle(id, label, checked = true, swatch = null) {
  const swatchHtml = swatch
    ? `<span class="cat-swatch" style="background:${swatch}"></span>`
    : '';
  return `
    <div class="control-row">
      <div class="control-name">${swatchHtml}${label}</div>
      <label class="toggle">
        <input type="checkbox" id="${id}" ${checked ? 'checked' : ''} />
        <span class="toggle-track"></span>
      </label>
    </div>`;
}

function _buildLayers(map) {
  const html = _section('Layers',
    _toggle('toggle-terrain', 'DTM Terrain') +
    _toggle('toggle-fill', 'MB Fill') +
    _toggle('toggle-outline', 'MB Outline')
  );
  document.getElementById('panel-body').insertAdjacentHTML('beforeend', html);

  const vis = (id, layer) => {
    document.getElementById(id).addEventListener('change', e => {
      map.setLayoutProperty(layer, 'visibility', e.target.checked ? 'visible' : 'none');
    });
  };
  vis('toggle-terrain', 'cog-dtm-layer');
  vis('toggle-fill', 'mesh-blocks-fill');
  vis('toggle-outline', 'mesh-blocks-outline');
}

function _buildCategories(map) {
  const activeCategories = new Set(CATEGORIES);
  const toggles = CATEGORIES.map(cat =>
    _toggle(`cat-${cat.replace(/\W/g, '_')}`, cat, true, CATEGORY_COLOURS[cat])
  ).join('');

  document.getElementById('panel-body').insertAdjacentHTML('beforeend', _section('Categories', toggles));

  CATEGORIES.forEach(cat => {
    const id = `cat-${cat.replace(/\W/g, '_')}`;
    document.getElementById(id).addEventListener('change', e => {
      e.target.checked ? activeCategories.add(cat) : activeCategories.delete(cat);
      const active = [...activeCategories];
      map.setFilter('mesh-blocks-fill', [
        'all',
        ['!=', ['get', 'mb_category_name_2021'], 'Water'],
        ['in', ['get', 'mb_category_name_2021'], ['literal', active]],
      ]);
      map.setFilter('mesh-blocks-outline', [
        'in', ['get', 'mb_category_name_2021'], ['literal', active],
      ]);
    });
  });
}

function _buildActions(map) {
  const html = _section('Actions',
    `<button class="btn" id="btn-cbd">Zoom to CBD</button>`
  );
  document.getElementById('panel-body').insertAdjacentHTML('beforeend', html);

  document.getElementById('btn-cbd').addEventListener('click', () => {
    map.flyTo({ center: [144.9631, -37.8136], zoom: 13, pitch: 45, bearing: -17, duration: 1500 });
  });
}

function _buildAttribution() {
  document.getElementById('attribution').innerHTML = `
    © <a href="https://openfreemap.org" target="_blank">OpenFreeMap</a><br>
    © <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors<br>
    <a href="https://www.abs.gov.au" target="_blank">ABS</a> Mesh Blocks 2021<br>
    <a href="https://data.melbourne.vic.gov.au" target="_blank">City of Melbourne</a> DTM 2018 CC BY 4.0
  `;
}
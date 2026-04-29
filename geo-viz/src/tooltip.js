export function getTooltip({ layer, object }) {
  if (!object) return null;

  const base = {
    style: {
      backgroundColor: 'rgba(15, 20, 30, 0.92)',
      color: '#e8eaf0',
      fontFamily: '"IBM Plex Mono", monospace',
      fontSize: '11px',
      padding: '8px 12px',
      borderRadius: '4px',
      border: '1px solid rgba(100,180,255,0.25)',
      backdropFilter: 'blur(8px)',
      maxWidth: '220px',
      lineHeight: '1.6',
    },
  };

  if (layer.id === 'scatter') {
    return {
      ...base,
      html: `
        <div style="color:#64b5f6;font-weight:600;margin-bottom:4px">POINT</div>
        <div>Lon <span style="color:#fff">${object.lon.toFixed(5)}</span></div>
        <div>Lat <span style="color:#fff">${object.lat.toFixed(5)}</span></div>
        <div>Height <span style="color:#80cbc4">${object.height.toFixed(2)} m</span></div>
      `,
    };
  }

  if (layer.id === 'hex') {
    const count = object.points?.length ?? 0;
    const meanH = count
      ? (object.points.reduce((s, p) => s + p.height, 0) / count).toFixed(1)
      : '—';
    return {
      ...base,
      html: `
        <div style="color:#ffb74d;font-weight:600;margin-bottom:4px">HEX BIN</div>
        <div>Points <span style="color:#fff">${count.toLocaleString()}</span></div>
        <div>Mean height <span style="color:#80cbc4">${meanH} m</span></div>
      `,
    };
  }

  if (layer.id === 'geojson') {
    const p = object.properties || {};
    const name = p.name || p.ref || '—';
    const hw   = p.highway || p.building || p.amenity || 'feature';
    return {
      ...base,
      html: `
        <div style="color:#ce93d8;font-weight:600;margin-bottom:4px">VECTOR</div>
        <div>Type <span style="color:#fff">${hw}</span></div>
        <div>Name <span style="color:#fff">${name}</span></div>
      `,
    };
  }

  return null;
}
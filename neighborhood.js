// Real neighbourhood around the house: terrain (USGS 3DEP) draped with MassGIS 2025 aerial imagery,
// OpenStreetMap footprints extruded into houses with hip roofs textured from the same aerial.
// Data lives in geo/neighborhood.json in model-local metres (x along Irving St, -y toward the street);
// three.js coords are (x, z_up, -y).
import * as THREE from 'three';

export async function addNeighborhood(scene) {
  const data = await fetch('geo/neighborhood.json').then(r => r.json());
  const group = new THREE.Group(); group.name = 'Neighborhood';
  const tex = await new THREE.TextureLoader().loadAsync(data.aerial.file);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 8;
  const [au, av] = data.aerial.uv_affine;
  const uvOf = (X, Y) => [au[0] * X + au[1] * Y + au[2], 1 - (av[0] * X + av[1] * Y + av[2])];

  // ---------------------------------------------------------------- terrain
  const T = data.terrain;
  const heightAtModel = (X, Y) => {
    const fx = THREE.MathUtils.clamp((X - T.x0) / T.step, 0, T.nx - 1.001);
    const fy = THREE.MathUtils.clamp((Y - T.y0) / T.step, 0, T.ny - 1.001);
    const i = Math.floor(fx), j = Math.floor(fy), a = fx - i, b = fy - j;
    const z = T.z;
    return (1 - a) * (1 - b) * z[j][i] + a * (1 - b) * z[j][i + 1] + (1 - a) * b * z[j + 1][i] + a * b * z[j + 1][i + 1];
  };
  const pos = [], uv = [], idx = [];
  for (let j = 0; j < T.ny; j++) for (let i = 0; i < T.nx; i++) {
    const X = T.x0 + i * T.step, Y = T.y0 + j * T.step;
    pos.push(X, T.z[j][i] - 0.02, -Y);
    uv.push(...uvOf(X, Y));
  }
  for (let j = 0; j < T.ny - 1; j++) for (let i = 0; i < T.nx - 1; i++) {
    const a = j * T.nx + i, b = a + 1, c = a + T.nx, d = c + 1;
    idx.push(a, b, c, b, d, c);
  }
  const tg = new THREE.BufferGeometry();
  tg.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  tg.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  tg.setIndex(idx); tg.computeVertexNormals();
  const ground = new THREE.Mesh(tg, new THREE.MeshStandardMaterial({ map: tex, roughness: 0.95 }));
  ground.name = 'Terrain'; ground.receiveShadow = true;
  group.add(ground);

  // ---------------------------------------------------------------- buildings
  const winTex = windowTexture();
  const wallPos = [], wallUv = [], wallCol = [], roofPos = [], roofUv = [];
  const palette = [0xb9b6ae, 0x9aa3a8, 0xc4b8a2, 0x8f9a8a, 0xa89480, 0xd2cfc6, 0x7f8891, 0xb3a28f].map(c => new THREE.Color(c));
  let seed = 7; const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  for (const b of data.buildings) {
    const P = b.pts, n = P.length, z0 = b.base - 0.3, z1 = b.base + b.walls, z2 = z1 + b.roof;
    const col = palette[Math.floor(rnd() * palette.length)];
    // walls
    for (let i = 0; i < n; i++) {
      const [x0, y0] = P[i], [x1, y1] = P[(i + 1) % n];
      const L = Math.hypot(x1 - x0, y1 - y0);
      const quad = [[x0, z0, -y0], [x1, z0, -y1], [x1, z1, -y1], [x0, z1, -y0]];
      const u1 = L / 3.2, v0 = -0.3 / 2.9, v1 = b.walls / 2.9;
      const q = [[0, v0], [u1, v0], [u1, v1], [0, v1]];
      for (const k of [0, 1, 2, 0, 2, 3]) { wallPos.push(...quad[k]); wallUv.push(...q[k]); wallCol.push(col.r, col.g, col.b); }
    }
    // hip roof: ring shrunk toward the centroid
    const cx = P.reduce((s, p) => s + p[0], 0) / n, cy = P.reduce((s, p) => s + p[1], 0) / n;
    const s = b.roof > 0 ? 0.32 : 1.0;
    const top = P.map(([x, y]) => [cx + (x - cx) * s, cy + (y - cy) * s]);
    const eave = P.map(([x, y]) => { const dx = x - cx, dy = y - cy, l = Math.hypot(dx, dy) || 1; return [x + dx / l * 0.35, y + dy / l * 0.35]; });
    if (b.roof > 0) for (let i = 0; i < n; i++) {
      const a = eave[i], bb = eave[(i + 1) % n], c = top[(i + 1) % n], d = top[i];
      const tri = [[a, z1], [bb, z1], [c, z2], [a, z1], [c, z2], [d, z2]];
      for (const [[x, y], zz] of tri) { roofPos.push(x, zz, -y); roofUv.push(...uvOf(x, y)); }
    }
    const tris = THREE.ShapeUtils.triangulateShape(top.map(p => new THREE.Vector2(p[0], p[1])), []);
    for (const t of tris) for (const k of [t[0], t[2], t[1]]) { const [x, y] = top[k]; roofPos.push(x, z2, -y); roofUv.push(...uvOf(x, y)); }
  }
  const wg = new THREE.BufferGeometry();
  wg.setAttribute('position', new THREE.Float32BufferAttribute(wallPos, 3));
  wg.setAttribute('uv', new THREE.Float32BufferAttribute(wallUv, 2));
  wg.setAttribute('color', new THREE.Float32BufferAttribute(wallCol, 3));
  wg.computeVertexNormals();
  const wallMat = new THREE.MeshStandardMaterial({ map: winTex.map, emissiveMap: winTex.glow, emissive: 0xffb36b,
    emissiveIntensity: 0.7, vertexColors: true, roughness: 0.9, side: THREE.DoubleSide });
  const walls = new THREE.Mesh(wg, wallMat);
  walls.name = 'Neighbor_Walls'; walls.castShadow = walls.receiveShadow = true;
  walls.userData.nightGlow = 0.7;
  const rg = new THREE.BufferGeometry();
  rg.setAttribute('position', new THREE.Float32BufferAttribute(roofPos, 3));
  rg.setAttribute('uv', new THREE.Float32BufferAttribute(roofUv, 2));
  rg.computeVertexNormals();
  const roofs = new THREE.Mesh(rg, new THREE.MeshStandardMaterial({ map: tex, roughness: 0.85, side: THREE.DoubleSide }));
  roofs.name = 'Neighbor_Roofs'; roofs.castShadow = true;
  group.add(walls, roofs);

  // ---------------------------------------------------------------- street lamps along the sidewalk
  for (const X of [-16, 19]) {
    const Y = -9.7, h = heightAtModel(X, Y);
    const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.1, 6.5, 8), new THREE.MeshStandardMaterial({ color: 0x111111 }));
    pole.position.set(X, h + 3.25, -Y); group.add(pole);
    const bulb = new THREE.Mesh(new THREE.SphereGeometry(0.22, 12, 8),
      new THREE.MeshStandardMaterial({ color: 0x222222, emissive: 0xffa95a, emissiveIntensity: 3 }));
    bulb.position.set(X, h + 6.5, -Y); bulb.userData.nightGlow = 3; group.add(bulb);
    const l = new THREE.PointLight(0xffa95a, 40, 30, 2); l.position.set(X, h + 6.3, -Y); group.add(l);
  }

  scene.add(group);
  return { group, floors: [ground], walls: [walls], heightAt: (x, z) => heightAtModel(x, -z),
           extent: Math.abs(T.x0) - 4, attribution: data.attribution };
}

function windowTexture() {
  // 2 windows per 3.2 m bay per 2.9 m storey; a random subset glows warm at night
  const S = 256, c = document.createElement('canvas'); c.width = c.height = S;
  const g = c.getContext('2d');
  g.fillStyle = '#ffffff'; g.fillRect(0, 0, S, S);
  g.strokeStyle = 'rgba(0,0,0,.10)';
  for (let y = 0; y < S; y += 9) { g.beginPath(); g.moveTo(0, y); g.lineTo(S, y); g.stroke(); }
  const wins = [[48, 70], [160, 70]];
  g.fillStyle = '#20232a';
  for (const [x, y] of wins) g.fillRect(x, y, 48, 96);
  const glowC = document.createElement('canvas'); glowC.width = glowC.height = S;
  const gg = glowC.getContext('2d'); gg.fillStyle = '#000'; gg.fillRect(0, 0, S, S);
  gg.fillStyle = '#ffffff'; gg.fillRect(wins[0][0] + 4, wins[0][1] + 4, 40, 88);
  const map = new THREE.CanvasTexture(c), glow = new THREE.CanvasTexture(glowC);
  for (const t of [map, glow]) { t.wrapS = t.wrapT = THREE.RepeatWrapping; t.colorSpace = THREE.SRGBColorSpace; }
  return { map, glow };
}

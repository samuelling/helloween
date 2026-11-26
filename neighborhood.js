// Placeholder street context: generic neighbouring houses, street trees and two lamp posts.
// Not real geometry. Swap it for real footprints or a splat scan later (see README).
// Coordinates are glTF/three (x = east-west along the street, z = toward the street, y = up).
import * as THREE from 'three';

function house(w, d, h, pitch, sidingHex, rnd) {
  const g = new THREE.Group();
  const siding = new THREE.MeshStandardMaterial({ color: sidingHex, roughness: 0.85 });
  const roof = new THREE.MeshStandardMaterial({ color: 0x1b1b1e, roughness: 0.9 });
  const body = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), siding);
  body.position.y = h / 2; g.add(body);
  const rh = (d / 2) * Math.tan(pitch);
  const shape = new THREE.Shape([new THREE.Vector2(-d / 2 - 0.4, 0), new THREE.Vector2(d / 2 + 0.4, 0), new THREE.Vector2(0, rh + 0.3)]);
  const r = new THREE.Mesh(new THREE.ExtrudeGeometry(shape, { depth: w + 0.6, bevelEnabled: false }), roof);
  r.rotation.y = Math.PI / 2; r.position.set(-w / 2 - 0.3, h, 0); g.add(r);
  const winGeo = new THREE.PlaneGeometry(0.9, 1.5);
  for (const fy of [h * 0.3, h * 0.72]) {
    for (let i = 0; i < 3; i++) {
      const lit = rnd() < 0.4;
      const m = new THREE.MeshStandardMaterial({ color: 0x111111, emissive: lit ? 0xffb56b : 0x0a0c12, emissiveIntensity: lit ? 1.2 : 0.4 });
      const win = new THREE.Mesh(winGeo, m);
      win.position.set((i - 1) * w * 0.3, fy, d / 2 + 0.01);
      if (lit) win.userData.nightGlow = 1.2;
      g.add(win);
    }
  }
  g.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  return g;
}

function tree(h, rnd) {
  const g = new THREE.Group();
  const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.28, h * 0.5, 8),
    new THREE.MeshStandardMaterial({ color: 0x2a1d14, roughness: 1 }));
  trunk.position.y = h * 0.25; g.add(trunk);
  const leaf = new THREE.MeshStandardMaterial({ color: new THREE.Color().setHSL(0.06 + rnd() * 0.04, 0.55, 0.16), roughness: 1 });
  for (let i = 0; i < 4; i++) {
    const b = new THREE.Mesh(new THREE.IcosahedronGeometry(h * (0.22 + rnd() * 0.08), 1), leaf);
    b.position.set((rnd() - 0.5) * h * 0.3, h * (0.6 + rnd() * 0.25), (rnd() - 0.5) * h * 0.3);
    g.add(b);
  }
  g.traverse(o => { if (o.isMesh) o.castShadow = true; });
  return g;
}

export function addNeighborhood(scene) {
  let seed = 31;
  const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  const hood = new THREE.Group(); hood.name = 'Placeholder_Neighborhood';
  const colours = [0x8c8f94, 0x6f7c86, 0xa89f8f, 0x5d6b5f, 0x9a8a7a, 0x7a6f86];
  // same side of the street (house fronts face +z toward the street, front wall at z = 0)
  for (const [x, w, d, h] of [[-18.5, 9, 12, 8.5], [-31, 10, 13, 7.8], [20, 9.5, 12, 9], [32.5, 9, 11, 7.6]]) {
    const hs = house(w, d, h, 0.62, colours[Math.floor(rnd() * colours.length)], rnd);
    hs.position.set(x, 0, -d / 2 - 0.5); hood.add(hs);
  }
  // across the street (fronts face -z)
  for (const x of [-26, -13, 0, 13, 26]) {
    const w = 8.5 + rnd() * 2, d = 11 + rnd() * 2, h = 7.5 + rnd() * 2;
    const hs = house(w, d, h, 0.6, colours[Math.floor(rnd() * colours.length)], rnd);
    hs.rotation.y = Math.PI; hs.position.set(x + (rnd() - 0.5) * 2, 0, 18 + d / 2 + 5); hood.add(hs);
  }
  // opposite sidewalk + ground beyond the street
  const far = new THREE.Mesh(new THREE.PlaneGeometry(80, 30), new THREE.MeshStandardMaterial({ color: 0x15170f, roughness: 1 }));
  far.rotation.x = -Math.PI / 2; far.position.set(0, -0.005, 30 + 15 - 8); far.receiveShadow = true; far.name = 'Lawn_Far';
  hood.add(far);
  const walk = new THREE.Mesh(new THREE.BoxGeometry(80, 0.1, 1.8), new THREE.MeshStandardMaterial({ color: 0x3a3936, roughness: 0.9 }));
  walk.position.set(0, -0.08, 21.2); walk.receiveShadow = true; walk.name = 'Sidewalk_Far'; hood.add(walk);
  // street trees
  for (const [x, z] of [[-9, 9.3], [11, 9.4], [-22, 9.2], [24, 9.5], [-6, 21.3], [8, 21.4], [-19, 21.2]]) {
    const t = tree(7 + rnd() * 4, rnd); t.position.set(x, 0, z); hood.add(t);
  }
  // lamp posts with warm sodium light
  for (const [x, z] of [[-14, 9.6], [16, 21.0]]) {
    const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.1, 6, 8), new THREE.MeshStandardMaterial({ color: 0x111111 }));
    pole.position.set(x, 3, z); hood.add(pole);
    const bulb = new THREE.Mesh(new THREE.SphereGeometry(0.22, 12, 8),
      new THREE.MeshStandardMaterial({ color: 0x222222, emissive: 0xffa95a, emissiveIntensity: 3 }));
    bulb.position.set(x, 6, z); bulb.userData.nightGlow = 3; hood.add(bulb);
    const l = new THREE.PointLight(0xffa95a, 40, 30, 2); l.position.set(x, 5.8, z); hood.add(l);
    l.userData.isStreetLamp = true;
  }
  scene.add(hood);
  return hood;
}

// Helloween decorator: a drawer of bizarre props + a light rig. Place anything on any surface, move /
// rotate / scale it with a gizmo, pose rigged props joint by joint (the articulator), and save,
// load or share the layout.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { TransformControls } from 'three/addons/controls/TransformControls.js';
import * as SkeletonUtils from 'three/addons/utils/SkeletonUtils.js';
import { initRig, applyPreset, presetsFor, capturePose, applyPose } from './poses.js?v=11';

const LIGHTS = {
  spot:     { name: 'Spotlight', icon: '🔦', type: 'spot', color: '#ff2a12', intensity: 260, angle: 22, penumbra: 0.4, desc: 'Aimable ground spot. Rotate it to aim.' },
  flood:    { name: 'Floodlight', icon: '💡', type: 'spot', color: '#ff1c0c', intensity: 700, angle: 55, penumbra: 0.7, desc: 'Wide wash for walls and porches.' },
  uplight:  { name: 'Uplight', icon: '⬆️', type: 'spot', color: '#ff2a12', intensity: 120, angle: 28, penumbra: 0.5, up: true, desc: 'Small can that grazes up a prop or column.' },
  beam:     { name: 'Searchlight beam', icon: '🔆', type: 'spot', color: '#bfe0ff', intensity: 900, angle: 5, penumbra: 0.2, beam: true, effect: 'sweep', desc: 'Narrow beam with a visible cone. Sweeps the sky.' },
  orb:      { name: 'Glowing orb', icon: '🔮', type: 'point', color: '#7a3cff', intensity: 25, orb: true, effect: 'pulse', desc: 'Floating point light with a glowing sphere.' },
  torch:    { name: 'Tiki torch', icon: '🔥', type: 'point', color: '#ff8a2a', intensity: 18, torch: true, effect: 'flicker', desc: 'Flickering firelight on a pole.' },
  strobe:   { name: 'Strobe', icon: '⚡', type: 'spot', color: '#ffffff', intensity: 900, angle: 50, penumbra: 0.3, effect: 'strobe', desc: 'Strobe flash.' },
  cycle:    { name: 'Colour wash', icon: '🌈', type: 'spot', color: '#ff00aa', intensity: 500, angle: 45, penumbra: 0.6, effect: 'cycle', desc: 'Wash that slowly cycles hue.' },
  lightning:{ name: 'Lightning storm', icon: '🌩️', type: 'lightning', desc: 'Random lightning flashes across the whole sky.' },
  fog:      { name: 'Ground fog', icon: '🌫️', type: 'fog', color: '#b9c2d0', radius: 3, desc: 'A low patch of drifting fog.' },
};
const EFFECTS = ['steady', 'flicker', 'pulse', 'strobe', 'cycle', 'sweep'];
const ORIGINAL_GROUPS = {
  'Skeletons': /^(Porch_)?Skeleton_/, 'Girls': /^Girl_/, 'Antler staves': /^Stave_/, 'Cairn': /^Cairn_/,
  'Horned figure + candles': /^(Horned_Figure|Oryx|LED_Candle|Candle)/, 'Porch props': /^(Rocking_Chair|Wreath|Ram_Horns|Star_Lantern|Pumpkin_)/,
};

export function initDecorator(ctx) {
  const { scene, camera, renderer, orbit, root: house, hood, redLights } = ctx;
  const loader = new GLTFLoader();
  const cache = {}, catalog = {};
  const decor = new THREE.Group(); decor.name = 'Decor'; scene.add(decor);
  const tc = new TransformControls(camera, renderer.domElement);
  tc.setSize(0.8);
  scene.add(tc.getHelper());
  let selected = null, placing = null, ghost = null, poseMode = false, jointSel = null;
  let lightning = null, uid = 1;
  const undo = [], redo = [];

  // ------------------------------------------------------------------ UI
  const css = document.createElement('style');
  css.textContent = `
  #decor { position:absolute; left:12px; top:12px; bottom:12px; width:300px; display:none; flex-direction:column;
    background:rgba(10,8,10,.86); border:1px solid #2a2226; border-radius:10px; backdrop-filter:blur(6px);
    font:13px/1.35 system-ui,sans-serif; color:#eee6df; z-index:5; }
  body.decorating #decor { display:flex; } body.decorating header, body.decorating #hint { display:none; }
  #decor .top { display:flex; gap:4px; padding:10px 10px 6px; flex-wrap:wrap; }
  #decor .top button, #insp button, #decor select { all:unset; cursor:pointer; padding:4px 8px; border:1px solid #3a3034;
    border-radius:6px; font-size:12px; background:#151013; }
  #decor .top button:hover, #insp button:hover { border-color:#ff3b2a; }
  #decor .tabs { display:flex; flex-wrap:wrap; gap:3px; padding:0 10px 6px; }
  #decor .tabs span { cursor:pointer; padding:3px 7px; border-radius:20px; font-size:11px; background:#1b1518; color:#bdb2ab; }
  #decor .tabs span.on { background:#ff3b2a; color:#000; font-weight:600; }
  #decor .grid { flex:1; overflow:auto; display:grid; grid-template-columns:1fr 1fr 1fr; gap:6px; padding:4px 10px 10px; align-content:start; }
  #decor .item { cursor:pointer; border:1px solid #2a2226; border-radius:7px; overflow:hidden; background:#120e10; text-align:center; }
  #decor .item:hover, #decor .item.on { border-color:#ff3b2a; }
  #decor .item img { width:100%; aspect-ratio:1; display:block; object-fit:cover; }
  #decor .item .ic { font-size:34px; line-height:78px; }
  #decor .item div { font-size:10.5px; padding:3px 2px 4px; color:#d8cfc8; }
  #insp { border-top:1px solid #2a2226; padding:10px; max-height:46%; overflow:auto; }
  #insp h4 { margin:0 0 6px; font:600 13px system-ui; color:#fff; }
  #insp .row { display:flex; align-items:center; justify-content:space-between; gap:8px; margin:5px 0; font-size:12px; }
  #insp .btns { display:flex; flex-wrap:wrap; gap:4px; margin:6px 0; }
  #insp button.on { background:#ff3b2a; color:#000; border-color:#ff3b2a; }
  #insp input[type=range] { width:140px; accent-color:#ff3b2a; }
  #insp .muted, #decor .muted { color:#8d8580; font-size:11px; }
  #decorBtn { all:unset; cursor:pointer; display:block; text-align:center; margin:0 0 12px; padding:9px 0; border-radius:8px;
    border:1px solid #ff3b2a; color:#ff3b2a; font:700 14px system-ui; }
  body.decorating #decorBtn { background:#ff3b2a; color:#000; }
  #placeHint { position:absolute; left:50%; top:14px; transform:translateX(-50%); padding:7px 12px; border-radius:8px;
    background:rgba(0,0,0,.7); font:12px system-ui; color:#fff; display:none; z-index:6; }
  @media (max-width:700px) { #decor { width:auto; right:12px; bottom:auto; height:48vh; } }`;
  document.head.appendChild(css);
  const panel = document.createElement('div');
  panel.id = 'decor';
  panel.innerHTML = `
    <div class="top">
      <button data-a="undo" title="Ctrl/⌘+Z">↶ Undo</button><button data-a="redo" title="Ctrl/⌘+Shift+Z">↷</button>
      <button data-a="share">🔗 Share</button><button data-a="export">⬇ Save file</button>
      <button data-a="import">⬆ Load</button><button data-a="clear">🗑 Clear</button>
      <button data-a="originals">👁 Originals</button>
    </div>
    <div class="tabs"></div><div class="grid"></div><div id="insp"><span class="muted">Pick something from the drawer,
    then click anywhere (lawn, porch, roof) to place it. Click a placed item to edit it.<br><br>
    <b>Keys:</b> W move · E rotate · R scale · D duplicate · G drop to ground · Del delete · Esc deselect</span></div>
    <input type="file" accept=".json,application/json" style="display:none">`;
  document.getElementById('stage').appendChild(panel);
  const hint = document.createElement('div'); hint.id = 'placeHint';
  document.getElementById('stage').appendChild(hint);
  const insp = panel.querySelector('#insp');
  const fileIn = panel.querySelector('input[type=file]');

  const btn = document.createElement('button');
  btn.id = 'decorBtn'; btn.textContent = '🎃 Decorate';
  const wb = document.getElementById('walkBtn'); wb.after(btn);
  btn.onclick = () => setDecorating(!document.body.classList.contains('decorating'));

  function setDecorating(on) {
    document.body.classList.toggle('decorating', on);
    btn.textContent = on ? '✓ Done decorating' : '🎃 Decorate';
    if (!on) { select(null); cancelPlace(); }
  }

  // ------------------------------------------------------------------ catalog + drawer
  let tab = 'Bones';
  async function loadCatalog() {
    const c = await fetch('props/catalog.json?v=11').then(r => r.json());
    Object.assign(catalog, c);
    const cats = [...new Set(Object.values(c).map(p => p.cat))];
    const order = ['Bones', 'Creatures', 'Ghouls', 'Graveyard', 'Spooky stuff', 'Lights', 'Effects', '2026 display'];
    const tabs = order.filter(t => cats.includes(t) || t === 'Lights' || t === 'Effects');
    panel.querySelector('.tabs').innerHTML = tabs.map(t => `<span data-t="${t}">${t}</span>`).join('');
    panel.querySelectorAll('.tabs span').forEach(s => s.onclick = () => { tab = s.dataset.t; drawGrid(); });
    drawGrid();
  }
  function drawGrid() {
    panel.querySelectorAll('.tabs span').forEach(s => s.classList.toggle('on', s.dataset.t === tab));
    const g = panel.querySelector('.grid');
    let items;
    if (tab === 'Lights') items = Object.entries(LIGHTS).filter(([k, v]) => !['fog', 'lightning'].includes(k));
    else if (tab === 'Effects') items = Object.entries(LIGHTS).filter(([k]) => ['fog', 'lightning'].includes(k));
    else items = Object.entries(catalog).filter(([, p]) => p.cat === tab);
    g.innerHTML = items.map(([k, p]) => `<div class="item" data-k="${k}" title="${(p.desc || '').replace(/"/g, '')}">` +
      (p.thumb ? `<img src="${p.thumb}" loading="lazy">` : `<div class="ic">${p.icon}</div>`) +
      `<div>${p.name}${p.rig ? ' 🦴' : ''}</div></div>`).join('');
    g.querySelectorAll('.item').forEach(el => el.onclick = () => startPlace(el.dataset.k));
  }

  // ------------------------------------------------------------------ building instances
  async function getGLTF(id) {
    if (!cache[id]) cache[id] = loader.loadAsync(catalog[id].file);
    return cache[id];
  }
  async function makeProp(id) {
    const p = catalog[id], g = await getGLTF(id);
    const obj = SkeletonUtils.clone(g.scene);
    const wrap = new THREE.Group();
    wrap.add(obj);
    wrap.userData = { decor: true, kind: 'prop', id, uid: uid++ };
    obj.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; o.frustumCulled = !o.isSkinnedMesh; } });
    if (p.bones) wrap.userData.rig = initRig(obj, p.bones);
    if (p.light) {
      const L = new THREE.PointLight(p.light.color, p.light.intensity, 12, 2);
      L.position.set(...p.light.offset); obj.add(L);
      wrap.userData.propLight = L; wrap.userData.baseIntensity = p.light.intensity;
    }
    wrap.userData.behaviors = p.behaviors || [];
    wrap.userData.inner = obj;
    const named = {};
    obj.traverse(o => { if (/^(Eye_|Wing_|Bat_|Lid_Hinge|Head$)/.test(o.name)) (named[o.name.split('_')[0]] ||= []).push(o); });
    wrap.userData.named = named;
    obj.traverse(o => { if (o.isMesh && o.material.emissiveIntensity > 0 && o.material.emissive?.getHex()) {
      o.material = o.material.clone(); o.userData.emit0 = o.material.emissiveIntensity; } });
    return wrap;
  }

  function makeLight(kind, s = {}) {
    const d = { ...LIGHTS[kind], ...s };
    const wrap = new THREE.Group();
    wrap.userData = { decor: true, kind: 'light', lkind: kind, uid: uid++,
      color: d.color, intensity: d.intensity, angle: d.angle, penumbra: d.penumbra, effect: d.effect || 'steady',
      beam: !!d.beam, shadow: !!s.shadow, radius: d.radius || 3 };
    const black = new THREE.MeshStandardMaterial({ color: 0x0c0c0c, roughness: 0.5, metalness: 0.4 });
    const lens = new THREE.MeshStandardMaterial({ color: 0x111111, emissive: new THREE.Color(d.color || '#fff'), emissiveIntensity: 2 });
    wrap.userData.lensMat = lens;
    if (d.type === 'spot') {
      const head = new THREE.Group(); wrap.add(head); wrap.userData.head = head;
      const r = kind === 'flood' ? 0.16 : kind === 'beam' ? 0.22 : 0.08;
      const can = new THREE.Mesh(new THREE.CylinderGeometry(r, r * 0.85, r * 2.2, 18), black);
      can.rotation.x = Math.PI / 2; head.add(can);
      const glass = new THREE.Mesh(new THREE.CircleGeometry(r * 0.9, 18), lens); glass.position.z = r * 1.11; head.add(glass);
      const stake = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, 0.25, 6), black); stake.position.y = -0.17; wrap.add(stake);
      head.position.y = 0.06 + r;
      const L = new THREE.SpotLight(d.color, d.intensity, 0, THREE.MathUtils.degToRad(d.angle), d.penumbra, 2);
      L.position.set(0, 0, r * 1.2); L.target.position.set(0, 0, 5);
      head.add(L, L.target);
      L.shadow.mapSize.set(1024, 1024); L.shadow.bias = -0.0005;
      wrap.userData.light = L;
      if (d.up) head.rotation.x = -Math.PI / 2; else head.rotation.x = -0.35;
      const cone = beamCone(d.color); cone.visible = !!d.beam; L.add(cone); wrap.userData.cone = cone;
      updateCone(wrap);
    } else if (d.type === 'point') {
      const L = new THREE.PointLight(d.color, d.intensity, 0, 2);
      wrap.add(L); wrap.userData.light = L;
      if (d.orb) {
        const s1 = new THREE.Mesh(new THREE.SphereGeometry(0.12, 24, 16), lens); s1.position.y = 1.3; wrap.add(s1);
        L.position.y = 1.3;
      } else {
        const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.035, 1.5, 8), new THREE.MeshStandardMaterial({ color: 0x5a3c22 }));
        pole.position.y = 0.75; wrap.add(pole);
        const cup = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.05, 0.16, 10), black); cup.position.y = 1.55; wrap.add(cup);
        const flame = new THREE.Mesh(new THREE.ConeGeometry(0.06, 0.22, 10), lens); flame.position.y = 1.74; wrap.add(flame);
        wrap.userData.flame = flame; L.position.y = 1.8;
      }
    } else if (d.type === 'fog') {
      wrap.add(fogPatch(wrap.userData));
    } else if (d.type === 'lightning') {
      const bolt = new THREE.Mesh(new THREE.OctahedronGeometry(0.25), new THREE.MeshStandardMaterial({ color: 0x223, emissive: 0x8fb0ff, emissiveIntensity: 2 }));
      bolt.position.y = 1.5; wrap.add(bolt);
      ensureLightning();
    }
    wrap.traverse(o => { if (o.isMesh) { o.castShadow = false; } });
    applyLightProps(wrap);
    return wrap;
  }

  function beamCone(color) {
    const geo = new THREE.ConeGeometry(1, 1, 32, 1, true);
    geo.translate(0, -0.5, 0); geo.rotateX(-Math.PI / 2);   // apex at origin, opening along +Z
    const mat = new THREE.ShaderMaterial({
      uniforms: { color: { value: new THREE.Color(color) }, strength: { value: 0.35 } },
      vertexShader: `varying float vZ; void main(){ vZ = position.z; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.); }`,
      fragmentShader: `uniform vec3 color; uniform float strength; varying float vZ;
        void main(){ float a = strength * pow(1.0 - clamp(vZ,0.,1.), 1.6); gl_FragColor = vec4(color*a, a); }`,
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide });
    const m = new THREE.Mesh(geo, mat);
    m.raycast = () => {};
    return m;
  }
  function updateCone(w) {
    const u = w.userData, c = u.cone; if (!c) return;
    const len = 30, r = Math.tan(THREE.MathUtils.degToRad(u.angle)) * len;
    c.scale.set(r, r, len);
    c.material.uniforms.color.value.set(u.color);
    c.visible = u.beam;
  }

  function fogPatch(u) {
    const g = new THREE.Group(); g.name = 'FogPatch';
    const cv = document.createElement('canvas'); cv.width = cv.height = 128;
    const x = cv.getContext('2d'), gr = x.createRadialGradient(64, 64, 4, 64, 64, 64);
    gr.addColorStop(0, 'rgba(255,255,255,.55)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
    x.fillStyle = gr; x.fillRect(0, 0, 128, 128);
    const tex = new THREE.CanvasTexture(cv);
    for (let i = 0; i < 16; i++) {
      const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, color: u.color, opacity: 0.32, depthWrite: false, transparent: true }));
      const a = Math.random() * Math.PI * 2, r = Math.random() * u.radius;
      s.position.set(Math.cos(a) * r, 0.25 + Math.random() * 0.35, Math.sin(a) * r);
      s.scale.setScalar(1.6 + Math.random() * 1.6);
      s.userData.phase = Math.random() * 10;
      s.raycast = () => {};
      g.add(s);
    }
    const hit = new THREE.Mesh(new THREE.CylinderGeometry(0.25, 0.25, 0.1, 12), new THREE.MeshBasicMaterial({ color: 0x8090a0, transparent: true, opacity: 0.35 }));
    hit.position.y = 0.05; g.add(hit);
    return g;
  }

  let flash = null;
  function ensureLightning() {
    if (lightning) return;
    lightning = new THREE.DirectionalLight(0xc8d8ff, 0);
    lightning.position.set(-30, 60, 40); scene.add(lightning);
    flash = { next: 2, until: 0, bursts: 0 };
  }

  function applyLightProps(w) {
    const u = w.userData, L = u.light;
    if (u.lensMat) u.lensMat.emissive.set(u.color || '#fff');
    if (!L) { w.traverse(o => { if (o.isSprite) { o.material.color.set(u.color); } }); return; }
    L.color.set(u.color);
    if (L.isSpotLight) { L.angle = THREE.MathUtils.degToRad(u.angle); L.penumbra = u.penumbra; }
    L.castShadow = !!u.shadow;
    updateCone(w);
  }

  // ------------------------------------------------------------------ placement
  const ray = new THREE.Raycaster(), mouse = new THREE.Vector2();
  function pick(e, objs) {
    const r = renderer.domElement.getBoundingClientRect();
    mouse.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(mouse, camera);
    return ray.intersectObjects(objs, true).filter(h => visibleChain(h.object) && !isGizmo(h.object));
  }
  const visibleChain = o => { for (let p = o; p; p = p.parent) if (!p.visible) return false; return true; };
  const isGizmo = o => { for (let p = o; p; p = p.parent) if (p === ghost) return true; return false; };
  const surfaces = () => [house, ...(hood ? [hood.group] : []), decor];

  async function startPlace(key) {
    cancelPlace();
    select(null);
    placing = key;
    panel.querySelectorAll('.item').forEach(el => el.classList.toggle('on', el.dataset.k === key));
    hint.style.display = 'block';
    hint.textContent = 'Click to place · Shift-click to place several · Esc to cancel';
    ghost = LIGHTS[key] ? makeLight(key) : await makeProp(key);
    if (placing !== key) return;
    ghost.traverse(o => { if (o.isMesh && o.material && !o.material.isShaderMaterial) { o.material = o.material.clone(); o.material.transparent = true; o.material.opacity = 0.55; } });
    ghost.visible = false;
    scene.add(ghost);
  }
  function cancelPlace() {
    placing = null; hint.style.display = 'none';
    panel.querySelectorAll('.item').forEach(el => el.classList.remove('on'));
    if (ghost) { ghost.removeFromParent(); disposeLights(ghost); ghost = null; }
  }
  function disposeLights(o) { o.traverse(x => { if (x.isLight && x.shadow?.map) x.shadow.map.dispose(); }); }

  const el = renderer.domElement;
  let down = null;
  el.addEventListener('pointermove', e => {
    if (!placing || !ghost) return;
    const h = pick(e, surfaces().filter(s => s !== decor))[0];
    if (!h) { ghost.visible = false; return; }
    ghost.visible = true;
    ghost.position.copy(h.point);
    const toCam = camera.position.clone().sub(h.point); toCam.y = 0;
    ghost.rotation.set(0, Math.atan2(toCam.x, toCam.z), 0);
  });
  el.addEventListener('pointerdown', e => { down = { x: e.clientX, y: e.clientY }; });
  el.addEventListener('pointerup', async e => {
    if (!document.body.classList.contains('decorating') || !down) return;
    if (Math.hypot(e.clientX - down.x, e.clientY - down.y) > 5 || tc.dragging) return;
    if (placing && ghost && ghost.visible) {
      const key = placing, pos = ghost.position.clone(), rot = ghost.rotation.y;
      const obj = LIGHTS[key] ? makeLight(key) : await makeProp(key);
      obj.position.copy(pos); obj.rotation.y = rot;
      if (obj.userData.kind === 'light' && obj.userData.head && !LIGHTS[key].up) aimAtHouse(obj);
      decor.add(obj);
      if (obj.userData.rig) groundSnap(obj);
      commit();
      if (!e.shiftKey) { cancelPlace(); select(obj); }
      return;
    }
    if (poseMode && selected?.userData.rig) {
      const hs = pick(e, [jointGroup]);
      if (hs[0]) { selectJoint(hs[0].object.userData.bone); return; }
    }
    const hits = pick(e, [decor]);
    let o = hits[0]?.object;
    while (o && !o.userData.decor) o = o.parent;
    select(o || null);
  });

  function aimAtHouse(w) {
    w.updateMatrixWorld(true);
    w.userData.head.lookAt(new THREE.Vector3(w.position.x * 0.7, 3.2, -1));
  }

  // ------------------------------------------------------------------ selection + inspector
  tc.addEventListener('dragging-changed', e => { orbit.enabled = !e.value; if (!e.value) commit(); });
  tc.addEventListener('objectChange', () => { if (jointSel) markPosed(); });

  function select(o) {
    if (jointGroup.parent) jointGroup.removeFromParent();
    poseMode = false; jointSel = null;
    selected = o;
    if (o) { tc.setSpace('world'); tc.setMode(tc.mode === 'rotate' && o.userData.kind === 'prop' ? 'rotate' : 'translate'); tc.attach(o); }
    else tc.detach();
    drawInspector();
  }

  function drawInspector() {
    if (!selected) {
      insp.innerHTML = `<span class="muted">Pick something from the drawer, then click anywhere (lawn, porch, roof) to place it.
        Click a placed item to edit it.<br><br><b>Keys:</b> W move · E rotate · R scale · D duplicate · G drop to ground · Del delete · Esc deselect</span>`;
      return;
    }
    const u = selected.userData;
    const title = u.kind === 'prop' ? catalog[u.id].name : LIGHTS[u.lkind].name;
    let h = `<h4>${title}</h4><div class="btns">
      <button data-m="translate" class="${tc.mode === 'translate' && !poseMode ? 'on' : ''}">Move</button>
      <button data-m="rotate" class="${tc.mode === 'rotate' && !poseMode ? 'on' : ''}">Rotate</button>
      <button data-m="scale" class="${tc.mode === 'scale' && !poseMode ? 'on' : ''}">Scale</button>
      <button data-a="dup">Duplicate</button><button data-a="ground">Drop</button><button data-a="del">Delete</button></div>`;
    if (u.kind === 'prop' && u.rig) {
      const rk = catalog[u.id].rig;
      h += `<div class="row"><b>Articulator</b><button data-a="pose" class="${poseMode ? 'on' : ''}">${poseMode ? 'Posing…' : 'Pose joints'}</button></div>
        <div class="row">Preset <select data-a="preset"><option value="">choose…</option>${presetsFor(rk).map(p => `<option>${p}</option>`).join('')}</select></div>
        <div class="muted">${poseMode ? (jointSel ? `Rotating <b>${jointSel.name}</b>. Drag the rings. Click another joint dot to switch.` : 'Click a joint dot, then drag the rings to bend it.') : 'Pose joints shows a dot on every joint.'}</div>
        ${poseMode ? '<div class="btns"><button data-a="resetjoint">Reset joint</button><button data-a="resetall">Reset whole pose</button></div>' : ''}`;
    }
    if (u.kind === 'light') {
      const L = LIGHTS[u.lkind];
      if (L.type !== 'lightning') h += `<div class="row">Colour <input type="color" data-p="color" value="${u.color}"></div>`;
      if (u.light) {
        h += `<div class="row">Brightness <input type="range" data-p="intensity" min="0" max="${L.type === 'point' ? 120 : 2500}" step="1" value="${u.intensity}"></div>`;
        if (u.light.isSpotLight) h += `<div class="row">Cone angle <input type="range" data-p="angle" min="2" max="80" step="1" value="${u.angle}"></div>
          <div class="row">Soft edge <input type="range" data-p="penumbra" min="0" max="1" step="0.01" value="${u.penumbra}"></div>
          <div class="row">Visible beam <input type="checkbox" data-p="beam" ${u.beam ? 'checked' : ''}></div>
          <div class="row">Cast shadows <input type="checkbox" data-p="shadow" ${u.shadow ? 'checked' : ''}></div>
          <div class="muted">Rotate the light to aim it.</div>`;
        h += `<div class="row">Effect <select data-p="effect">${EFFECTS.map(f => `<option ${f === u.effect ? 'selected' : ''}>${f}</option>`).join('')}</select></div>`;
      }
      if (L.type === 'fog') h += `<div class="row">Spread <input type="range" data-p="radius" min="1" max="8" step="0.5" value="${u.radius}"></div>`;
    }
    if (u.kind === 'prop') h += `<div class="muted">${catalog[u.id].desc || ''}</div>`;
    insp.innerHTML = h;
    insp.querySelectorAll('[data-m]').forEach(b => b.onclick = () => { exitPose(); tc.attach(selected); tc.setMode(b.dataset.m); tc.setSpace(b.dataset.m === 'translate' ? 'world' : 'local'); drawInspector(); });
    insp.querySelectorAll('button[data-a]').forEach(b => b.onclick = () => action(b.dataset.a));
    const pre = insp.querySelector('select[data-a=preset]');
    if (pre) pre.onchange = () => { if (pre.value) { setPreset(selected, pre.value); } };
    insp.querySelectorAll('[data-p]').forEach(inp => {
      const ev = inp.type === 'checkbox' || inp.tagName === 'SELECT' ? 'change' : 'input';
      inp.addEventListener(ev, () => {
        const k = inp.dataset.p;
        u[k] = inp.type === 'checkbox' ? inp.checked : inp.type === 'range' ? +inp.value : inp.value;
        if (k === 'shadow' && u.shadow && shadowCount() > 4) { u.shadow = false; inp.checked = false; alert('Up to 4 shadow-casting lights keeps it smooth.'); }
        if (k === 'radius') { selected.children.forEach(c => c.name === 'FogPatch' && selected.remove(c)); selected.add(fogPatch(u)); }
        applyLightProps(selected);
      });
      inp.addEventListener('change', commit);
    });
  }
  const shadowCount = () => decor.children.filter(o => o.userData.shadow).length;

  function action(a) {
    if (!selected) return;
    if (a === 'del') { const s = selected; select(null); disposeLights(s); s.removeFromParent(); commit(); }
    if (a === 'dup') duplicate();
    if (a === 'ground') { groundSnap(selected); commit(); }
    if (a === 'pose') { poseMode ? exitPose() : enterPose(); drawInspector(); }
    if (a === 'resetjoint' && jointSel) { jointSel.quaternion.copy(jointSel.userData.rest); commit(); }
    if (a === 'resetall') { setPreset(selected, presetsFor(catalog[selected.userData.id].rig)[0]); }
  }

  async function duplicate() {
    const s = serializeItem(selected);
    s.pos = [s.pos[0] + 0.8, s.pos[1], s.pos[2] + 0.4];
    const o = await buildItem(s);
    decor.add(o); select(o); commit();
  }

  function floorBelow(p) {
    ray.set(new THREE.Vector3(p.x, p.y + 2, p.z), new THREE.Vector3(0, -1, 0));
    const hit = ray.intersectObjects([house, ...(hood ? [hood.group] : [])], true).filter(h => visibleChain(h.object))[0];
    return hit ? hit.point.y : 0;
  }
  function groundSnap(o) {
    if (o.userData.kind === 'light') { o.position.y = floorBelow(o.position) + (o.userData.head ? 0.12 : 0); return; }
    o.updateMatrixWorld(true);
    const box = new THREE.Box3().setFromObject(o.userData.inner || o, true);
    const c = box.getCenter(new THREE.Vector3());
    ray.set(new THREE.Vector3(c.x, box.max.y + 0.5, c.z), new THREE.Vector3(0, -1, 0));
    const hit = ray.intersectObjects([house, ...(hood ? [hood.group] : [])], true).filter(h => visibleChain(h.object))[0];
    const floor = hit ? hit.point.y : 0;
    o.position.y += floor - box.min.y - (o.userData.bury || 0);
  }

  // ------------------------------------------------------------------ articulator
  const jointGroup = new THREE.Group(); jointGroup.name = 'JointHandles';
  const jointMat = new THREE.MeshBasicMaterial({ color: 0xffd21a, depthTest: false, transparent: true, opacity: 0.85 });
  const jointOn = new THREE.MeshBasicMaterial({ color: 0xff3b2a, depthTest: false });
  function enterPose() {
    const rig = selected.userData.rig;
    poseMode = true; jointSel = null; tc.detach();
    jointGroup.clear();
    const size = Math.max(0.025, new THREE.Box3().setFromObject(selected).getSize(new THREE.Vector3()).length() * 0.012);
    for (const n of rig.order) {
      const b = rig.bones[n];
      const s = new THREE.Mesh(new THREE.SphereGeometry(size, 10, 8), jointMat);
      s.renderOrder = 999; s.userData.bone = b; s.userData.follow = b;
      jointGroup.add(s);
    }
    scene.add(jointGroup);
  }
  function exitPose() { poseMode = false; jointSel = null; if (jointGroup.parent) jointGroup.removeFromParent(); if (selected) tc.attach(selected); }
  function selectJoint(b) {
    jointSel = b;
    jointGroup.children.forEach(s => s.material = s.userData.bone === b ? jointOn : jointMat);
    tc.attach(b); tc.setMode('rotate'); tc.setSpace('local');
    drawInspector();
  }
  function markPosed() { selected.userData.posed = true; selected.userData.posedStamp = (selected.userData.posedStamp || 0) + 1; }
  function setPreset(o, name) {
    const rig = o.userData.rig, kind = catalog[o.userData.id].rig;
    const res = applyPreset(o.userData.inner, rig, kind, name);
    o.userData.bury = res.bury;
    o.userData.inner.rotation.z = res.flip ? Math.PI : 0;
    o.userData.inner.updateMatrixWorld(true);
    o.userData.posed = true;
    o.userData.posedStamp = (o.userData.posedStamp || 0) + 1;
    if (res.snap !== false) groundSnap(o);
    if (poseMode) enterPose();
    commit();
  }

  // ------------------------------------------------------------------ originals on/off
  const hiddenGroups = new Set();
  function setOriginal(group, show) {
    const re = ORIGINAL_GROUPS[group];
    house.traverse(o => { if (re.test(o.name)) o.visible = show; });
    if (show) hiddenGroups.delete(group); else hiddenGroups.add(group);
  }
  function setRedLights(show) {
    for (const l of redLights) l.visible = show;
    if (show) hiddenGroups.delete('Red lights'); else hiddenGroups.add('Red lights');
  }
  function originalsMenu() {
    select(null);
    const groups = [...Object.keys(ORIGINAL_GROUPS), 'Red lights'];
    insp.innerHTML = `<h4>Original 2026 display</h4><div class="muted">Hide the pieces you want to replace.</div>` +
      groups.map(g => `<div class="row">${g}<input type="checkbox" data-g="${g}" ${hiddenGroups.has(g) ? '' : 'checked'}></div>`).join('') +
      `<div class="btns"><button data-x="none">Hide all</button><button data-x="all">Show all</button></div>`;
    insp.querySelectorAll('input[data-g]').forEach(c => c.onchange = () => { c.dataset.g === 'Red lights' ? setRedLights(c.checked) : setOriginal(c.dataset.g, c.checked); commit(); });
    insp.querySelectorAll('button[data-x]').forEach(b => b.onclick = () => {
      groups.forEach(g => g === 'Red lights' ? setRedLights(b.dataset.x === 'all') : setOriginal(g, b.dataset.x === 'all'));
      originalsMenu(); commit(); });
  }

  // ------------------------------------------------------------------ serialize / undo / share
  const r4 = v => +v.toFixed(4);
  function serializeItem(o) {
    const u = o.userData;
    const s = { kind: u.kind, pos: o.position.toArray().map(r4), quat: o.quaternion.toArray().map(r4), scale: o.scale.toArray().map(r4) };
    if (u.kind === 'prop') {
      s.id = u.id;
      if (u.rig && u.posed) s.pose = capturePose(u.rig);
      if (u.inner.rotation.z) s.flip = true;
      if (u.bury) s.bury = u.bury;
    } else {
      Object.assign(s, { lkind: u.lkind, color: u.color, intensity: u.intensity, angle: u.angle, penumbra: u.penumbra,
        effect: u.effect, beam: u.beam, shadow: u.shadow, radius: u.radius });
      if (u.head) s.aim = u.head.quaternion.toArray().map(r4);
    }
    return s;
  }
  async function buildItem(s) {
    let o;
    if (s.kind === 'prop') {
      if (!catalog[s.id]) return null;
      o = await makeProp(s.id);
      if (s.pose && o.userData.rig) { applyPose(o.userData.rig, s.pose); o.userData.posed = true; o.userData.posedStamp = 1; }
      if (s.flip) o.userData.inner.rotation.z = Math.PI;
      o.userData.bury = s.bury || 0;
    } else {
      o = makeLight(s.lkind, s);
      if (s.aim && o.userData.head) o.userData.head.quaternion.fromArray(s.aim);
    }
    o.position.fromArray(s.pos); o.quaternion.fromArray(s.quat); o.scale.fromArray(s.scale);
    return o;
  }
  function serialize() {
    return { v: 1, items: decor.children.map(serializeItem), hidden: [...hiddenGroups] };
  }
  let building = false;
  async function load(state) {
    building = true;
    select(null);
    for (const o of [...decor.children]) { disposeLights(o); o.removeFromParent(); }
    const objs = await Promise.all((state.items || []).map(buildItem));
    objs.forEach(o => o && decor.add(o));
    for (const g of [...Object.keys(ORIGINAL_GROUPS), 'Red lights']) {
      const show = !(state.hidden || []).includes(g);
      g === 'Red lights' ? setRedLights(show) : setOriginal(g, show);
    }
    building = false;
  }
  function commit() {
    if (building) return;
    const s = JSON.stringify(serialize());
    if (undo[undo.length - 1] !== s) { undo.push(s); if (undo.length > 60) undo.shift(); redo.length = 0; }
    try { localStorage.setItem('helloween-layout', s); } catch (e) {}
  }
  async function doUndo() { if (undo.length < 2) return; redo.push(undo.pop()); await load(JSON.parse(undo[undo.length - 1])); persist(); }
  async function doRedo() { if (!redo.length) return; const s = redo.pop(); undo.push(s); await load(JSON.parse(s)); persist(); }
  function persist() { try { localStorage.setItem('helloween-layout', undo[undo.length - 1]); } catch (e) {} }

  async function toB64(str) {
    const cs = new Blob([str]).stream().pipeThrough(new CompressionStream('gzip'));
    const buf = new Uint8Array(await new Response(cs).arrayBuffer());
    let bin = ''; buf.forEach(b => bin += String.fromCharCode(b));
    return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  }
  async function fromB64(s) {
    const bin = atob(s.replace(/-/g, '+').replace(/_/g, '/'));
    const buf = Uint8Array.from(bin, c => c.charCodeAt(0));
    const ds = new Blob([buf]).stream().pipeThrough(new DecompressionStream('gzip'));
    return new Response(ds).text();
  }

  panel.querySelector('.top').addEventListener('click', async e => {
    const a = e.target.dataset.a; if (!a) return;
    if (a === 'undo') doUndo();
    if (a === 'redo') doRedo();
    if (a === 'clear' && confirmClear()) { await load({ items: [], hidden: [] }); commit(); }
    if (a === 'export') {
      const blob = new Blob([JSON.stringify(serialize(), null, 1)], { type: 'application/json' });
      const aEl = document.createElement('a'); aEl.href = URL.createObjectURL(blob); aEl.download = 'helloween-layout.json'; aEl.click();
    }
    if (a === 'import') fileIn.click();
    if (a === 'originals') originalsMenu();
    if (a === 'share') {
      const url = location.origin + location.pathname + '#d=' + await toB64(JSON.stringify(serialize()));
      try { await navigator.clipboard.writeText(url); e.target.textContent = '✓ Link copied'; }
      catch (err) { prompt('Copy this link:', url); }
      setTimeout(() => e.target.textContent = '🔗 Share', 2000);
    }
  });
  const confirmClear = () => { insp.innerHTML = '<span class="muted">Cleared. Undo brings it back.</span>'; return true; };
  fileIn.onchange = async () => { const f = fileIn.files[0]; if (!f) return; await load(JSON.parse(await f.text())); commit(); fileIn.value = ''; };

  // ------------------------------------------------------------------ keys
  addEventListener('keydown', e => {
    if (!document.body.classList.contains('decorating') || /INPUT|SELECT|TEXTAREA/.test(document.activeElement?.tagName)) return;
    const mod = e.metaKey || e.ctrlKey;
    if (mod && e.key.toLowerCase() === 'z') { e.preventDefault(); e.shiftKey ? doRedo() : doUndo(); return; }
    if (e.key === 'Escape') { if (placing) cancelPlace(); else if (poseMode) { exitPose(); drawInspector(); } else select(null); }
    if (!selected) return;
    const k = e.key.toLowerCase();
    if (k === 'w' || k === 'e' || k === 'r') { exitPose(); tc.attach(selected); tc.setMode({ w: 'translate', e: 'rotate', r: 'scale' }[k]); tc.setSpace(k === 'w' ? 'world' : 'local'); drawInspector(); }
    if (k === 'd' && !mod) duplicate();
    if (mod && k === 'd') { e.preventDefault(); duplicate(); }
    if (k === 'g') { groundSnap(selected); commit(); }
    if (k === 'delete' || k === 'backspace') action('del');
  });

  // ------------------------------------------------------------------ per-frame behaviours + effects
  const tmpV = new THREE.Vector3(), clock = new THREE.Clock();
  function update() {
    const t = clock.getElapsedTime();
    if (jointGroup.parent) jointGroup.children.forEach(s => s.userData.follow.getWorldPosition(s.position));
    for (const o of decor.children) {
      const u = o.userData;
      if (u.kind === 'prop') propBehaviours(o, u, t);
      else lightEffects(o, u, t);
    }
    if (lightning && flash) {
      const any = decor.children.some(o => o.userData.lkind === 'lightning');
      if (!any) lightning.intensity = 0;
      else if (t > flash.next) {
        if (t < flash.until) lightning.intensity = 9 * (0.5 + Math.random() * 0.5);
        else if (flash.bursts > 0) { flash.bursts--; flash.until = t + 0.06 + Math.random() * 0.08; flash.next = t + 0.05 + Math.random() * 0.12; lightning.intensity = 0; }
        else { lightning.intensity = 0; flash.next = t + 4 + Math.random() * 9; flash.bursts = 2 + Math.floor(Math.random() * 3); flash.until = flash.next + 0.08; }
      } else lightning.intensity = 0;
    }
  }
  function propBehaviours(o, u, t) {
    const b = u.behaviors, ph = (u.uid * 1.37) % 6.28;
    const inner = u.inner;
    if (b.includes('bob')) { inner.position.y = 0.15 + 0.12 * Math.sin(t * 1.3 + ph); inner.rotation.z = 0.06 * Math.sin(t * 0.9 + ph); }
    if (b.includes('swing')) inner.rotation.z = 0.05 * Math.sin(t * 1.1 + ph);
    if (b.includes('pulse') || b.includes('flicker')) {
      const k = b.includes('flicker') ? 0.75 + 0.25 * Math.sin(t * 13 + ph) * Math.sin(t * 7.3) + 0.1 * Math.random() : 0.65 + 0.35 * Math.sin(t * 2.2 + ph);
      if (u.propLight) u.propLight.intensity = u.baseIntensity * k;
      inner.traverse(m => { if (m.userData.emit0) m.material.emissiveIntensity = m.userData.emit0 * k; });
    }
    if (b.includes('eyes_follow') && u.named.Eye) for (const e of u.named.Eye) { e.lookAt(camera.position); e.rotateY(Math.PI); }
    if (b.includes('creak') && u.named.Lid) u.named.Lid[0].rotation.y = -0.6 + 0.45 * Math.sin(t * 0.5 + ph);
    if (b.includes('flap') && u.named.Wing) u.named.Wing.forEach((w, i) => w.rotation.z = (w.name.includes('_L') ? 1 : -1) * 0.7 * Math.sin(t * 14 + i));
    if (b.includes('flutter') && u.named.Wing) u.named.Wing.forEach(w => w.rotation.z = (w.name.includes('_L') ? 1 : -1) * 0.5 * (0.5 + 0.5 * Math.sin(t * 1.6 + ph)));
    if (b.includes('orbit') && u.named.Bat) inner.rotation.y = t * 0.6 + ph;
    if (b.includes('peck') && u.named.Head) { const s = Math.floor(t * 1.4 + ph); u.named.Head[0].rotation.y = Math.sin(s * 12.9898) * 0.9; }
    if (b.includes('sway') && u.rig && !poseMode) {
      for (const n of u.rig.order) {
        const bn = u.rig.bones[n];
        if (!bn.userData.swayBase || u.posedStamp !== bn.userData.stamp) { bn.userData.swayBase = bn.quaternion.clone(); bn.userData.stamp = u.posedStamp; }
        const i = +n.split('_')[1] || 0;
        bn.quaternion.copy(bn.userData.swayBase).multiply(new THREE.Quaternion().setFromEuler(new THREE.Euler(0.05 * Math.sin(t * 1.2 + i * 0.6 + ph), 0, 0.05 * Math.cos(t * 0.9 + i * 0.5 + ph))));
      }
    }
  }
  function lightEffects(o, u, t) {
    const L = u.light; if (!L && !u.lkind) return;
    const ph = (u.uid * 2.1) % 6.28;
    if (u.lkind === 'fog') { o.children.forEach(g => g.name === 'FogPatch' && g.children.forEach(s => { if (s.isSprite) { s.position.x += Math.sin(t * 0.2 + s.userData.phase) * 0.002; s.material.opacity = 0.22 + 0.1 * Math.sin(t * 0.5 + s.userData.phase); } })); return; }
    if (!L) return;
    let k = 1, col = null;
    switch (u.effect) {
      case 'flicker': k = 0.7 + 0.2 * Math.sin(t * 11 + ph) * Math.sin(t * 6.7) + 0.15 * Math.random(); break;
      case 'pulse': k = 0.55 + 0.45 * Math.sin(t * 2 + ph); break;
      case 'strobe': k = (Math.floor(t * 9 + ph) % 2) ? 1 : 0; break;
      case 'cycle': col = new THREE.Color().setHSL((t * 0.05 + ph) % 1, 1, 0.5); break;
      case 'sweep': if (u.head) { u.head.rotation.y = 0.9 * Math.sin(t * 0.35 + ph); } break;
    }
    L.intensity = u.intensity * k;
    if (col) { L.color.copy(col); u.lensMat.emissive.copy(col); if (u.cone) u.cone.material.uniforms.color.value.copy(col); }
    if (u.lensMat && !col) u.lensMat.emissiveIntensity = 2 * k;
    if (u.flame) u.flame.scale.y = 0.8 + 0.3 * k;
  }

  // ------------------------------------------------------------------ boot
  const ready = (async () => {
    await loadCatalog();
    let state = null;
    const m = location.hash.match(/#d=([\w-]+)/);
    if (m) { try { state = JSON.parse(await fromB64(m[1])); } catch (e) { console.warn('bad share link', e); } }
    if (!state) { try { state = JSON.parse(localStorage.getItem('helloween-layout') || 'null'); } catch (e) {} }
    if (state) await load(state);
    commit();
    if (m) setDecorating(false);
  })();

  return { update, ready, setDecorating, get decorating() { return document.body.classList.contains('decorating'); },
           exitForWalk: () => { setDecorating(false); }, decor };
}

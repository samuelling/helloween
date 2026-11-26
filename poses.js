// Articulation helpers + pose presets for the rigged props.
// Directions are written in Blender's armature frame (x right, -y = facing, z up) and converted here.
import * as THREE from 'three';

const B2T = (d) => new THREE.Vector3(d[0], d[2], -d[1]);   // Blender -> three (root-local)

// ---------------------------------------------------------------- core ops
export function initRig(root, boneDefs) {
  // call on a fresh clone at the origin (rest pose): remembers each bone's tail in its own space
  const bones = {};
  root.updateMatrixWorld(true);
  root.traverse(o => { if (o.isBone) bones[o.name] = o; });
  const defs = {};
  for (const d of boneDefs) {
    const b = bones[d.n]; if (!b) continue;
    b.userData.rest = b.quaternion.clone();
    b.userData.tailLocal = b.worldToLocal(new THREE.Vector3(...d.t));
    defs[d.n] = d;
  }
  return { bones, order: boneDefs.map(d => d.n).filter(n => bones[n]), defs };
}

export function resetPose(rig) {
  for (const n of rig.order) rig.bones[n].quaternion.copy(rig.bones[n].userData.rest);
}

function boneDir(b) {
  b.updateWorldMatrix(true, false);
  const h = new THREE.Vector3().setFromMatrixPosition(b.matrixWorld);
  return b.localToWorld(b.userData.tailLocal.clone()).sub(h).normalize();
}

export function aimBone(root, bone, dirRoot) {
  const rq = root.getWorldQuaternion(new THREE.Quaternion());
  const want = dirRoot.clone().normalize().applyQuaternion(rq);
  const cur = boneDir(bone);
  const q = new THREE.Quaternion().setFromUnitVectors(cur, want);
  const bw = bone.getWorldQuaternion(new THREE.Quaternion());
  const pw = bone.parent.getWorldQuaternion(new THREE.Quaternion());
  bone.quaternion.copy(pw.invert().multiply(q.multiply(bw)));
  bone.updateMatrixWorld(true);
}

export function rotateBoneRootAxis(root, bone, axisRoot, angle) {
  const rq = root.getWorldQuaternion(new THREE.Quaternion());
  const axisW = axisRoot.clone().normalize().applyQuaternion(rq);
  const pw = bone.parent.getWorldQuaternion(new THREE.Quaternion());
  const local = axisW.applyQuaternion(pw.invert());
  bone.quaternion.premultiply(new THREE.Quaternion().setFromAxisAngle(local, angle));
  bone.updateMatrixWorld(true);
}

export function capturePose(rig) {
  const out = {};
  for (const n of rig.order) {
    const b = rig.bones[n];
    if (b.quaternion.angleTo(b.userData.rest) > 1e-4) out[n] = b.quaternion.toArray().map(v => +v.toFixed(5));
  }
  return out;
}
export function applyPose(rig, pose) {
  resetPose(rig);
  for (const [n, q] of Object.entries(pose || {})) if (rig.bones[n]) rig.bones[n].quaternion.fromArray(q);
}

// ---------------------------------------------------------------- presets
const HUMAN = {
  'Stand': {},
  'Crawl (cobra)': {
    pelvis: [0, -1, 0.12], spine: [0, -0.9, 0.45], chest: [0, -0.55, 0.85], neck: [0, -0.4, 0.92], head: [0, -0.1, 1],
    upper_armL: [0.18, -0.25, -1], forearmL: [0.06, -0.35, -1], handL: [0.04, -1, -0.15],
    thighL: [0.12, 1, -0.1], shinL: [0.05, 1, 0.15], footL: [0, 0.35, -1] },
  'Emerging from grave': {
    pelvis: [0, -0.75, 0.65], spine: [0, -0.85, 0.5], chest: [0, -0.75, 0.62], neck: [0, -0.55, 0.85], head: [0, -0.15, 1],
    upper_armL: [0.18, -1, -0.35], forearmL: [0.05, -1, -0.35], handL: [0, -1, -0.6],
    upper_armR: [-0.3, -0.5, -1], forearmR: [-0.1, -0.9, -0.5],
    thighL: [0.15, 0.2, -1], shinL: [0, 1, -0.3], footL: [0, 0.3, -1], _bury: 0.35 },
  'Kneel & bow': {
    pelvis: [0, -0.3, 1], spine: [0, -0.75, 0.66], chest: [0, -0.95, 0.35], neck: [0, -0.98, 0], head: [0, -0.55, -0.85],
    upper_armL: [0.18, -0.45, -1], forearmL: [0.05, -0.7, -0.75], handL: [0, -0.9, -0.5],
    thighL: [0.15, -1, -0.28], shinL: [0, 1, -0.06], footL: [0, 1, -0.25] },
  'Kneel & reach': {
    pelvis: [0, 0, 1], spine: [0, -0.2, 1], chest: [0, -0.35, 1], neck: [0, -0.35, 1], head: [0, -0.05, 1],
    upper_armL: [0.15, -0.85, -0.5], forearmL: [0.02, -0.95, -0.3], handL: [0, -0.9, -0.45],
    upper_armR: [-0.1, -0.6, -0.8], forearmR: [0.1, -1, -0.1],
    thighL: [0.06, -0.12, -1], shinL: [0, 1, -0.04], footL: [0, 1, -0.3] },
  'Sit in chair': {
    pelvis: [0, 0.25, 1], spine: [0, 0.12, 1], chest: [0, 0.02, 1], neck: [0.05, -0.12, 1], head: [0.35, -0.2, 1],
    upper_armL: [0.3, 0.12, -1], forearmL: [0.08, -1, -0.12], handL: [0.03, -1, -0.4],
    thighL: [0.12, -1, 0.06], shinL: [0.03, -0.12, -1], footL: [0, -1, -0.3], _snap: false },
  'Sit on ground': {
    pelvis: [0, 0.35, 1], spine: [0, -0.15, 1], chest: [0, -0.55, 0.85], neck: [0, -0.5, 0.86], head: [0, -0.2, 1],
    upper_armL: [0.25, -1, -0.45], forearmL: [0.02, -1, -0.2], handL: [0, -1, -0.3],
    upper_armR: [-0.45, -0.25, -1], forearmR: [-0.25, -0.65, -0.8], handR: [0, -1, -0.6],
    thighL: [0.3, -1, 0.5], shinL: [0.05, -0.35, -1], footL: [0, -1, -0.25],
    thighR: [-0.35, -1, 0.15], shinR: [0.05, -0.75, -0.65], footR: [0, -1, -0.2] },
  'Zombie walk': {
    spine: [0, -0.15, 1], chest: [0, -0.2, 1], neck: [0.1, -0.35, 0.9], head: [0.3, -0.3, 0.9],
    upper_armL: [0.08, -1, 0.05], forearmL: [0.02, -1, -0.1], handL: [0, -1, -0.3],
    upper_armR: [-0.1, -1, -0.1], forearmR: [0, -1, 0.05],
    thighL: [0.05, -0.35, -1], shinL: [0, 0.1, -1], thighR: [-0.05, 0.25, -1], shinR: [0, 0.3, -1] },
  'Wave hello': {
    head: [-0.2, -0.1, 1], upper_armR: [-0.8, -0.1, 0.55], forearmR: [-0.15, -0.15, 1], handR: [-0.1, -0.2, 1],
    upper_armL: [0.15, 0, -1], forearmL: [0.1, -0.3, -1] },
  'Dance': {
    pelvis: [0.15, 0, 1], spine: [-0.15, -0.05, 1], chest: [-0.2, 0, 1], head: [0.3, -0.1, 1],
    upper_armL: [0.8, 0, 0.6], forearmL: [0.2, 0, 1], upper_armR: [-0.9, -0.2, -0.3], forearmR: [-0.3, -0.6, 0.7],
    thighL: [0.35, -0.3, -1], shinL: [0.1, 0.5, -1], thighR: [-0.05, 0, -1] },
  'Lie flat': {
    pelvis: [0, -1, 0.02], spine: [0, -1, 0.02], chest: [0, -1, 0.02], neck: [0, -1, 0.05], head: [0, -1, 0.1],
    upper_armL: [0.5, -0.2, -0.2], forearmL: [0.4, -0.8, 0], thighL: [0.1, 1, -0.05], shinL: [0.05, 1, 0], footL: [0, 0.4, -1] },
};

const DOG = {
  'Stand': {},
  'Sit': { hips: [0, -0.5, 0.85], spine: [0, -0.45, 0.9], chest: [0, -0.4, 0.92], neck: [0, -0.3, 0.95], head: [0, -1, 0.1],
    hind_upperL: [0.1, -0.95, -0.1], hind_lowerL: [0, 0.9, -0.35], hind_pawL: [0, -1, -0.2],
    front_upperL: [0, -0.1, -1], front_lowerL: [0, 0, -1], front_pawL: [0, -1, -0.3],
    tail1: [0, 1, -0.5], tail2: [0, 1, -0.1], tail3: [0.3, 1, 0] },
  'Howl': { hips: [0, -0.5, 0.85], spine: [0, -0.45, 0.9], chest: [0, -0.4, 0.92], neck: [0, -0.1, 1], head: [0, -0.45, 0.9],
    hind_upperL: [0.1, -0.95, -0.1], hind_lowerL: [0, 0.9, -0.35], hind_pawL: [0, -1, -0.2],
    front_upperL: [0, -0.1, -1], front_lowerL: [0, 0, -1], front_pawL: [0, -1, -0.3], tail1: [0, 1, -0.5] },
  'Play bow': { spine: [0, -1, -0.3], chest: [0, -1, -0.3], neck: [0, -1, 0.35], head: [0, -1, 0.05],
    front_upperL: [0, -1, -0.45], front_lowerL: [0, -1, -0.08], front_pawL: [0, -1, -0.2],
    tail1: [0, 0.5, 0.9], tail2: [0, 0.3, 1], tail3: [0, -0.2, 1] },
  'Prowl': { spine: [0, -1, 0.05], chest: [0, -1, -0.05], neck: [0, -1, 0.1], head: [0, -1, -0.15],
    front_upperL: [0, -0.3, -1], front_lowerL: [0, 0.3, -1], front_upperR: [0, 0.3, -1], front_lowerR: [0, -0.2, -1],
    hind_upperL: [0, 0.3, -1], tail1: [0, 1, -0.2], tail2: [0, 1, -0.3], tail3: [0, 1, -0.5] },
};

// procedural presets for spiders and bone chains
function legOut(rig, leg) {
  const a = rig.defs[leg + '_a'], c = rig.defs[leg + '_c'];
  const v = new THREE.Vector3(c.t[0] - a.h[0], 0, c.t[2] - a.h[2]).normalize();
  return [v.x, -v.z];   // back to Blender-ish (x, y)
}
function spiderPose(rig, kind) {
  const P = {};
  const legs = [...new Set(rig.order.filter(n => n.startsWith('leg')).map(n => n.slice(0, -2)))];
  for (const leg of legs) {
    const [ox, oy] = legOut(rig, leg);
    const front = leg.startsWith('leg0');
    if (kind === 'Crouch') { P[leg + '_a'] = [ox * 0.5, oy * 0.5, 0.9]; P[leg + '_b'] = [ox, oy, -0.15]; P[leg + '_c'] = [ox * 0.3, oy * 0.3, -1]; }
    if (kind === 'Rear up' && front) { P[leg + '_a'] = [ox * 0.3, -0.5, 0.9]; P[leg + '_b'] = [ox * 0.4, -0.6, 0.7]; P[leg + '_c'] = [ox * 0.2, -1, 0.1]; }
    if (kind === 'Curled (dead)') { P[leg + '_a'] = [ox * 0.4, oy * 0.4, 1]; P[leg + '_b'] = [-ox * 0.5, -oy * 0.5, 0.6]; P[leg + '_c'] = [-ox, -oy, -0.2]; }
    if (kind === 'Pounce' && (front || leg.startsWith('leg1'))) { P[leg + '_a'] = [ox * 0.4, -0.9, 0.5]; P[leg + '_b'] = [ox * 0.3, -1, 0.1]; P[leg + '_c'] = [ox * 0.1, -1, -0.5]; }
  }
  if (kind === 'Rear up') P.body = [0, -1, 0.45];
  if (kind === 'Curled (dead)') P._flip = true;
  return P;
}

function chains(rig) {
  const map = {};
  for (const n of rig.order) {
    const m = n.match(/^(t\d+)_\d+$/) || (n.startsWith('seg') || n === 'head' ? ['', 'serpent'] : null);
    if (!m) continue;
    (map[m[1]] ||= []).push(n);
  }
  return Object.values(map);
}

const CHAIN_PRESETS = ['Straight', 'S-curve', 'Coil', 'Rear up', 'Curl over'];
function applyChain(root, rig, kind) {
  resetPose(rig);
  const up = new THREE.Vector3(0, 1, 0), side = new THREE.Vector3(1, 0, 0);
  chains(rig).forEach((ch, ci) => {
    const serp = ch[0].startsWith('seg');
    ch.forEach((n, i) => {
      const b = rig.bones[n], f = i / ch.length;
      if (kind === 'S-curve') rotateBoneRootAxis(root, b, serp ? up : side, (serp ? 0.55 : 0.25) * Math.sin(i * 0.9 + ci));
      if (kind === 'Coil') rotateBoneRootAxis(root, b, serp ? up : side, serp ? 0.5 + 0.02 * i : 0.32);
      if (kind === 'Rear up') { if (!serp || i > ch.length - 7) rotateBoneRootAxis(root, b, side, serp ? -0.28 : 0.12); }
      if (kind === 'Curl over') rotateBoneRootAxis(root, b, side, serp ? (i > ch.length - 8 ? -0.45 : 0) : 0.38 * f + 0.05);
    });
  });
}

export function presetsFor(rigKind) {
  if (rigKind === 'human') return Object.keys(HUMAN);
  if (rigKind === 'dog') return Object.keys(DOG);
  if (rigKind === 'spider') return ['Stand', 'Crouch', 'Rear up', 'Pounce', 'Curled (dead)'];
  return CHAIN_PRESETS;
}

export function applyPreset(root, rig, rigKind, name) {
  if (rigKind === 'chain') { applyChain(root, rig, name); return {}; }
  let P = rigKind === 'human' ? HUMAN[name] : rigKind === 'dog' ? DOG[name] : (name === 'Stand' ? {} : spiderPose(rig, name));
  P = { ...P };
  for (const [k, d] of Object.entries(P)) {   // mirror .L -> .R when not given
    if (k.endsWith('L') && /(arm|hand|thigh|shin|foot|upper|lower|paw)L$/.test(k)) {
      const r = k.slice(0, -1) + 'R';
      if (!(r in P)) P[r] = [-d[0], d[1], d[2]];
    }
  }
  resetPose(rig);
  root.updateMatrixWorld(true);
  for (const n of rig.order) if (P[n]) aimBone(root, rig.bones[n], B2T(P[n]));
  return { bury: P._bury || 0, snap: P._snap !== false, flip: !!P._flip };
}

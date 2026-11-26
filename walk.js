// First-person walking for the Helloween scene: WASD + mouse look (pointer lock), touch sticks on phones,
// BVH-accelerated collision so you can climb the porch steps, bump into skeletons and not walk through walls.
import * as THREE from 'three';
import { PointerLockControls } from 'three/addons/controls/PointerLockControls.js';
import { computeBoundsTree, disposeBoundsTree, acceleratedRaycast } from 'https://cdn.jsdelivr.net/npm/three-mesh-bvh@0.8.3/build/index.module.js';

THREE.BufferGeometry.prototype.computeBoundsTree = computeBoundsTree;
THREE.BufferGeometry.prototype.disposeBoundsTree = disposeBoundsTree;
THREE.Mesh.prototype.raycast = acceleratedRaycast;

const EYE = 1.62, RADIUS = 0.28, STEP_UP = 0.42, WALK = 2.0, RUN = 4.5, GRAV = 18, JUMP = 5.2;
const NO_COLLIDE = /Leaves|String_Lights|Flame|Hanger|Twine|Antlers|Hanging_Baskets|Ghost|Lawn/i;

export function initWalk({ scene, camera, renderer, orbit, root, ui }) {
  // ---- collision set (static meshes, world-space BVH)
  const colliders = [];
  root.updateMatrixWorld(true);
  root.traverse(o => {
    if (!o.isMesh || NO_COLLIDE.test(o.name) || NO_COLLIDE.test(o.parent?.name || '')) return;
    o.geometry.computeBoundsTree({ maxLeafTris: 8 });
    colliders.push(o);
  });
  const ground = root.getObjectByName('Lawn');
  const floorSet = ground ? [...colliders, ground] : colliders;
  if (ground) ground.geometry.computeBoundsTree();

  const ray = new THREE.Raycaster();
  ray.firstHitOnly = true;
  const plc = new PointerLockControls(camera, renderer.domElement);
  const state = { on: false, vel: new THREE.Vector3(), vy: 0, feet: new THREE.Vector3(), keys: {}, grounded: true,
                  touchMove: new THREE.Vector2(), torch: null };

  // flashlight (F)
  const torch = new THREE.SpotLight(0xffd7a0, 0, 18, 0.45, 0.6, 2);
  torch.position.set(0, 0, 0); torch.target.position.set(0, 0, -1);
  camera.add(torch); camera.add(torch.target);
  if (!camera.parent) scene.add(camera);

  function floorAt(p, from = 1.0) {
    ray.set(new THREE.Vector3(p.x, p.y + from, p.z), new THREE.Vector3(0, -1, 0));
    ray.far = from + 3;
    const h = ray.intersectObjects(floorSet, false)[0];
    return h ? h.point.y : -Infinity;
  }

  function blocked(p, dir, dist) {
    // three horizontal probes: ankle (above step height), waist, head
    for (const y of [STEP_UP + 0.05, 0.95, 1.55]) {
      ray.set(new THREE.Vector3(p.x, p.y + y, p.z), dir);
      ray.far = dist + RADIUS;
      const h = ray.intersectObjects(colliders, false)[0];
      if (h) return h;
    }
    return null;
  }

  function enter(spawn) {
    state.on = true; orbit.enabled = false;
    const s = spawn || { pos: [1.4, 0, 9.3], look: [0.8, 2.6, 0] };
    state.feet.set(s.pos[0], 0, s.pos[2]);
    state.feet.y = Math.max(0, floorAt(state.feet, 2));
    camera.position.copy(state.feet).add(new THREE.Vector3(0, EYE, 0));
    camera.lookAt(...s.look);
    camera.fov = 70; camera.updateProjectionMatrix();
    if (!matchMedia('(pointer: coarse)').matches) plc.lock();
    ui.onWalk?.(true);
  }
  function exit() {
    state.on = false; orbit.enabled = true;
    orbit.target.copy(camera.position).add(camera.getWorldDirection(new THREE.Vector3()).multiplyScalar(4));
    if (plc.isLocked) plc.unlock();
    ui.onWalk?.(false);
  }
  plc.addEventListener('unlock', () => { if (state.on && !matchMedia('(pointer: coarse)').matches) ui.onPaused?.(); });

  addEventListener('keydown', e => {
    state.keys[e.code] = true;
    if (!state.on) return;
    if (e.code === 'KeyF') torch.intensity = torch.intensity ? 0 : 60;
    if (e.code === 'Space' && state.grounded) { state.vy = JUMP; state.grounded = false; }
  });
  addEventListener('keyup', e => { state.keys[e.code] = false; });

  // ---- touch: left half = move stick, right half = look
  const touches = new Map();
  const el = renderer.domElement;
  el.addEventListener('touchstart', e => {
    if (!state.on) return;
    for (const t of e.changedTouches) touches.set(t.identifier, { x0: t.clientX, y0: t.clientY, x: t.clientX, y: t.clientY,
      left: t.clientX < innerWidth / 2 });
  }, { passive: true });
  el.addEventListener('touchmove', e => {
    if (!state.on) return;
    for (const t of e.changedTouches) {
      const s = touches.get(t.identifier); if (!s) continue;
      if (s.left) state.touchMove.set((t.clientX - s.x0) / 60, (t.clientY - s.y0) / 60).clampLength(0, 1);
      else {
        const e2 = new THREE.Euler().setFromQuaternion(camera.quaternion, 'YXZ');
        e2.y -= (t.clientX - s.x) * 0.005; e2.x = THREE.MathUtils.clamp(e2.x - (t.clientY - s.y) * 0.005, -1.4, 1.4);
        camera.quaternion.setFromEuler(e2);
      }
      s.x = t.clientX; s.y = t.clientY;
    }
  }, { passive: true });
  el.addEventListener('touchend', e => {
    for (const t of e.changedTouches) { const s = touches.get(t.identifier); if (s?.left) state.touchMove.set(0, 0); touches.delete(t.identifier); }
  });

  const fwd = new THREE.Vector3(), right = new THREE.Vector3(), up = new THREE.Vector3(0, 1, 0);
  function update(dt) {
    if (!state.on) return;
    dt = Math.min(dt, 0.05);
    const k = state.keys;
    let mx = (k.KeyD || k.ArrowRight ? 1 : 0) - (k.KeyA || k.ArrowLeft ? 1 : 0) + state.touchMove.x;
    let mz = (k.KeyW || k.ArrowUp ? 1 : 0) - (k.KeyS || k.ArrowDown ? 1 : 0) - state.touchMove.y;
    const speed = (k.ShiftLeft || k.ShiftRight) ? RUN : WALK;
    camera.getWorldDirection(fwd); fwd.y = 0; fwd.normalize();
    right.crossVectors(fwd, up).normalize();
    const want = new THREE.Vector3().addScaledVector(fwd, mz).addScaledVector(right, mx);
    if (want.lengthSq() > 1) want.normalize();
    want.multiplyScalar(speed);
    state.vel.lerp(want, 1 - Math.exp(-12 * dt));

    // horizontal move with wall sliding (two passes)
    let step = state.vel.clone().multiplyScalar(dt);
    for (let pass = 0; pass < 2 && step.lengthSq() > 1e-8; pass++) {
      const len = step.length(), dir = step.clone().divideScalar(len);
      const hit = blocked(state.feet, dir, len);
      if (!hit) { state.feet.add(step); break; }
      const n = hit.face ? hit.face.normal.clone().transformDirection(hit.object.matrixWorld) : dir.clone().negate();
      n.y = 0; n.normalize();
      const allowed = Math.max(0, hit.distance - RADIUS);
      state.feet.addScaledVector(dir, allowed);
      step.addScaledVector(dir, -allowed);
      step.addScaledVector(n, -step.dot(n));       // slide along the wall
    }
    // keep inside the neighbourhood
    state.feet.x = THREE.MathUtils.clamp(state.feet.x, -38, 38);
    state.feet.z = THREE.MathUtils.clamp(state.feet.z, -38, 30);

    // vertical: step up onto stairs, fall with gravity
    const floor = floorAt(state.feet, STEP_UP + 0.05);
    state.vy -= GRAV * dt;
    state.feet.y += state.vy * dt;
    if (state.feet.y <= floor + 0.001) { state.feet.y = floor; state.vy = 0; state.grounded = true; }
    else if (state.feet.y - floor < 0.06 && state.vy <= 0) { state.feet.y = floor; state.vy = 0; state.grounded = true; }
    else state.grounded = false;
    if (!isFinite(state.feet.y)) state.feet.y = 0;

    const bob = state.grounded ? Math.sin(performance.now() / 160) * 0.025 * (state.vel.length() / RUN) : 0;
    camera.position.set(state.feet.x, state.feet.y + EYE + bob, state.feet.z);
  }

  return { enter, exit, update, get on() { return state.on; }, lock: () => plc.lock(), torch };
}

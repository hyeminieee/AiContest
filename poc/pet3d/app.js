// REFLEX 펫 (three.js): 선택·학습은 local_engine.js(파이썬 engine.py를 옮긴 것)가 계산하고, 이 파일은 그 결과를 3D로 보여준다.
// 이동·쓰다듬기 같은 장면은 화면 표현이며 학습에 영향을 주지 않는다.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

const L = window.ReflexLocal, G = L.Genetics, D = window.REFLEX_DATA;
const $ = (id) => document.getElementById(id);
const N0 = D.defaults.initial_trials, N1 = D.defaults.reversal_trials;

// ---------------------------------------------------------------- 장면
const canvas = $("scene");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(32, 1, 0.1, 100);
camera.position.set(5.6, 4.9, 6.6);
const controls = new OrbitControls(camera, canvas);
controls.target.set(1.0, 0.45, 0);
controls.enableDamping = true;
controls.minDistance = 5.5; controls.maxDistance = 16;
controls.minPolarAngle = 0.5; controls.maxPolarAngle = 1.25;
controls.enablePan = false;

scene.add(new THREE.HemisphereLight(0xfff3e8, 0xd2a991, 1.15));
const sun = new THREE.DirectionalLight(0xfff0dc, 2.1);
sun.position.set(5, 9, 4);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
Object.assign(sun.shadow.camera, { left: -7, right: 7, top: 7, bottom: -7 });
sun.shadow.radius = 4;
scene.add(sun);

const mat = (color, extra = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.82, metalness: 0, flatShading: true, ...extra });
const mesh = (geo, m, { cast = true, receive = true } = {}) => { const o = new THREE.Mesh(geo, m); o.castShadow = cast; o.receiveShadow = receive; return o; };

function buildRoom() {
  const g = new THREE.Group();
  const base = mesh(new THREE.BoxGeometry(9, 0.6, 9), mat(0xd9a982));
  base.position.y = -0.3; g.add(base);
  const floor = mesh(new THREE.BoxGeometry(8.6, 0.06, 8.6), mat(0xf1d9b5));
  floor.position.y = 0.03; g.add(floor);
  for (let i = -4; i <= 4; i++) { // 마루 줄무늬
    const s = mesh(new THREE.BoxGeometry(8.6, 0.005, 0.02), mat(0xe2c39a), { cast: false });
    s.position.set(0, 0.065, i * 0.95); g.add(s);
  }
  const rug = mesh(new THREE.CylinderGeometry(2.0, 2.0, 0.04, 40), mat(0xf6c1b4));
  rug.position.set(0.8, 0.08, 0); g.add(rug);
  const rug2 = mesh(new THREE.CylinderGeometry(1.55, 1.55, 0.045, 40), mat(0xfad7cc));
  rug2.position.set(0.8, 0.085, 0); g.add(rug2);
  const wallM = mat(0xfbeee2);
  const back = mesh(new THREE.BoxGeometry(0.3, 2.6, 9), wallM); back.position.set(-4.35, 1.3, 0); g.add(back);
  const side = mesh(new THREE.BoxGeometry(9, 2.6, 0.3), wallM); side.position.set(0, 1.3, -4.35); g.add(side);
  const trim = mat(0xe8b9a0);
  const t1 = mesh(new THREE.BoxGeometry(0.34, 0.18, 9), trim); t1.position.set(-4.35, 0.09, 0); g.add(t1);
  const t2 = mesh(new THREE.BoxGeometry(9, 0.18, 0.34), trim); t2.position.set(0, 0.09, -4.35); g.add(t2);
  // 창문
  const frame = mesh(new THREE.BoxGeometry(0.12, 1.2, 1.7), mat(0xffffff)); frame.position.set(-4.18, 1.55, -1.2); g.add(frame);
  const glass = mesh(new THREE.BoxGeometry(0.13, 1.0, 1.5), mat(0xbfe3f2, { roughness: 0.3, emissive: 0x9ccfe6, emissiveIntensity: 0.25 }), { cast: false });
  glass.position.set(-4.17, 1.55, -1.2); g.add(glass);
  const bar = mesh(new THREE.BoxGeometry(0.14, 1.0, 0.06), mat(0xffffff)); bar.position.set(-4.16, 1.55, -1.2); g.add(bar);
  // 액자: 초파리 회로 그림
  const art = mesh(new THREE.BoxGeometry(1.3, 0.9, 0.08), mat(0xffffff)); art.position.set(1.4, 1.65, -4.18); g.add(art);
  const artIn = mesh(new THREE.BoxGeometry(1.12, 0.72, 0.09), mat(0x2f3e55)); artIn.position.set(1.4, 1.65, -4.17); g.add(artIn);
  for (let i = 0; i < 14; i++) {
    const d = mesh(new THREE.SphereGeometry(0.03, 8, 6), mat(i % 3 ? 0x7fd1b9 : 0xf3a86b, { emissive: 0x335544, emissiveIntensity: 0.4 }), { cast: false });
    d.position.set(1.4 + Math.sin(i * 2.3) * 0.45, 1.65 + Math.cos(i * 1.7) * 0.27, -4.12); g.add(d);
  }
  // 화분
  const plant = (x, z, s) => {
    const p = new THREE.Group();
    const pot = mesh(new THREE.CylinderGeometry(0.28, 0.22, 0.42, 10), mat(0xd77f62)); pot.position.y = 0.21; p.add(pot);
    for (let i = 0; i < 5; i++) {
      const lf = mesh(new THREE.IcosahedronGeometry(0.26, 0), mat(i % 2 ? 0x7fbf7a : 0x6aae6a));
      lf.position.set(Math.cos(i * 1.3) * 0.16, 0.62 + (i % 3) * 0.14, Math.sin(i * 1.3) * 0.16); lf.scale.set(0.8, 1.15, 0.8); p.add(lf);
    }
    p.position.set(x, 0.06, z); p.scale.setScalar(s); g.add(p);
  };
  plant(-3.6, -3.6, 1.15); plant(3.6, -3.7, 0.9);
  // 둥지(침대)
  const bed = new THREE.Group();
  const ring = mesh(new THREE.TorusGeometry(0.62, 0.2, 10, 24), mat(0xc58b5e)); ring.rotation.x = Math.PI / 2; ring.position.y = 0.2; bed.add(ring);
  const cush = mesh(new THREE.CylinderGeometry(0.55, 0.55, 0.14, 24), mat(0xfff4e6)); cush.position.y = 0.12; bed.add(cush);
  bed.position.set(-2.6, 0.06, 2.6); g.add(bed);
  // 공·블록 상자
  const box = mesh(new THREE.BoxGeometry(0.9, 0.6, 0.6), mat(0xa7c4e8)); box.position.set(-3.5, 0.36, 1.0); g.add(box);
  return g;
}
scene.add(buildRoom());

// ---------------------------------------------------------------- 글자 스프라이트
function labelSprite(text, { bg = "#ffffff", fg = "#3b2a22", size = 64, pad = 22, scale = 0.0042 } = {}) {
  const c = document.createElement("canvas"), x = c.getContext("2d");
  x.font = `800 ${size}px "Malgun Gothic", sans-serif`;
  const w = Math.ceil(x.measureText(text).width) + pad * 2, h = size + pad * 1.4;
  c.width = w; c.height = h;
  x.font = `800 ${size}px "Malgun Gothic", sans-serif`;
  x.fillStyle = bg; x.beginPath(); x.roundRect(0, 0, w, h, h / 2.4); x.fill();
  x.fillStyle = fg; x.textBaseline = "middle"; x.textAlign = "center"; x.fillText(text, w / 2, h / 2 + 3);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: t, depthTest: false, transparent: true }));
  s.scale.set(w * scale, h * scale, 1); s.renderOrder = 10;
  return s;
}
const emojiSprite = (ch, px = 0.42, fg = "#ff6b81") => labelSprite(ch, { bg: "rgba(0,0,0,0)", fg, size: 96, pad: 6, scale: px / 110 });

// ---------------------------------------------------------------- 펫 (팀이 만든 모델. 구매 에셋 원본 아님)
const TRAIT_COLOR = { g_apl: { high: 0x5a8fd6, low: 0xf08a4b }, decay: { high: 0xf2c14e, low: 0xc7ced6 } };
// 동물 모습은 꾸미기일 뿐이다. 모든 펫이 같은 초파리 회로를 쓰고, 성향 코드에도 들어가지 않는다.
const SPECIES = { pig: { name: "새끼돼지", emoji: "🐷" }, calf: { name: "송아지", emoji: "🐮" }, chick: { name: "병아리", emoji: "🐥" }, puppy: { name: "강아지", emoji: "🐶" } };
const ico = (r, d = 2) => new THREE.IcosahedronGeometry(r, d);
const BLACK = () => mat(0x2a1f1c, { roughness: 0.3, flatShading: false });
function addEyes(head, x, y, z, r = 0.046) {
  for (const s of [-1, 1]) {
    const e = mesh(new THREE.SphereGeometry(r, 12, 10), BLACK()); e.position.set(x, y, z * s); head.add(e);
    const hl = mesh(new THREE.SphereGeometry(r * 0.3, 6, 6), new THREE.MeshBasicMaterial({ color: 0xffffff }), { cast: false });
    hl.position.set(x + r * 0.75, y + r * 0.45, z * s * 0.92); head.add(hl);
  }
}
function addCheeks(head, x, y, z, color = 0xff8aa0) {
  for (const s of [-1, 1]) {
    const c = mesh(new THREE.SphereGeometry(0.04, 8, 6), new THREE.MeshStandardMaterial({ color, transparent: true, opacity: 0.5 }), { cast: false });
    c.position.set(x, y, z * s); head.add(c);
  }
}
function quadLegs(root, legM, footM, { x = 0.24, z = 0.2, y = 0.2, len = 0.22, r = 0.085 } = {}) {
  const legs = [];
  for (const [lx, lz] of [[x, z], [x, -z], [-x, z], [-x, -z]]) {
    const leg = new THREE.Group(); leg.position.set(lx, y, lz);
    const l = mesh(new THREE.CylinderGeometry(r, r * 0.95, len, 8), legM); l.position.y = -len / 2 + 0.07; leg.add(l);
    const f = mesh(new THREE.CylinderGeometry(r * 0.98, r * 1.02, 0.06, 8), footM); f.position.y = -len + 0.08; leg.add(f);
    root.add(leg); legs.push(leg);
  }
  return legs;
}
function addCollar(root, levels, { x, y, r, bellY }) { // 목걸이 띠 색 = 억제 강도, 방울 색 = 경험 유지
  const c = mesh(new THREE.TorusGeometry(r, 0.035, 6, 20), mat(TRAIT_COLOR.g_apl[levels.g_apl])); c.position.set(x, y, 0); c.rotation.set(0.25, Math.PI / 2, 0); root.add(c);
  const b = mesh(ico(0.055, 1), mat(TRAIT_COLOR.decay[levels.decay], { metalness: 0.4, roughness: 0.4 })); b.position.set(x + r * 0.62, bellY, 0); root.add(b);
}
const BUILD = {
  pig(root) {
    const pink = mat(0xf3a3ab), dark = mat(0xe3838f);
    const body = mesh(ico(0.42), pink); body.scale.set(1.18, 0.92, 1.0); body.position.y = 0.46; root.add(body);
    const head = new THREE.Group(); head.position.set(0.4, 0.66, 0); root.add(head);
    head.add(mesh(ico(0.34), pink));
    const snout = mesh(new THREE.CylinderGeometry(0.14, 0.15, 0.12, 12), dark); snout.rotation.z = Math.PI / 2; snout.position.set(0.32, -0.05, 0); head.add(snout);
    for (const z of [-0.05, 0.05]) { const n = mesh(new THREE.SphereGeometry(0.022, 8, 6), BLACK()); n.position.set(0.385, -0.05, z); head.add(n); }
    addEyes(head, 0.27, 0.07, 0.13); addCheeks(head, 0.24, -0.05, 0.23);
    for (const s of [-1, 1]) { const ear = mesh(new THREE.ConeGeometry(0.1, 0.2, 4), pink); ear.position.set(0.02, 0.3, 0.16 * s); ear.rotation.set(0.5 * s, 0, -0.25); head.add(ear); }
    const legs = quadLegs(root, pink, dark);
    const tail = mesh(new THREE.TorusGeometry(0.06, 0.02, 6, 12, Math.PI * 1.6), dark); tail.position.set(-0.5, 0.56, 0); tail.rotation.y = Math.PI / 2; root.add(tail);
    return { body, head, legs, collar: { x: 0.24, y: 0.56, r: 0.3, bellY: 0.42 } };
  },
  calf(root) {
    const white = mat(0xf7f3ee), black = mat(0x2d2826), pink = mat(0xf2b1b5), horn = mat(0xf3e2c0);
    const body = mesh(ico(0.42), white); body.scale.set(1.26, 0.95, 1.0); body.position.y = 0.52; root.add(body);
    for (const [x, y, z, s] of [[-0.18, 0.72, 0.3, 0.16], [0.12, 0.46, -0.4, 0.14], [-0.38, 0.5, -0.22, 0.12], [0.05, 0.82, -0.12, 0.1]]) {
      const sp = mesh(ico(s, 1), black); sp.position.set(x, y, z); sp.scale.set(1.2, 0.8, 0.5); sp.lookAt(0, 0.52, 0); root.add(sp);
    }
    const head = new THREE.Group(); head.position.set(0.46, 0.76, 0); root.add(head);
    head.add(mesh(ico(0.31), white));
    const muzzle = mesh(ico(0.18), pink); muzzle.scale.set(0.8, 0.72, 1.12); muzzle.position.set(0.26, -0.1, 0); head.add(muzzle);
    for (const z of [-0.06, 0.06]) { const n = mesh(new THREE.SphereGeometry(0.022, 8, 6), BLACK()); n.position.set(0.4, -0.08, z); head.add(n); }
    addEyes(head, 0.2, 0.07, 0.14);
    for (const s of [-1, 1]) {
      const h = mesh(new THREE.ConeGeometry(0.04, 0.12, 6), horn); h.position.set(-0.02, 0.3, 0.12 * s); h.rotation.x = 0.3 * s; head.add(h);
      const ear = mesh(ico(0.08, 1), pink); ear.scale.set(0.5, 0.45, 1.3); ear.position.set(-0.02, 0.16, 0.32 * s); head.add(ear);
    }
    const legs = quadLegs(root, white, black, { y: 0.26, len: 0.3, r: 0.08 });
    const tail = mesh(new THREE.CylinderGeometry(0.018, 0.018, 0.34, 6), white); tail.position.set(-0.55, 0.52, 0); tail.rotation.z = -0.5; root.add(tail);
    const tuft = mesh(ico(0.045, 1), black); tuft.position.set(-0.63, 0.37, 0); root.add(tuft);
    return { body, head, legs, collar: { x: 0.32, y: 0.64, r: 0.29, bellY: 0.48 } };
  },
  chick(root) {
    const yellow = mat(0xffd95a), orange = mat(0xf39a2b), light = mat(0xffe999);
    const body = mesh(ico(0.4), yellow); body.scale.set(1.05, 0.98, 1.0); body.position.y = 0.44; root.add(body);
    const head = new THREE.Group(); head.position.set(0.2, 0.86, 0); root.add(head);
    head.add(mesh(ico(0.27), yellow));
    const beak = mesh(new THREE.ConeGeometry(0.07, 0.15, 6), orange); beak.rotation.z = -Math.PI / 2; beak.position.set(0.3, -0.03, 0); head.add(beak);
    addEyes(head, 0.2, 0.06, 0.12, 0.04); addCheeks(head, 0.18, -0.06, 0.19, 0xffa07a);
    for (let i = 0; i < 3; i++) { const t = mesh(new THREE.ConeGeometry(0.035, 0.12, 5), light); t.position.set(-0.02 + i * 0.05, 0.3, (i - 1) * 0.03); t.rotation.z = (1 - i) * 0.35; head.add(t); }
    for (const s of [-1, 1]) { const w = mesh(ico(0.2, 1), light); w.scale.set(0.95, 0.55, 0.28); w.position.set(-0.05, 0.48, 0.38 * s); w.rotation.x = 0.2 * s; root.add(w); }
    const tail = mesh(new THREE.ConeGeometry(0.08, 0.16, 5), light); tail.position.set(-0.43, 0.56, 0); tail.rotation.z = 1.1; root.add(tail);
    const legs = [];
    for (const s of [-1, 1]) {
      const leg = new THREE.Group(); leg.position.set(0.05, 0.14, 0.13 * s);
      const l = mesh(new THREE.CylinderGeometry(0.025, 0.025, 0.16, 6), orange); l.position.y = -0.05; leg.add(l);
      const f = mesh(new THREE.BoxGeometry(0.16, 0.03, 0.12), orange); f.position.set(0.04, -0.12, 0); leg.add(f);
      root.add(leg); legs.push(leg);
    }
    return { body, head, legs, collar: { x: 0.16, y: 0.68, r: 0.23, bellY: 0.56 } };
  },
  puppy(root) {
    const tan = mat(0xd8ad74), light = mat(0xf2dcb6), ear = mat(0xa9764a);
    const body = mesh(ico(0.4), tan); body.scale.set(1.25, 0.9, 0.95); body.position.y = 0.46; root.add(body);
    const head = new THREE.Group(); head.position.set(0.43, 0.72, 0); root.add(head);
    head.add(mesh(ico(0.32), tan));
    const snout = mesh(ico(0.15), light); snout.scale.set(1.15, 0.78, 0.95); snout.position.set(0.27, -0.08, 0); head.add(snout);
    const nose = mesh(new THREE.SphereGeometry(0.045, 10, 8), BLACK()); nose.position.set(0.43, -0.04, 0); head.add(nose);
    addEyes(head, 0.24, 0.07, 0.13);
    for (const s of [-1, 1]) { const e = mesh(ico(0.13, 1), ear); e.scale.set(0.55, 1.15, 0.32); e.position.set(-0.02, 0.04, 0.3 * s); e.rotation.x = 0.25 * s; head.add(e); }
    const legs = quadLegs(root, tan, light, { y: 0.21, len: 0.24, r: 0.08 });
    const tail = mesh(new THREE.ConeGeometry(0.06, 0.28, 6), tan); tail.position.set(-0.52, 0.66, 0); tail.rotation.z = 0.7; root.add(tail);
    return { body, head, legs, collar: { x: 0.28, y: 0.57, r: 0.29, bellY: 0.43 } };
  },
};
function buildPet(species, levels, baby) {
  const root = new THREE.Group();
  const parts = BUILD[species](root);
  addCollar(root, levels, parts.collar);
  root.scale.setScalar(baby ? 0.78 : 1);
  root.userData = { body: parts.body, head: parts.head, legs: parts.legs };
  return root;
}

const petRoot = new THREE.Group(); petRoot.scale.setScalar(1.3); scene.add(petRoot);
let petModel = null, customModel = null, tag = null;
const HOME = new THREE.Vector3(-0.2, 0.06, 0);
petRoot.position.copy(HOME);

function setPetModel(pet) {
  if (petModel) petRoot.remove(petModel);
  if (customModel) {
    petModel = customModel.clone(true);
    const s = pet.gen > 1 ? 0.78 : 1; petModel.scale.multiplyScalar(s);
    petModel.userData = { body: petModel, head: petModel, legs: [], tail: null };
  } else petModel = buildPet(pet.species, levelsOf(pet), pet.gen > 1);
  petRoot.add(petModel);
  if (tag) petRoot.remove(tag);
  tag = labelSprite(`${pet.name} · ${pet.gen}세대`, { size: 44, pad: 16, scale: 0.0026 });
  tag.position.set(0, pet.gen > 1 ? 1.05 : 1.25, 0); petRoot.add(tag);
}

// A·B 물건: A = 초록 블록, B = 주황 공 (화면 표현. 모델 입력은 DM2·DM4 경로)
function buildToy(kind) {
  const g = new THREE.Group();
  if (kind === "A") {
    const b = mesh(new THREE.BoxGeometry(0.46, 0.46, 0.46, 2, 2, 2), mat(0x4fae86)); b.position.y = 0.23; b.rotation.y = 0.4; g.add(b);
    const s = mesh(new THREE.BoxGeometry(0.2, 0.2, 0.2), mat(0xbfe8d4)); s.position.y = 0.56; s.rotation.y = 0.9; g.add(s);
  } else {
    const b = mesh(new THREE.IcosahedronGeometry(0.27, 1), mat(0xf08a4b)); b.position.y = 0.27; g.add(b);
    const r = mesh(new THREE.TorusGeometry(0.27, 0.035, 6, 20), mat(0xfff1e0)); r.position.y = 0.27; r.rotation.x = 1.2; g.add(r);
  }
  const lab = labelSprite(kind, { bg: kind === "A" ? "#4fae86" : "#f08a4b", fg: "#fff", size: 56, pad: 16 }); lab.position.y = 1.0; g.add(lab);
  g.scale.setScalar(0.001); scene.add(g);
  return g;
}
const toys = { A: buildToy("A"), B: buildToy("B") };
const SLOTS = [new THREE.Vector3(2.4, 0.06, -1.35), new THREE.Vector3(2.4, 0.06, 1.35)];
toys.A.position.copy(SLOTS[0]); toys.B.position.copy(SLOTS[1]); toys.A.scale.setScalar(0.8); toys.B.scale.setScalar(0.8);

// 손(쓰다듬기)과 효과
const hand = new THREE.Group();
{ const m = mat(0xfff3e9); const palm = mesh(new THREE.SphereGeometry(0.16, 12, 10), m); palm.scale.set(1.2, 0.55, 1); hand.add(palm);
  for (let i = 0; i < 4; i++) { const f = mesh(new THREE.CapsuleGeometry(0.035, 0.12, 3, 6), m); f.position.set(0.16, 0, -0.1 + i * 0.066); f.rotation.z = Math.PI / 2; hand.add(f); }
  const th = mesh(new THREE.CapsuleGeometry(0.035, 0.08, 3, 6), m); th.position.set(0.02, 0, 0.17); th.rotation.x = 1; hand.add(th); }
hand.scale.setScalar(1.6); hand.visible = false; scene.add(hand);

// ---------------------------------------------------------------- 애니메이션
let speed = 1;
const tweens = new Set();
const sleep = (ms) => (speed === 0 ? Promise.resolve() : new Promise((r) => setTimeout(r, ms / speed)));
function tween(ms, fn) {
  if (speed === 0) { fn(1); return Promise.resolve(); }
  return new Promise((res) => tweens.add({ t0: performance.now(), ms: ms / speed, fn, res }));
}
const ease = (t) => (t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2);
function faceTo(target) { petRoot.rotation.y = Math.atan2(-(target.z - petRoot.position.z), target.x - petRoot.position.x); }
async function walkTo(target, ms = 900) {
  const from = petRoot.position.clone(), to = target.clone();
  faceTo(to);
  const legs = petModel.userData.legs;
  await tween(ms, (t) => {
    const e = ease(t);
    petRoot.position.lerpVectors(from, to, e);
    petRoot.position.y = HOME.y + Math.abs(Math.sin(t * Math.PI * 4)) * 0.12;
    legs.forEach((l, i) => (l.rotation.z = Math.sin(t * Math.PI * 8 + (i % 2) * Math.PI) * 0.45));
  });
  legs.forEach((l) => (l.rotation.z = 0)); petRoot.position.y = HOME.y;
}
async function floatUp(sprite, from, ms = 1100) {
  scene.add(sprite);
  await tween(ms, (t) => { sprite.position.set(from.x, from.y + t * 0.9, from.z); sprite.material.opacity = 1 - t * t; });
  scene.remove(sprite);
}
async function pet() { // 쓰다듬기 = 보상(+1)의 화면 표현
  const top = petRoot.position.clone().add(new THREE.Vector3(0, 1.2, 0));
  hand.visible = true;
  await tween(300, (t) => hand.position.set(top.x, top.y + 0.6 * (1 - t), top.z));
  const hearts = [0, 1, 2].map(() => emojiSprite("♥", 0.34));
  hearts.forEach((h, i) => { setTimeout(() => floatUp(h, top.clone().add(new THREE.Vector3((i - 1) * 0.25, 0, 0))), (i * 160) / Math.max(speed, 1)); });
  await tween(900, (t) => { hand.position.z = top.z + Math.sin(t * Math.PI * 6) * 0.12; petModel.userData.head.rotation.x = Math.sin(t * Math.PI * 6) * 0.12; });
  petModel.userData.head.rotation.x = 0;
  await tween(250, (t) => (hand.position.y = top.y + 0.6 * t));
  hand.visible = false;
}
async function scold() { // 처벌(-1)의 화면 표현
  floatUp(labelSprite("!", { bg: "#d0585e", fg: "#fff", size: 60, pad: 14 }), petRoot.position.clone().add(new THREE.Vector3(0, 1.3, 0)), 900);
  const h = petModel.userData.head;
  await tween(700, (t) => (h.rotation.y = Math.sin(t * Math.PI * 6) * 0.35 * (1 - t)));
  h.rotation.y = 0;
}
async function nothing() { // 결과 없음(0)
  await floatUp(labelSprite("…", { bg: "#ffffff", fg: "#a08b7e", size: 56, pad: 14 }), petRoot.position.clone().add(new THREE.Vector3(0, 1.3, 0)), 800);
}
async function showToys(order) {
  order.forEach((k, i) => { toys[k].position.copy(SLOTS[i]); });
  await tween(260, (t) => Object.values(toys).forEach((o) => o.scale.setScalar(0.3 + 0.7 * ease(t))));
}
const REST = 0.8; // 쉬는 동안에도 두 물건을 작게 보여 준다
async function hideToys() { await tween(220, (t) => Object.values(toys).forEach((o) => o.scale.setScalar(1 - (1 - REST) * t))); }

// ---------------------------------------------------------------- 펫 목록과 세션
const NAMES = ["모모", "보리", "콩이", "두부"];
const founders = [
  { g_apl: "high", decay: "high" }, { g_apl: "high", decay: "low" }, { g_apl: "low", decay: "high" }, { g_apl: "low", decay: "low" },
].map((lv, i) => ({ id: `P${i + 1}`, name: `${NAMES[i]}(P${i + 1})`, species: ["pig", "calf", "chick", "puppy"][i], code: G.encode(lv), gen: 1, parents: [], from: {}, origin: "시조", trainSeed: i, hist: null, result: null }));
const roster = [...founders];
let current = roster[0], session = null, policy = D.defaults.reward_policy, busy = false, breedSeed = 1, childNo = 0;
const levelsOf = (p) => G.decode(p.code).levels;
const lookOptions = (sel) => Object.entries(SPECIES).map(([k, v]) => `<option value="${k}" ${k === sel ? "selected" : ""}>${v.emoji} ${v.name}</option>`).join("");
const settingsOf = (p) => G.decode(p.code).settings;
const labelsOf = (p) => G.decode(p.code).labels;

function newSession() {
  session = new L.Session("baseline", current.trainSeed, { ...settingsOf(current), reward_policy: policy });
}
const phaseCount = (ph) => session.history.filter((h) => h.phase === ph).length;
const remaining = (ph) => Math.max(0, (ph === "initial" ? N0 : N1) - phaseCount(ph));
function criterion(hist, ph) { // engine.py의 주 기준과 같음(임시값)
  const p = D.defaults, n = ph === "initial" ? N0 : N1, seq = hist.filter((h) => h.phase === ph).slice(0, n);
  let run = 0;
  for (let i = 0; i < seq.length; i++) { run = seq[i].p_correct >= p.crit_p ? run + 1 : 0; if (run >= p.crit_k) return i + 1; }
  return null;
}

async function trial() {
  const order = Math.random() < 0.5 ? ["A", "B"] : ["B", "A"]; // 좌우 위치는 화면 표현일 뿐 모델과 무관
  await showToys(order);
  await sleep(180);
  const rec = session.step(); // 모델이 선택하고, 정해진 보상 정책으로 학습한다
  const slot = SLOTS[order.indexOf(rec.choice)];
  await walkTo(new THREE.Vector3(slot.x - 0.75, HOME.y, slot.z));
  if (rec.outcome > 0) await pet(); else if (rec.outcome < 0) await scold(); else await nothing();
  await Promise.all([walkTo(HOME, 700), hideToys()]);
  faceTo(new THREE.Vector3(3, 0, 0));
  updateUI();
}
async function run(n) {
  if (busy || n <= 0) return;
  busy = true; updateButtons();
  for (let i = 0; i < n; i++) await trial();
  busy = false;
  if (phaseCount("reversal") >= N1) finishPet();
  updateUI();
}
function finishPet() {
  current.hist = session.history.slice();
  current.result = { initial: criterion(current.hist, "initial"), reversal: criterion(current.hist, "reversal"), policy };
  toast(`${current.name} 훈련 완료 · 첫 학습 ${fmtReach(current.result.initial)}, 재학습 ${fmtReach(current.result.reversal)}`);
  renderRoster(); drawPetChart();
}
const fmtReach = (v) => (v == null ? "40회 안 미도달" : `${v}회`);

function selectPet(p) {
  current = p; newSession(); setPetModel(p);
  petRoot.position.copy(HOME); faceTo(new THREE.Vector3(3, 0, 0));
  updateUI(); renderRoster();
}

// ---------------------------------------------------------------- 화면 갱신
function updateUI() {
  const st = session.state(), lab = labelsOf(current), lv = levelsOf(current), set = settingsOf(current);
  $("petName").textContent = current.name;
  $("petGen").textContent = `${current.gen}세대 · ${current.origin}`;
  $("petOrigin").textContent = `선택 seed ${current.trainSeed}`;
  $("petLook").innerHTML = lookOptions(current.species);
  $("petTraits").innerHTML = Object.keys(D.traits).map((t) => {
    const col = "#" + TRAIT_COLOR[t][lv[t]].toString(16).padStart(6, "0");
    return `<div class="trait" style="border-color:${col}"><small>${t === "g_apl" ? "목걸이 띠" : "방울"} · ${t} ${set[t]}</small><span style="color:${col}">●</span> ${lab[t]}</div>`;
  }).join("");
  $("petCode").textContent = G.toHex(current.code);
  $("petFrom").innerHTML = current.parents.length
    ? `부모 ${current.parents.join(" × ")} · ${Object.entries(current.from).map(([t, id]) => `${t === "g_apl" ? "억제" : "경험 유지"}는 ${id}에게서`).join(", ")}`
    : "시조 펫: 성향을 정해서 만든 1세대입니다.";
  $("pA").textContent = st.pA.toFixed(3);
  $("pABar").style.left = `${st.pA * 100}%`;
  $("good").innerHTML = st.good === "A" ? '<span style="color:var(--a)">A 블록</span>' : '<span style="color:var(--b)">B 공</span>';
  $("phase").textContent = session.reversals === 0 ? "첫 학습" : "재학습";
  $("trial").textContent = `${st.trial} / ${N0 + N1}`;
  $("prog0").style.width = `${(phaseCount("initial") / N0) * 100}%`;
  $("prog1").style.width = `${(phaseCount("reversal") / N1) * 100}%`;
  const c0 = criterion(session.history, "initial"), c1 = criterion(session.history, "reversal");
  $("reach").innerHTML = `완료 기준(임시값): 정답 확률 ${D.defaults.crit_p} 이상 ${D.defaults.crit_k}회 연속<br>` +
    `첫 학습 <b>${c0 != null ? c0 + "회" : phaseCount("initial") >= N0 ? "40회 안 미도달" : "진행 중"}</b> · ` +
    `재학습 <b>${c1 != null ? c1 + "회" : phaseCount("reversal") >= N1 ? "40회 안 미도달" : session.reversals ? "진행 중" : "-"}</b>`;
  $("kcA").textContent = (st.kc_active_A * 100).toFixed(1) + "%";
  $("kcB").textContent = (st.kc_active_B * 100).toFixed(1) + "%";
  $("ov").textContent = st.overlap_AB.toFixed(3);
  $("apl").textContent = st.apl_inhibition_A.toFixed(2);
  $("gapl").textContent = session.p.g_apl;
  $("decay").textContent = session.p.decay;
  $("circuitSrc").textContent = `· ${D.inputs.A}·${D.inputs.B} 입력 · KC ${D.n_kc.toLocaleString()}`;
  drawLive(); updateButtons();
}
function updateButtons() {
  const ph = session.reversals === 0 ? "initial" : "reversal";
  $("btnStep").disabled = busy || remaining(ph) === 0;
  $("btnPhase").disabled = busy || remaining(ph) === 0;
  $("btnReverse").disabled = busy || session.reversals > 0 || phaseCount("initial") < N0;
  $("btnReset").disabled = busy;
  $("btnBreed").disabled = busy || selected.length !== 2;
}

// ---------------------------------------------------------------- 그래프 (Canvas 2D)
function setupCanvas(cv) { const x = cv.getContext("2d"); x.clearRect(0, 0, cv.width, cv.height); return x; }
function axes(x, cv, { L = 44, R = 12, T = 14, B = 30, n = 80, revAt = null, yLabel = "" } = {}) {
  const W = cv.width - L - R, H = cv.height - T - B, X = (i) => L + (i / n) * W, Y = (v) => T + (1 - v) * H;
  x.strokeStyle = "rgba(120,84,62,.15)"; x.lineWidth = 1; x.fillStyle = "#a08b7e"; x.font = "600 18px Malgun Gothic";
  for (const v of [0, 0.5, 1]) { x.beginPath(); x.moveTo(L, Y(v)); x.lineTo(L + W, Y(v)); x.stroke(); x.fillText(v.toFixed(1), 6, Y(v) + 6); }
  for (let i = 0; i <= n; i += 20) x.fillText(String(i), X(i) - 8, T + H + 24);
  if (revAt != null) { x.setLineDash([6, 6]); x.strokeStyle = "#5a8fd6"; x.lineWidth = 2; x.beginPath(); x.moveTo(X(revAt), T); x.lineTo(X(revAt), T + H); x.stroke(); x.setLineDash([]);
    x.fillStyle = "#5a8fd6"; x.fillText("규칙 변경", X(revAt) + 6, T + 18); }
  if (yLabel) { x.fillStyle = "#a08b7e"; x.fillText(yLabel, L + 4, T + H - 6); }
  x.setLineDash([3, 5]); x.strokeStyle = "rgba(228,111,125,.5)"; x.beginPath(); x.moveTo(L, Y(D.defaults.crit_p)); x.lineTo(L + W, Y(D.defaults.crit_p)); x.stroke(); x.setLineDash([]);
  return { X, Y };
}
function line(x, pts, X, Y, color, w = 3) { x.strokeStyle = color; x.lineWidth = w; x.lineJoin = "round"; x.beginPath(); pts.forEach((v, i) => (i ? x.lineTo(X(i + 1), Y(v)) : x.moveTo(X(i + 1), Y(v)))); x.stroke(); }
function drawLive() {
  const cv = $("chart"), x = setupCanvas(cv), h = session.history;
  const rev = h.findIndex((r) => r.phase !== "initial");
  const { X, Y } = axes(x, cv, { revAt: rev >= 0 ? rev : null });
  if (!h.length) { x.fillStyle = "#a08b7e"; x.font = "600 22px Malgun Gothic"; x.fillText("▶ 버튼을 눌러 훈련을 시작하세요", 150, 150); return; }
  line(x, h.map((r) => r.p_correct), X, Y, "#e46f7d");
  h.forEach((r, i) => { x.fillStyle = r.correct ? "#46a37a" : "#d0585e"; x.beginPath(); x.arc(X(i + 1), Y(r.correct ? 1 : 0) + (r.correct ? 8 : -8), 4, 0, 7); x.fill(); });
}
const PET_COLORS = ["#e46f7d", "#5a8fd6", "#46a37a", "#f08a4b", "#9b6fd0", "#2fa7a7", "#c9a227", "#d0585e"];
function drawPetChart() {
  const cv = $("petChart"), x = setupCanvas(cv), done = roster.filter((p) => p.hist);
  const { X, Y } = axes(x, cv, { revAt: N0 });
  done.forEach((p, i) => line(x, p.hist.map((r) => r.p_correct), X, Y, PET_COLORS[i % PET_COLORS.length], p.gen > 1 ? 3.5 : 2));
  $("petLegend").innerHTML = done.length ? done.map((p, i) => `<span style="color:${PET_COLORS[i % PET_COLORS.length]}">━ ${p.name}</span>`).join("") : '<span class="muted">훈련을 마친 펫이 여기에 표시됩니다.</span>';
}

// ---------------------------------------------------------------- 교배
let selected = [];
function renderRoster() {
  $("roster").innerHTML = roster.map((p) => {
    const lab = labelsOf(p), r = p.result;
    return `<button class="pcard ${selected.includes(p) ? "sel" : ""} ${p === current ? "cur" : ""}" data-id="${p.id}">
      <b>${SPECIES[p.species].emoji} ${p.name}</b><span>${p.gen}세대 · ${lab.g_apl} · ${lab.decay}</span>
      <div class="res">${r ? `첫 학습 ${fmtReach(r.initial)} · 재학습 ${fmtReach(r.reversal)}` : "아직 훈련 전"}</div></button>`;
  }).join("");
  $("roster").querySelectorAll(".pcard").forEach((b) => (b.onclick = () => {
    const p = roster.find((q) => q.id === b.dataset.id);
    if (selected.includes(p)) selected = selected.filter((q) => q !== p);
    else if (selected.length < 2) selected.push(p); else selected = [selected[1], p];
    $("breedSel").textContent = selected.length === 2 ? `${selected[0].name} × ${selected[1].name}` : "부모를 2마리 고르세요";
    renderRoster(); updateButtons();
  }));
}
function breed() {
  const [a, b] = selected, seed = breedSeed++;
  const { code, from } = G.cross(a, b, G.rng(seed));
  childNo++;
  const kid = { id: `C${childNo}`, name: `아기${childNo}(C${childNo})`, species: a.species, code, gen: Math.max(a.gen, b.gen) + 1, parents: [a.id, b.id], from,
                origin: "무작위 교배", trainSeed: 100 + childNo, breedSeed: seed, hist: null, result: null };
  roster.push(kid);
  const lab = labelsOf(kid);
  $("childBox").innerHTML = `<div class="box"><h3>🐣 ${kid.name}이(가) 태어났어요</h3>
    <p>${a.name} × ${b.name} · 교배 난수 ${seed}<br>억제 강도: <b>${lab.g_apl}</b> (${from.g_apl}에게서) · 경험 유지: <b>${lab.decay}</b> (${from.decay}에게서)<br>
    성향 코드(끝 8자리) <code>…${G.toHex(code).slice(-8)}</code><br>배운 것은 물려받지 않아 학습 전 상태에서 시작합니다.</p>
    <label class="look">아기 모습 <select id="kidLook">${lookOptions(kid.species)}</select> <span class="muted">꾸미기만 바뀌고 성향·학습과는 무관(유전 아님)</span></label>
    <button class="primary" id="btnAdopt">이 아기 데려와 훈련하기</button></div>`;
  $("kidLook").onchange = (e) => { kid.species = e.target.value; renderRoster(); };
  $("btnAdopt").onclick = () => { selectPet(kid); switchTab("train"); toast(`${kid.name}을(를) 데려왔어요. 부모와 같은 절차로 훈련합니다.`); };
  renderRoster();
}

// ---------------------------------------------------------------- 네 조합 비교 (브라우저 계산)
async function compare() {
  const btn = $("btnCompare"); btn.disabled = true; btn.textContent = "계산 중…";
  await new Promise((r) => setTimeout(r, 30));
  const combos = founders.map((p) => ({ p, rows: { baseline: [], learning_off: [] } }));
  for (const c of combos) for (const cond of ["baseline", "learning_off"]) {
    for (let s = 0; s < 30; s++) c.rows[cond].push(L.runOne(cond, s, { ...settingsOf(c.p), reward_policy: policy }));
    await new Promise((r) => setTimeout(r, 0));
  }
  const med = (a) => { const v = a.filter((x) => x != null).sort((p, q) => p - q); if (!v.length) return "-"; const m = v.length / 2; return v.length % 2 ? v[(v.length - 1) / 2] : (v[m - 1] + v[m]) / 2; };
  const reach = (rs, k) => rs.filter((r) => r[k] != null).length;
  $("compareOut").innerHTML = `<table class="res"><tr><th>성향 조합</th><th>첫 학습 도달</th><th>재학습 도달 (중앙값)</th><th>학습 끔 재학습</th></tr>
    ${combos.map((c) => { const lab = labelsOf(c.p), b = c.rows.baseline;
      return `<tr><td>${lab.g_apl}<br><span class="muted">${lab.decay}</span></td><td>${reach(b, "initial")}/30</td><td>${reach(b, "reversal")}/30 (${med(b.map((r) => r.reversal))})</td><td>${reach(c.rows.learning_off, "reversal")}/30</td></tr>`; }).join("")}
    </table><p class="hint" style="margin-top:8px">보상 정책: ${policy === "reward_punish" ? "보상 + 처벌" : "보상만"} · seed 0–29(예비 범위) · 40회 안 도달 기준 · 브라우저 시연 계산</p>`;
  const cv = $("cumChart"); cv.classList.remove("hidden");
  const x = setupCanvas(cv), { X, Y } = axes(x, cv, { n: 40, yLabel: "재학습 누적 도달 비율" });
  combos.forEach((c, i) => {
    const vals = c.rows.baseline.map((r) => r.reversal);
    line(x, Array.from({ length: 40 }, (_, t) => vals.filter((v) => v != null && v <= t + 1).length / 30), X, Y, PET_COLORS[i], 3);
    const lab = labelsOf(c.p); x.fillStyle = PET_COLORS[i]; x.font = "700 17px Malgun Gothic"; x.fillText(`━ ${lab.g_apl}·${lab.decay}`, cv.width - 250, cv.height - 130 + i * 22);
  });
  btn.disabled = false; btn.textContent = "다시 실행";
}

// ---------------------------------------------------------------- 탭, 버튼, 에셋
function switchTab(tab) {
  document.querySelectorAll("#tabs button").forEach((b) => b.classList.toggle("on", b.dataset.tab === tab));
  $("chartCard").classList.toggle("hidden", tab !== "train");
  document.querySelector(".circuit-card").classList.toggle("hidden", tab !== "train");
  $("breedCard").classList.toggle("hidden", tab !== "breed");
  $("compareCard").classList.toggle("hidden", tab !== "compare");
  if (tab === "compare") drawPetChart();
}
document.querySelectorAll("#tabs button").forEach((b) => (b.onclick = () => switchTab(b.dataset.tab)));
document.querySelectorAll("#policy button").forEach((b) => (b.onclick = () => {
  if (busy) return;
  policy = b.dataset.p;
  document.querySelectorAll("#policy button").forEach((q) => q.classList.toggle("on", q === b));
  roster.forEach((p) => { p.hist = null; p.result = null; });
  selectPet(current); drawPetChart();
  toast(`보상 정책을 '${b.textContent}'(으)로 바꿨어요. 훈련 기록을 처음부터 다시 쌓습니다.`);
}));
document.querySelectorAll("#speed button").forEach((b) => (b.onclick = () => {
  speed = Number(b.dataset.s);
  document.querySelectorAll("#speed button").forEach((q) => q.classList.toggle("on", q === b));
}));
$("btnStep").onclick = () => run(1);
$("btnPhase").onclick = () => run(remaining(session.reversals === 0 ? "initial" : "reversal"));
$("btnReverse").onclick = () => { session.reverse(); toast("규칙을 바꿨어요. 이제 B 공이 정답입니다."); updateUI(); };
$("btnReset").onclick = () => { current.hist = null; current.result = null; selectPet(current); };
$("btnBreed").onclick = breed;
$("petLook").onchange = (e) => { current.species = e.target.value; setPetModel(current); renderRoster(); };
$("btnCompare").onclick = compare;
$("glb").onchange = async (e) => {
  const f = e.target.files[0]; if (!f) return;
  try {
    const gltf = await new GLTFLoader().parseAsync(await f.arrayBuffer(), "");
    const m = gltf.scene; m.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
    const box = new THREE.Box3().setFromObject(m), size = box.getSize(new THREE.Vector3());
    m.scale.multiplyScalar(0.9 / Math.max(size.x, size.y, size.z));
    m.rotation.y = Math.PI / 2; // 에셋 정면(+z)을 펫 진행 방향(+x)으로
    const wrap = new THREE.Group(); wrap.add(m); customModel = wrap; setPetModel(current);
    toast(`'${f.name}'을(를) 이 브라우저에서만 불러왔어요. 파일은 저장하거나 보내지 않습니다.`);
  } catch (err) { toast("GLB를 불러오지 못했어요: " + err.message); }
};
let toastTimer;
function toast(msg) { const t = $("toast"); t.textContent = msg; t.classList.add("on"); clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.remove("on"), 2600); }

// ---------------------------------------------------------------- 그리기 루프
function resize() { const w = window.innerWidth, h = window.innerHeight; renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix(); }
window.addEventListener("resize", resize); resize();
const clock = new THREE.Clock();
renderer.setAnimationLoop(() => {
  const now = performance.now(), t = clock.getElapsedTime();
  for (const tw of [...tweens]) { const k = Math.min(1, (now - tw.t0) / tw.ms); tw.fn(k); if (k >= 1) { tweens.delete(tw); tw.res(); } }
  if (petModel && !busy) { const b = petModel.userData.body; if (b) b.scale.y = (b === petModel ? 1 : 0.92) * (1 + Math.sin(t * 2.2) * 0.02); }
  Object.values(toys).forEach((o, i) => (o.children[o.children.length - 1].position.y = 1.0 + Math.sin(t * 2 + i) * 0.04));
  controls.update(); renderer.render(scene, camera);
});

selectPet(current); renderRoster(); drawPetChart();

// 자동 점검용(?test=1): 훈련 → 규칙 변경 → 재학습 → 교배 → 비교를 즉시 실행하고 결과를 body에 남긴다
if (new URLSearchParams(location.search).get("test")) (async () => {
  speed = 0;
  await run(remaining("initial")); session.reverse(); await run(remaining("reversal"));
  selected = [founders[1], founders[2]]; $("breedSel").textContent = `${selected[0].name} × ${selected[1].name}`; renderRoster(); breed();
  const kid = roster[roster.length - 1]; selectPet(kid);
  await run(remaining("initial")); session.reverse(); await run(remaining("reversal"));
  await compare();
  const tab = new URLSearchParams(location.search).get("tab"); if (tab) switchTab(tab);
  speed = 1;
  document.body.dataset.test = JSON.stringify({ founder: founders[0].result, kid: { name: kid.name, from: kid.from, gen: kid.gen, result: kid.result },
    trained: roster.filter((p) => p.result).length, table: $("compareOut").innerText.slice(0, 300) });
})().catch((e) => (document.body.dataset.test = "ERR " + e.stack));

// 모습 확인용(?gallery=1): 네 동물을 나란히 보여준다
if (new URLSearchParams(location.search).get("gallery")) {
  petRoot.visible = false; Object.values(toys).forEach((o) => (o.visible = false));
  founders.forEach((p, i) => {
    const m = buildPet(p.species, levelsOf(p), false); m.scale.setScalar(1.3);
    const t0 = -1.95 + i * 1.3; m.position.set(0.45 + t0 * 0.78, 0.06, 0.4 - t0 * 0.57); m.rotation.y = -0.96; scene.add(m);
    const t = labelSprite(`${SPECIES[p.species].emoji} ${SPECIES[p.species].name}`, { size: 40, pad: 14, scale: 0.0024 });
    t.position.set(m.position.x, 1.5, m.position.z); scene.add(t);
  });
  document.body.dataset.test = "gallery";
}

// 설명용 캡처(?pose=pet): 첫 학습 40회를 마친 뒤, 정답 물건 앞에서 쓰다듬기를 받는 순간을 멈춰 보여준다(화면 표현, 학습과 무관)
if (new URLSearchParams(location.search).get("pose") === "pet") (async () => {
  speed = 0;
  await run(remaining("initial"));
  toys.A.position.copy(SLOTS[0]); toys.B.position.copy(SLOTS[1]); toys.A.scale.setScalar(1); toys.B.scale.setScalar(1);
  petRoot.position.set(SLOTS[0].x - 0.8, HOME.y, SLOTS[0].z); faceTo(SLOTS[0]);
  const top = petRoot.position.clone().add(new THREE.Vector3(0, 1.25, 0));
  hand.visible = true; hand.position.set(top.x, top.y + 0.1, top.z);
  [-0.32, 0, 0.32].forEach((dx, i) => { const h = emojiSprite("♥", 0.34); h.position.set(top.x + dx, top.y + 0.45 + i * 0.16, top.z + dx); scene.add(h); });
  speed = 1;
  setTimeout(() => {
    const proj = (v) => { const p = v.clone().project(camera); return [Math.round(((p.x + 1) / 2) * innerWidth), Math.round(((1 - p.y) / 2) * innerHeight)]; };
    document.body.dataset.pose = JSON.stringify({ pet: proj(petRoot.position.clone().add(new THREE.Vector3(0, 0.55, 0))), hand: proj(top),
      A: proj(SLOTS[0].clone().add(new THREE.Vector3(0, 0.5, 0))), B: proj(SLOTS[1].clone().add(new THREE.Vector3(0, 0.4, 0))) });
  }, 600);
})();

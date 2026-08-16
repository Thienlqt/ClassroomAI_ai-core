<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import {
  Clock,
  DirectionalLight,
  Object3D,
  PerspectiveCamera,
  Scene,
  SRGBColorSpace,
  WebGLRenderer,
} from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { VRMLoaderPlugin, VRMUtils } from "@pixiv/three-vrm";

import previewUrl from "../assets/teacher-avatar-preview.png";

const props = defineProps({ speaking: Boolean });

const host = ref(null);
const loading = ref(true);
const progress = ref(0);
const failed = ref(false);

let renderer;
let camera;
let scene;
let vrm;
let frameId;
let resizeObserver;
let lookTarget;
let pointerX = 0;
let pointerY = 0;
let blinkElapsed = 0;
let blinkAt = 2 + Math.random() * 3;
let blinkPhase = -1;
let modelForwardRotation = 0;
const clock = new Clock();
const mouthExpressions = ["aa", "ih", "ou", "ee", "oh"];

function setBoneRotation(name, rotation) {
  const bone = vrm?.humanoid?.getNormalizedBoneNode(name);
  if (!bone) return;
  bone.rotation.set(rotation.x ?? 0, rotation.y ?? 0, rotation.z ?? 0);
}

function applyRelaxedStandingPose() {
  // VRM avatars load in a T-pose. Lower the arms into a neutral teacher pose.
  setBoneRotation("leftUpperArm", { z: Math.PI * 0.4 });
  setBoneRotation("rightUpperArm", { z: -Math.PI * 0.4 });
  setBoneRotation("leftLowerArm", { z: Math.PI * 0.05 });
  setBoneRotation("rightLowerArm", { z: -Math.PI * 0.05 });
}

function resize() {
  if (!host.value || !renderer || !camera) return;
  const { clientWidth: width, clientHeight: height } = host.value;
  renderer.setSize(width, height, false);
  camera.aspect = width / Math.max(height, 1);
  camera.updateProjectionMatrix();
}

function updateBlink(delta) {
  if (!vrm?.expressionManager) return;
  blinkElapsed += delta;
  if (blinkPhase < 0 && blinkElapsed >= blinkAt) blinkPhase = 0;
  if (blinkPhase < 0) return;

  blinkPhase += delta / 0.18;
  vrm.expressionManager.setValue("blink", Math.sin(Math.PI * blinkPhase));
  if (blinkPhase >= 1) {
    vrm.expressionManager.setValue("blink", 0);
    blinkPhase = -1;
    blinkElapsed = 0;
    blinkAt = 2 + Math.random() * 4;
  }
}

function updateMouth(elapsed) {
  const manager = vrm?.expressionManager;
  if (!manager) return;

  if (!props.speaking) {
    mouthExpressions.forEach((name) => manager.setValue(name, 0));
    return;
  }

  // Piper does not return phoneme timings, so cross-fade between VRM vowel
  // shapes while the audio is playing to create natural-looking speech.
  const vowelPosition = elapsed * 4.5;
  const currentIndex = Math.floor(vowelPosition) % mouthExpressions.length;
  const nextIndex = (currentIndex + 1) % mouthExpressions.length;
  const vowelMix = vowelPosition - Math.floor(vowelPosition);
  const openness = 0.12 + Math.abs(Math.sin(elapsed * 9.5)) * 0.55;

  mouthExpressions.forEach((name, index) => {
    let weight = 0;
    if (index === currentIndex) weight = openness * (1 - vowelMix);
    if (index === nextIndex) weight = openness * vowelMix;
    manager.setValue(name, weight);
  });
}

function onPointerMove(event) {
  if (!host.value) return;
  const bounds = host.value.getBoundingClientRect();
  pointerX = ((event.clientX - bounds.left) / bounds.width) * 2 - 1;
  pointerY = -(((event.clientY - bounds.top) / bounds.height) * 2 - 1);
}

function animate() {
  const delta = Math.min(clock.getDelta(), 0.05);
  const elapsed = clock.elapsedTime;

  if (vrm) {
    updateBlink(delta);
    updateMouth(elapsed);
    if (lookTarget) {
      lookTarget.position.x += (pointerX * 0.9 - lookTarget.position.x) * 0.04;
      lookTarget.position.y += (1.42 + pointerY * 0.32 - lookTarget.position.y) * 0.04;
    }
    vrm.scene.position.y = Math.sin(elapsed * 1.25) * 0.008;
    // Keep the VRM version correction while adding a small idle turn.
    vrm.scene.rotation.y = modelForwardRotation + Math.sin(elapsed * 0.45) * 0.025;
    const happyValue = props.speaking ? 0.18 + Math.sin(elapsed * 5) * 0.04 : 0.08;
    vrm.expressionManager?.setValue("happy", happyValue);
    vrm.update(delta);
  }

  renderer?.render(scene, camera);
  frameId = requestAnimationFrame(animate);
}

onMounted(async () => {
  scene = new Scene();

  camera = new PerspectiveCamera(27, 1, 0.1, 20);
  camera.position.set(0, 1.32, 3.15);
  camera.lookAt(0, 1.25, 0);

  renderer = new WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.outputColorSpace = SRGBColorSpace;
  renderer.setClearColor(0x000000, 0);
  host.value.append(renderer.domElement);

  const keyLight = new DirectionalLight(0xfff2dd, 3.1);
  keyLight.position.set(1.6, 2.8, 2.5);
  scene.add(keyLight);
  const fillLight = new DirectionalLight(0xbdd8ff, 1.5);
  fillLight.position.set(-2.2, 1.8, 1.2);
  scene.add(fillLight);

  resizeObserver = new ResizeObserver(resize);
  resizeObserver.observe(host.value);
  host.value.addEventListener("pointermove", onPointerMove);
  resize();
  animate();

  try {
    const loader = new GLTFLoader();
    loader.register((parser) => new VRMLoaderPlugin(parser));
    const gltf = await loader.loadAsync(
      "/assets/avatar/teacher.vrm",
      (event) => {
        if (event.total) progress.value = Math.round((event.loaded / event.total) * 100);
      },
    );
    vrm = gltf.userData.vrm;
    if (!vrm) throw new Error("The teacher model is not a valid VRM file.");
    VRMUtils.removeUnnecessaryVertices(vrm.scene);
    VRMUtils.combineSkeletons(vrm.scene);
    VRMUtils.rotateVRM0(vrm);
    modelForwardRotation = vrm.scene.rotation.y;
    applyRelaxedStandingPose();
    vrm.scene.traverse((object) => {
      object.frustumCulled = false;
    });
    lookTarget = new Object3D();
    lookTarget.position.set(0, 1.42, 3);
    scene.add(lookTarget);
    if (vrm.lookAt) vrm.lookAt.target = lookTarget;
    scene.add(vrm.scene);
    loading.value = false;
  } catch (error) {
    console.error("Teacher VRM failed to load", error);
    loading.value = false;
    failed.value = true;
  }
});

watch(
  () => props.speaking,
  () => {
    if (!vrm?.expressionManager) return;
    vrm.expressionManager.setValue("happy", props.speaking ? 0.2 : 0.08);
    if (!props.speaking) {
      mouthExpressions.forEach((name) => vrm.expressionManager.setValue(name, 0));
    }
  },
);

onBeforeUnmount(() => {
  cancelAnimationFrame(frameId);
  resizeObserver?.disconnect();
  host.value?.removeEventListener("pointermove", onPointerMove);
  if (vrm) VRMUtils.deepDispose(vrm.scene);
  renderer?.dispose();
  renderer?.domElement.remove();
});
</script>

<template>
  <div ref="host" class="avatar-stage" aria-label="Animated 3D teacher">
    <div v-if="loading" class="avatar-status">
      <span class="loader-ring" aria-hidden="true"></span>
      <span>Preparing teacher{{ progress ? ` · ${progress}%` : "" }}</span>
    </div>
    <div v-if="failed" class="avatar-fallback">
      <img :src="previewUrl" alt="Teacher avatar preview" />
      <span>Static teacher mode</span>
    </div>
    <div v-if="speaking" class="speaking-pill">
      <span aria-hidden="true"></span>
      Gemma is speaking
    </div>
  </div>
</template>

<style scoped>
.avatar-stage {
  position: absolute;
  inset: 0;
  overflow: hidden;
}

.avatar-stage :deep(canvas) {
  width: 100%;
  height: 100%;
  display: block;
}

.avatar-status,
.avatar-fallback {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: grid;
  place-content: center;
  justify-items: center;
  gap: 12px;
  color: #38544b;
  font-weight: 750;
}

.avatar-fallback img {
  width: min(46vw, 430px);
  max-height: 78vh;
  object-fit: contain;
  filter: drop-shadow(0 24px 32px rgb(36 68 54 / 0.2));
}

.loader-ring {
  width: 38px;
  height: 38px;
  border: 4px solid rgb(41 107 81 / 0.18);
  border-top-color: #296b51;
  border-radius: 50%;
  animation: spin 800ms linear infinite;
}

.speaking-pill {
  position: absolute;
  left: 50%;
  bottom: 17%;
  transform: translateX(-50%);
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 14px;
  border: 1px solid rgb(255 255 255 / 0.65);
  border-radius: 999px;
  color: #173b2f;
  background: rgb(255 255 255 / 0.82);
  box-shadow: 0 12px 30px rgb(34 71 57 / 0.15);
  backdrop-filter: blur(12px);
  font-size: 12px;
  font-weight: 800;
}

.speaking-pill span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ef8f64;
  box-shadow: 0 0 0 5px rgb(239 143 100 / 0.18);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>

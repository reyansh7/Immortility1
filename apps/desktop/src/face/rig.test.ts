import * as THREE from "three";
import { describe, expect, it } from "vitest";
import { faceLabel, type FaceState } from "./faceState";
import {
  EXPRESSIONS,
  blinkAmount,
  effectivePower,
  frameBudget,
  graphicsHint,
  jawOpen,
  pixelRatioCap,
  envelope,
  nextBlink,
  speechEnergy,
  syllable,
} from "./rig";
import { BoneDriver } from "./boneDriver";

describe("expressions", () => {
  it("defines a look for every face state", () => {
    for (const state of Object.keys(faceLabel) as FaceState[])
      expect(EXPRESSIONS[state]).toBeDefined();
  });
  it("dims the eyes when disconnected and brightens them when listening", () => {
    expect(EXPRESSIONS.disconnected.eye).toBeLessThan(EXPRESSIONS.idle.eye);
    expect(EXPRESSIONS.listening.eye).toBeGreaterThan(EXPRESSIONS.idle.eye);
  });
});

describe("palette", () => {
  it("keeps every working state inside the crimson family", () => {
    for (const [state, look] of Object.entries(EXPRESSIONS)) {
      if (state === "disconnected") continue;
      const r = parseInt(look.hue.slice(1, 3), 16);
      const g = parseInt(look.hue.slice(3, 5), 16);
      const b = parseInt(look.hue.slice(5, 7), 16);
      expect(r).toBeGreaterThan(g * 1.8);
      expect(r).toBeGreaterThan(b * 1.6);
    }
  });
});

describe("frame budget", () => {
  const options = {
    quality: "balanced" as const,
    compact: false,
    active: false,
    reduced: false,
    visible: true,
  };
  it("idles below the active rate and stops when hidden", () => {
    expect(frameBudget(options)).toBeLessThan(
      frameBudget({ ...options, active: true }),
    );
    expect(frameBudget({ ...options, visible: false })).toBe(0);
    expect(frameBudget({ ...options, quality: "2d" })).toBe(0);
  });
  it("keeps the companion cheap and honours reduced motion", () => {
    expect(frameBudget({ ...options, compact: true })).toBeLessThanOrEqual(12);
    expect(frameBudget({ ...options, reduced: true })).toBe(0);
  });
  it("idles slowly and keeps interaction frames under each launch profile", () => {
    expect(effectivePower("auto", true)).toBe("battery");
    expect(effectivePower("auto", false)).toBe("performance");
    const idle = frameBudget({ ...options, power: "performance" });
    const active = frameBudget({
      ...options,
      power: "performance",
      active: true,
    });
    expect(idle).toBeLessThanOrEqual(12);
    expect(active).toBe(60);
    expect(frameBudget({ ...options, power: "battery" })).toBeLessThanOrEqual(
      8,
    );
    expect(pixelRatioCap({ ...options, power: "battery" })).toBe(1);
    expect(
      pixelRatioCap({ ...options, quality: "high", power: "performance" }),
    ).toBe(1.75);
    expect(graphicsHint("auto", true)).toBe("low-power");
    expect(graphicsHint("performance", true)).toBe("high-performance");
  });
});

describe("speech", () => {
  it("never opens the jaw without a reported level", () => {
    expect(jawOpen(0, 1)).toBe(0);
    expect(jawOpen(1, 1)).toBeLessThanOrEqual(0.8);
  });
  it("maps playback RMS into 0..1", () => {
    expect(speechEnergy(0)).toBe(0);
    expect(speechEnergy(0.1)).toBeCloseTo(0.4);
    expect(speechEnergy(2)).toBe(1);
  });
  it("attacks faster than it releases", () => {
    const up = envelope(0, 1, 0.05);
    const down = 1 - envelope(1, 0, 0.05);
    expect(up).toBeGreaterThan(down);
  });
  it("keeps the syllable rhythm in range", () => {
    for (let t = 0; t < 5; t += 0.013) {
      const value = syllable(t);
      expect(value).toBeGreaterThanOrEqual(0);
      expect(value).toBeLessThanOrEqual(1);
    }
  });
});

describe("blinking", () => {
  it("closes then reopens within the blink length", () => {
    expect(blinkAmount(-0.01)).toBe(0);
    expect(blinkAmount(0.068)).toBeCloseTo(1);
    expect(blinkAmount(0.2)).toBe(0);
  });
  it("schedules natural intervals and occasional double blinks", () => {
    expect(nextBlink(() => 0.05)).toBeCloseTo(0.22);
    const interval = nextBlink(() => 0.5);
    expect(interval).toBeGreaterThan(2);
    expect(interval).toBeLessThan(6.5);
  });
});

describe("BoneDriver", () => {
  it("applies rig-space pitch regardless of the parent's orientation", () => {
    const rig = new THREE.Group();
    const parent = new THREE.Object3D();
    parent.quaternion.setFromEuler(new THREE.Euler(0.4, 1.1, -0.3));
    const bone = new THREE.Object3D();
    const tip = new THREE.Object3D();
    rig.add(parent);
    parent.add(bone);
    bone.add(tip);
    // Place the tip one unit in front of the bone pivot, in rig space.
    rig.updateMatrixWorld(true);
    const forward = new THREE.Vector3(0, 0, 1).applyQuaternion(
      bone.getWorldQuaternion(new THREE.Quaternion()).invert(),
    );
    tip.position.copy(forward);
    const driver = new BoneDriver(bone, rig);
    driver.set(Math.PI / 2, 0, 0);
    rig.updateMatrixWorld(true);
    const pivot = bone.getWorldPosition(new THREE.Vector3());
    const end = tip.getWorldPosition(new THREE.Vector3()).sub(pivot);
    // +X pitch swings a forward-pointing chin straight down.
    expect(end.x).toBeCloseTo(0, 5);
    expect(end.y).toBeCloseTo(-1, 5);
    expect(end.z).toBeCloseTo(0, 5);
  });
  it("offsets in rig space and restores the rest pose", () => {
    const rig = new THREE.Group();
    const parent = new THREE.Object3D();
    parent.rotation.set(0, Math.PI / 2, 0);
    parent.scale.setScalar(2);
    const bone = new THREE.Object3D();
    rig.add(parent);
    parent.add(bone);
    const driver = new BoneDriver(bone, rig);
    rig.updateMatrixWorld(true);
    const rest = bone.getWorldPosition(new THREE.Vector3());
    driver.set(0, 0, 0, new THREE.Vector3(0.5, 0, 0));
    rig.updateMatrixWorld(true);
    const moved = bone.getWorldPosition(new THREE.Vector3()).sub(rest);
    expect(moved.x).toBeCloseTo(0.5, 5);
    expect(moved.z).toBeCloseTo(0, 5);
    driver.set(0, 0, 0);
    rig.updateMatrixWorld(true);
    expect(
      bone.getWorldPosition(new THREE.Vector3()).distanceTo(rest),
    ).toBeCloseTo(0, 6);
  });
});

describe("speech energy safety", () => {
  it("treats an invalid playback meter as silence", () => {
    expect(speechEnergy(Number.NaN)).toBe(0);
    expect(speechEnergy(Infinity)).toBe(0);
    expect(speechEnergy(0.12)).toBeCloseTo(0.48);
  });
});

import * as THREE from "three";

/**
 * Drives one bone with head-space rotations/offsets regardless of how the
 * exporter oriented its local axes. Rest pose is captured once.
 */
export class BoneDriver {
  readonly bone: THREE.Object3D;
  private readonly restQ: THREE.Quaternion;
  private readonly restP: THREE.Vector3;
  private readonly restS: THREE.Vector3;
  /** Rotation of the parent in rig space, and its inverse. */
  private readonly parentQ: THREE.Quaternion;
  private readonly parentQi: THREE.Quaternion;
  private readonly parentScale: number;
  /** Local axis index most aligned with rig-space up (for squash/blink). */
  readonly upAxis: 0 | 1 | 2;
  private readonly tmpQ = new THREE.Quaternion();
  private readonly tmpE = new THREE.Euler(0, 0, 0, "YXZ");
  private readonly tmpV = new THREE.Vector3();

  constructor(bone: THREE.Object3D, rig: THREE.Object3D) {
    this.bone = bone;
    this.restQ = bone.quaternion.clone();
    this.restP = bone.position.clone();
    this.restS = bone.scale.clone();
    rig.updateMatrixWorld(true);
    const rigQi = rig.getWorldQuaternion(new THREE.Quaternion()).invert();
    const parent = bone.parent ?? rig;
    this.parentQ = rigQi
      .clone()
      .multiply(parent.getWorldQuaternion(new THREE.Quaternion()));
    this.parentQi = this.parentQ.clone().invert();
    const rigScale = rig.getWorldScale(new THREE.Vector3()).x || 1;
    this.parentScale =
      parent.getWorldScale(new THREE.Vector3()).x / rigScale || 1;
    const boneQ = this.parentQ.clone().multiply(this.restQ);
    const up = new THREE.Vector3(0, 1, 0).applyQuaternion(boneQ.invert());
    const abs = [Math.abs(up.x), Math.abs(up.y), Math.abs(up.z)];
    this.upAxis =
      abs[0] >= abs[1] && abs[0] >= abs[2] ? 0 : abs[1] >= abs[2] ? 1 : 2;
  }

  /** Applies a rig-space rotation (pitch X, yaw Y, roll Z) about the bone pivot plus a rig-space offset. */
  set(
    pitch: number,
    yaw: number,
    roll = 0,
    offset?: THREE.Vector3,
    squash = 1,
  ): void {
    this.tmpE.set(pitch, yaw, roll, "YXZ");
    this.tmpQ.setFromEuler(this.tmpE);
    // local = parentQ⁻¹ · R · parentQ · rest
    this.bone.quaternion
      .copy(this.parentQi)
      .multiply(this.tmpQ)
      .multiply(this.parentQ)
      .multiply(this.restQ);
    this.bone.position.copy(this.restP);
    if (offset) {
      this.tmpV
        .copy(offset)
        .applyQuaternion(this.parentQi)
        .divideScalar(this.parentScale);
      this.bone.position.add(this.tmpV);
    }
    this.bone.scale.copy(this.restS);
    if (squash !== 1)
      this.bone.scale.setComponent(
        this.upAxis,
        this.restS.getComponent(this.upAxis) * squash,
      );
  }
}

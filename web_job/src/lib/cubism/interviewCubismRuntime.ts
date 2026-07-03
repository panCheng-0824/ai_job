import { CubismFramework, LogLevel, Option } from "@framework/live2dcubismframework";
import { LAppPal } from "./demo/lapppal";
import { LAppSubdelegate } from "./demo/lappsubdelegate";

export type CubismPresenceState = "idle" | "listening" | "speaking" | "thinking";

let frameworkStarted = false;
let frameworkRefCount = 0;

function ensureFramework(): void {
  if (frameworkStarted) return;
  LAppPal.updateTime();
  const option = new Option();
  option.logFunction = LAppPal.printMessage;
  option.loggingLevel = LogLevel.LogLevel_Warning;
  CubismFramework.startUp(option);
  CubismFramework.initialize();
  frameworkStarted = true;
}

function retainFramework(): void {
  ensureFramework();
  frameworkRefCount += 1;
}

function releaseFramework(): void {
  frameworkRefCount = Math.max(0, frameworkRefCount - 1);
  if (frameworkRefCount === 0 && frameworkStarted) {
    CubismFramework.dispose();
    frameworkStarted = false;
  }
}

export class InterviewCubismRuntime {
  #canvas: HTMLCanvasElement;
  #subdelegate: LAppSubdelegate | null = null;
  #rafId = 0;
  #running = false;
  #lastState: CubismPresenceState | null = null;
  #pendingState: CubismPresenceState | null = null;
  #pendingModel: string | null = null;
  #currentModel = "Haru";

  constructor(canvas: HTMLCanvasElement) {
    this.#canvas = canvas;
  }

  async start(): Promise<boolean> {
    retainFramework();

    const subdelegate = new LAppSubdelegate();
    if (!subdelegate.initialize(this.#canvas)) {
      releaseFramework();
      return false;
    }

    this.#subdelegate = subdelegate;
    this.#running = true;

    const loop = (): void => {
      if (!this.#running || !this.#subdelegate) return;
      LAppPal.updateTime();
      this.#subdelegate.update();
      this.#flushPendingState();
      this.#rafId = requestAnimationFrame(loop);
    };
    this.#rafId = requestAnimationFrame(loop);
    return true;
  }

  stop(): void {
    this.#running = false;
    if (this.#rafId) cancelAnimationFrame(this.#rafId);
    this.#rafId = 0;
    this.#subdelegate?.release();
    this.#subdelegate = null;
    this.#lastState = null;
    releaseFramework();
  }

  applyPresenceState(state: CubismPresenceState): void {
    this.#pendingState = state;
    this.#flushPendingState();
  }

  setModel(modelName: string): void {
    if (!modelName || modelName === this.#currentModel) return;
    this.#currentModel = modelName;
    this.#lastState = null;
    this.#pendingModel = modelName;
    this.#subdelegate?.getLive2DManager()?.changeModel(modelName);
  }

  getModel(): string {
    return this.#currentModel;
  }

  executeCommand(cmd: {
    type: "expression" | "motion" | "hit";
    id?: string;
    group?: string;
    index?: number;
    area?: string;
  }): void {
    const manager = this.#subdelegate?.getLive2DManager();
    if (!manager?.isModelReady() || !cmd?.type) return;

    switch (cmd.type) {
      case "expression":
        if (cmd.id) manager.playExpression(cmd.id);
        break;
      case "motion":
        if (cmd.group != null) manager.playMotion(cmd.group, cmd.index ?? 0);
        break;
      case "hit":
        if (cmd.area) manager.playHitInteraction(cmd.area);
        break;
      default:
        break;
    }
  }

  #flushPendingState(): void {
    if (this.#pendingModel) {
      const manager = this.#subdelegate?.getLive2DManager();
      if (!manager?.isModelReady()) return;
      if (manager.getCurrentModelName() !== this.#pendingModel) return;
      this.#pendingModel = null;
      this.#lastState = null;
    }
    if (this.#pendingState == null) return;
    const manager = this.#subdelegate?.getLive2DManager();
    if (!manager?.isModelReady()) return;
    if (this.#pendingState === this.#lastState) {
      this.#pendingState = null;
      return;
    }
    manager.applyPresenceState(this.#pendingState);
    this.#lastState = this.#pendingState;
    this.#pendingState = null;
  }
}

declare global {
  interface Window {
    Live2DCubismCore?: unknown;
  }
}

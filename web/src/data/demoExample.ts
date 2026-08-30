/**
 * Pre-computed clean vs watermarked gallery for first-load "see it working".
 * Fixtures are real TransformersBackend offline output (Qwen2.5-0.5B by default)
 * — not toy tokens and not hand-faked scores. Regenerate with
 * scripts/generate_demo_example.py. Runtime still defaults to the weightless
 * built-in engine; only this JSON ships.
 */
import type {
  BranchState,
  DetectionSnapshot,
  GenerationLiveState,
  TokenEvent,
} from "../types/generation";
import galleryJson from "./demo-gallery.json";

export type DemoProfileMeta = {
  id: string;
  name: string;
  gamma: number;
  delta: number;
  context_width: number;
  ignore_repeated_ngrams: boolean;
  z_threshold: number;
  min_scored_tokens: number;
};

export type DemoExample = {
  id: string;
  label: string;
  strength_label?: string;
  prompt: string;
  seed: number;
  max_new_tokens: number;
  temperature?: number;
  /** "coupled_crn" when clean/loaded share common random numbers. */
  sampling?: string;
  profile_id: string;
  profile?: DemoProfileMeta;
  key_fingerprint: string;
  engine: string;
  model?: string;
  note: string;
  /** Measured fraction of aligned positions where token ids differ. */
  flip_rate?: number;
  flipped_tokens?: number;
  aligned_tokens?: number;
  match_prefix?: number;
  control: BranchState;
  loaded: BranchState;
};

export type DemoGallery = {
  version: number;
  model: string;
  engine: string;
  sampling?: string;
  key_fingerprint: string;
  note: string;
  examples: DemoExample[];
};

export const DEMO_GALLERY = galleryJson as DemoGallery;

/** First gallery entry — default selection on load. */
export const DEMO_EXAMPLE: DemoExample = DEMO_GALLERY.examples[0]!;

export function getDemoExample(id: string | null | undefined): DemoExample {
  if (!id) return DEMO_EXAMPLE;
  return DEMO_GALLERY.examples.find((e) => e.id === id) ?? DEMO_EXAMPLE;
}

export function exampleToLiveState(example: DemoExample): GenerationLiveState {
  const control: BranchState = {
    text: example.control.text,
    tokens: example.control.tokens as TokenEvent[],
    detection: example.control.detection as DetectionSnapshot,
  };
  const loaded: BranchState = {
    text: example.loaded.text,
    tokens: example.loaded.tokens as TokenEvent[],
    detection: example.loaded.detection as DetectionSnapshot,
  };
  return {
    generationId: `demo:${example.id}`,
    status: "completed",
    error: null,
    keyFingerprint: example.key_fingerprint,
    control,
    loaded,
    lastSeq: 0,
  };
}

/** @deprecated use exampleToLiveState(DEMO_EXAMPLE) */
export function demoToLiveState(): GenerationLiveState {
  return exampleToLiveState(DEMO_EXAMPLE);
}

export function formatStrength(example: DemoExample): string {
  const p = example.profile;
  if (!p) return example.strength_label ?? "default";
  const strength = example.strength_label ?? "default";
  return `${strength} · δ ${p.delta}`;
}

export function loadedZ(example: DemoExample): number {
  return example.loaded.detection?.z_score ?? 0;
}

export function controlZ(example: DemoExample): number {
  return example.control.detection?.z_score ?? 0;
}

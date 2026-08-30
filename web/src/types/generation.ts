export type BranchLabel = "control" | "loaded";

export type DetectionSnapshot = {
  num_tokens_total: number;
  num_tokens_scored: number;
  num_green: number;
  expected_green: number;
  green_fraction: number | null;
  z_score: number;
  p_value: number;
  detected: boolean;
  threshold: number;
  excluded_prefix_count: number;
  excluded_repeated_count: number;
  excluded_other_count: number;
  verdict: "insufficient_scored_tokens" | "no_evidence" | "detected";
  verdict_label: string;
};

export type CandidateProb = {
  token_id: number;
  text: string;
  probability: number;
  favored: boolean;
};

export type TokenEvent = {
  position: number;
  token_id: number;
  text: string;
  favored: boolean;
  eligible: boolean;
  exclusion_reason: string | null;
  z_score: number;
  p_value: number;
  green_count: number;
  scored_count: number;
  base_probability?: number;
  biased_probability?: number | null;
  final_sampling_probability?: number;
  base_logit?: number;
  biased_logit?: number | null;
  entropy?: number;
  context_ids?: number[];
  top_candidates_before?: CandidateProb[];
  top_candidates_after?: CandidateProb[];
  text_so_far?: string;
  detection?: DetectionSnapshot;
};

export type StreamEvent = {
  v: number;
  type: string;
  generation_id?: string;
  seq: number;
  branch?: BranchLabel;
  message?: string;
  position?: number;
  token_id?: number;
  text?: string;
  favored?: boolean;
  eligible?: boolean;
  exclusion_reason?: string | null;
  z_score?: number;
  p_value?: number;
  green_count?: number;
  scored_count?: number;
  latency_ms?: number;
  base_probability?: number;
  biased_probability?: number | null;
  final_sampling_probability?: number;
  base_logit?: number;
  biased_logit?: number | null;
  entropy?: number;
  context_ids?: number[];
  top_candidates_before?: CandidateProb[];
  top_candidates_after?: CandidateProb[];
  text_so_far?: string;
  detection?: DetectionSnapshot;
  model_mode?: string;
  profile_id?: string;
  key_fingerprint?: string;
  seed?: number;
  max_new_tokens?: number;
};

export type CreateGenerationResponse = {
  generation_id: string;
  status: string;
  model_mode: string;
  profile_id: string;
  key_fingerprint: string;
  seed: number;
  max_new_tokens: number;
};

export type BranchState = {
  text: string;
  tokens: TokenEvent[];
  detection: DetectionSnapshot | null;
};

export type GenerationLiveState = {
  generationId: string | null;
  status: "idle" | "running" | "completed" | "stopped" | "failed" | "busy";
  error: string | null;
  keyFingerprint: string | null;
  control: BranchState;
  loaded: BranchState;
  lastSeq: number;
};

export const emptyBranch = (): BranchState => ({
  text: "",
  tokens: [],
  detection: null,
});

export const emptyGenerationState = (): GenerationLiveState => ({
  generationId: null,
  status: "idle",
  error: null,
  keyFingerprint: null,
  control: emptyBranch(),
  loaded: emptyBranch(),
  lastSeq: 0,
});

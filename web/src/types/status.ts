export type AppStatus = {
  name: string;
  version: string;
  model_mode: string;
  model_ready: boolean;
  app_ready: boolean;
  telemetry: boolean;
  host: string;
  port: number;
  fake_sample: string | null;
};

export type ReadyStatus = {
  ready: boolean;
  app_ready: boolean;
  model_ready: boolean;
  model_mode: string;
  version: string;
  detail: string;
};

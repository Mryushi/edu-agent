export interface StandaloneConfig {
  deploymentUrl: string;
  assistantId: string;
  langsmithApiKey?: string;
}
// eslint-disable  MC8yOmFIVnBZMlhsc3JQbGxydm5uN002U1hkdmVRPT06NDk0YjhjODc=

const CONFIG_KEY = "deep-agent-config";

export function getConfig(): StandaloneConfig | null {
  if (typeof window === "undefined") return null;

  const stored = localStorage.getItem(CONFIG_KEY);
  if (!stored) return null;

  try {
    return JSON.parse(stored);
  } catch {
    return null;
  }
}
// NOTE  MS8yOmFIVnBZMlhsc3JQbGxydm5uN002U1hkdmVRPT06NDk0YjhjODc=

export function saveConfig(config: StandaloneConfig): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(CONFIG_KEY, JSON.stringify(config));
}

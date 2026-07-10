export type BackendReadiness = {
  status: string;
  database: string;
  market_data: string;
  primary_provider: string;
  unavailable_providers: string[];
};

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function getBackendReadiness(): Promise<BackendReadiness | null> {
  try {
    const response = await fetch(`${backendUrl}/ready`, {
      cache: "no-store",
      signal: AbortSignal.timeout(3000),
    });
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as BackendReadiness;
  } catch {
    return null;
  }
}

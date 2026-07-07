// Typed API client for the MTO backend.
//
// The backend URL is configurable via NEXT_PUBLIC_API_URL so the frontend
// can point at a different host in production. Defaults to localhost:8000
// for local dev.

export type Category =
  | 'PIPE'
  | 'FITTING'
  | 'FLANGE'
  | 'VALVE'
  | 'GASKET'
  | 'BOLT'
  | 'SUPPORT';

export type EndType = 'BW' | 'SW' | 'THD' | 'FLGD';

export interface MTOItem {
  item_no: number;
  category: Category;
  description: string;
  size_nps: string | null;
  schedule_rating: string | null;
  material_spec: string | null;
  end_type: EndType | null;
  quantity: number;
  unit: string;
  length_m: number | null;
  confidence: number | null;
  remarks: string | null;
}

export interface DrawingMeta {
  drawing_no: string | null;
  revision: string | null;
  line_number: string | null;
  nps: string | null;
  material_class: string | null;
  service: string | null;
}

export interface Summary {
  total_pipe_length_m: number;
  fittings: number;
  flanges: number;
  valves: number;
  gaskets: number;
  bolt_sets: number;
  field_welds: number;
}

export interface MTO {
  drawing_meta: DrawingMeta;
  items: MTOItem[];
  summary: Summary;
  source: string;
}

export type JobState = 'pending' | 'processing' | 'done' | 'error';

export interface JobResponse {
  job_id: string;
  state: JobState;
  message: string | null;
  filename: string;
  created_at: string;
  updated_at: string;
  mto: MTO | null;
}

export interface ApiError {
  detail: string;
  code: string;
}

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const MAX_FILE_SIZE_MB = 20;
export const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;
export const ACCEPTED_TYPES = ['image/png', 'image/jpeg', 'application/pdf'];
export const ACCEPTED_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.pdf'];

export class ApiError extends Error {
  code: string;
  constructor(message: string, code: string) {
    super(message);
    this.code = code;
    this.name = 'ApiError';
  }
}

async function parseError(res: Response): Promise<ApiError> {
  try {
    const body = (await res.json()) as { detail: unknown; code?: string };
    const message =
      typeof body.detail === 'string'
        ? body.detail
        : JSON.stringify(body.detail);
    return new ApiError(message, body.code || 'ERROR');
  } catch {
    return new ApiError(`HTTP ${res.status}`, 'ERROR');
  }
}

export async function uploadFile(
  file: File,
  onProgress?: (pct: number) => void
): Promise<{ job_id: string }> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API_URL}/api/upload`);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    };
    xhr.onload = () => {
      if (xhr.status === 202) {
        try {
          resolve(JSON.parse(xhr.responseText));
        } catch {
          reject(new ApiError('Invalid response from server', 'ERROR'));
        }
      } else {
        // Parse error from response body
        try {
          const body = JSON.parse(xhr.responseText);
          reject(
            new ApiError(
              typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail),
              body.code || 'ERROR'
            )
          );
        } catch {
          reject(new ApiError(`HTTP ${xhr.status}`, 'ERROR'));
        }
      }
    };
    xhr.onerror = () =>
      reject(
        new ApiError(
          'Network error — is the backend running on ' + API_URL + '?',
          'NETWORK'
        )
      );
    const form = new FormData();
    form.append('file', file);
    xhr.send(form);
  });
}

export async function getJob(jobId: string): Promise<JobResponse> {
  const res = await fetch(`${API_URL}/api/mto/${jobId}`);
  if (!res.ok) throw await parseError(res);
  return res.json();
}

export function getCsvUrl(jobId: string): string {
  return `${API_URL}/api/mto/${jobId}/csv`;
}

export async function getHealth(): Promise<{
  status: string;
  provider: string;
}> {
  const res = await fetch(`${API_URL}/api/health`);
  if (!res.ok) throw await parseError(res);
  return res.json();
}

export { API_URL };

import {
  RunSummary,
  RunDetail,
  EventItem,
  SystemHealth,
  SampleData,
  HandoffItem,
} from '../types';
import { requireSupabase } from './supabase';

const BASE_URL = '/api';

async function authorizedFetch(url: string, init?: RequestInit): Promise<Response> {
  const { data, error } = await requireSupabase().auth.getSession();
  if (error) throw new Error(error.message);
  if (!data.session) throw new Error('Your session has expired. Sign in again.');

  const headers = new Headers(init?.headers);
  headers.set('Authorization', `Bearer ${data.session.access_token}`);
  return fetch(url, { ...init, headers });
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const responseText = await res.text();
    let errorDetail = responseText || 'API request failed';
    try {
      const errorJson = JSON.parse(responseText);
      errorDetail = errorJson.detail || errorDetail;
    } catch {
      // Keep the raw response body when the server does not return JSON.
    }
    throw new Error(errorDetail || `HTTP error ${res.status}`);
  }
  return res.json();
}

export const api = {
  async getHealth(): Promise<SystemHealth> {
    const res = await fetch(`${BASE_URL}/health`);
    return handleResponse<SystemHealth>(res);
  },

  async getSamples(): Promise<SampleData> {
    const res = await fetch(`${BASE_URL}/samples`);
    return handleResponse<SampleData>(res);
  },

  async listRuns(): Promise<RunSummary[]> {
    const res = await authorizedFetch(`${BASE_URL}/runs`);
    return handleResponse<RunSummary[]>(res);
  },

  async getRun(runId: string): Promise<RunDetail> {
    const res = await authorizedFetch(`${BASE_URL}/runs/${runId}`);
    return handleResponse<RunDetail>(res);
  },

  async createRun(data: {
    title: string;
    transcript: string;
    company_rules: string;
    max_review_cycles?: number;
    fault_injection?: string | null;
  }): Promise<{ id: string; status: string; message: string }> {
    const res = await authorizedFetch(`${BASE_URL}/runs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse(res);
  },

  async getEvents(runId: string): Promise<EventItem[]> {
    const res = await authorizedFetch(`${BASE_URL}/runs/${runId}/events`);
    return handleResponse<EventItem[]>(res);
  },

  async getHandoffs(runId: string): Promise<HandoffItem[]> {
    const res = await authorizedFetch(`${BASE_URL}/runs/${runId}/handoffs`);
    return handleResponse<HandoffItem[]>(res);
  },

  async resumeRun(runId: string): Promise<{ status: string; message: string }> {
    const res = await authorizedFetch(`${BASE_URL}/runs/${runId}/resume`, {
      method: 'POST',
    });
    return handleResponse(res);
  },

  async resetRun(runId: string): Promise<{ status: string; message: string }> {
    const res = await authorizedFetch(`${BASE_URL}/runs/${runId}/reset`, {
      method: 'POST',
    });
    return handleResponse(res);
  },

  async submitCorrection(
    runId: string,
    data: {
      fact_id: string;
      field_name: string;
      corrected_value: string;
      correction_note?: string;
    }
  ): Promise<{ status: string; message: string; source_version: number }> {
    const res = await authorizedFetch(`${BASE_URL}/runs/${runId}/corrections`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse(res);
  },
};

// Shared API types used across admin UI

export interface Job {
  id: number;
  title: string;
  description: string;
  created_at: string;
}

export interface Candidate {
  id: number;
  name: string;
  email: string;
  phone?: string;
  linkedin_url?: string;
  resume_url?: string;
  job_id?: number;
  token: string;
  expires_at: string;
  created_at: string;
}

export interface Interview {
  id: number;
  job_id: number;
  candidate_id: number;
  status: string;
  created_at: string;
  completed_at?: string;
  audio_url?: string;
  video_url?: string;
  candidate?: Candidate;
  job?: Job;
  overall_score?: number;
}



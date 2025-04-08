import axios from 'axios';
import { endpoints } from '../config';

// Create axios instance
const api = axios.create({
  baseURL: endpoints.base,
  headers: {
    'Content-Type': 'application/json',
  },
});

// API functions for jobs
export const jobsApi = {
  getAll: async () => {
    const response = await api.get(endpoints.jobs);
    return response.data;
  },
  getById: async (id) => {
    const response = await api.get(`${endpoints.jobs}/${id}`);
    return response.data;
  },
  create: async (jobData) => {
    const response = await api.post(endpoints.jobs, jobData);
    return response.data;
  },
};

// API functions for candidates
export const candidatesApi = {
  getAll: async () => {
    const response = await api.get(endpoints.candidates);
    return response.data;
  },
  getById: async (id) => {
    const response = await api.get(`${endpoints.candidates}/${id}`);
    return response.data;
  },
  create: async (candidateData) => {
    const response = await api.post(endpoints.candidates, candidateData);
    return response.data;
  },
  uploadResume: async (candidateId, file) => {
    const formData = new FormData();
    formData.append('candidate_id', candidateId);
    formData.append('resume_file', file);
    
    const response = await axios.post(endpoints.uploadResume, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    return response.data;
  },
};

// API functions for matches
export const matchesApi = {
  getAll: async () => {
    const response = await api.get(endpoints.matches);
    return response.data;
  },
  getById: async (id) => {
    const response = await api.get(`${endpoints.matches}/${id}`);
    return response.data;
  },
  create: async (matchData) => {
    const response = await api.post(endpoints.matches, matchData);
    return response.data;
  },
};

// API functions for interviews
export const interviewsApi = {
  getAll: async () => {
    const response = await api.get(endpoints.interviews);
    return response.data;
  },
  getById: async (id) => {
    const response = await api.get(`${endpoints.interviews}/${id}`);
    return response.data;
  },
  create: async (interviewData) => {
    const response = await api.post(endpoints.interviews, interviewData);
    return response.data;
  },
};

// Health check
export const checkHealth = async () => {
  try {
    const response = await api.get(endpoints.health);
    return response.data.status === 'healthy';
  } catch (error) {
    console.error('Health check failed:', error);
    return false;
  }
};

export default {
  jobs: jobsApi,
  candidates: candidatesApi,
  matches: matchesApi,
  interviews: interviewsApi,
  checkHealth,
}; 
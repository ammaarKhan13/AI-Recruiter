// API configuration
const API_URL = "http://localhost:8000";

export const endpoints = {
  base: API_URL,
  health: `${API_URL}/health`,
  jobs: `${API_URL}/api/jobs`,
  candidates: `${API_URL}/api/candidates`,
  matches: `${API_URL}/api/matches`,
  interviews: `${API_URL}/api/interviews`,
  uploadResume: `${API_URL}/api/candidates/upload-resume`,
  process: `${API_URL}/api/process`
};

export default {
  apiUrl: API_URL,
  endpoints
}; 
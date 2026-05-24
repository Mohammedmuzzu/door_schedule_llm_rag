const FASTBID24_LOCAL_HOSTS = new Set(['127.0.0.1', 'localhost', '']);
const FASTBID24_DEFAULT_API = FASTBID24_LOCAL_HOSTS.has(window.location.hostname)
  ? 'http://127.0.0.1:8765/api/v1'
  : 'https://door-schedule-llm-rag.onrender.com/api/v1';

window.FASTBID24_CONFIG = {
  apiBaseUrl: window.FASTBID24_API_BASE_URL || FASTBID24_DEFAULT_API,
  requireAuth: true,
  allowLocalDemo: false,
};

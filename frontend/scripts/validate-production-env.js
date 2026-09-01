const backendUrl = (process.env.REACT_APP_BACKEND_URL || '').trim();

if (!backendUrl) {
  throw new Error('REACT_APP_BACKEND_URL is required for a production build.');
}

let parsed;
try {
  parsed = new URL(backendUrl);
} catch {
  throw new Error('REACT_APP_BACKEND_URL must be a valid absolute URL.');
}

if (parsed.protocol !== 'https:') {
  throw new Error('REACT_APP_BACKEND_URL must use HTTPS for a production build.');
}

if (['localhost', '127.0.0.1', '::1'].includes(parsed.hostname)) {
  throw new Error('REACT_APP_BACKEND_URL cannot point to localhost in a production build.');
}

console.log(`Production API origin validated: ${parsed.origin}`);

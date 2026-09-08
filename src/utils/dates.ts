export function formatIST(value: any, fallback = 'Unknown time') {
  if (!value) return fallback;
  const d = new Date(String(value).replace(/^:/, ''));
  if (Number.isNaN(d.getTime())) return String(value);
  return new Intl.DateTimeFormat('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
    timeZone: 'Asia/Kolkata',
  }).format(d) + ' IST';
}

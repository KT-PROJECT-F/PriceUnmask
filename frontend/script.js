// Frontend track starts here. First task: fetch /api/health and show the result.
fetch("/api/health")
  .then((r) => r.json())
  .then((d) => {
    document.getElementById("status").textContent = `API: ${d.status}`;
  })
  .catch(() => {
    document.getElementById("status").textContent = "API not reachable";
  });

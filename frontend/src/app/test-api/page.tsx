"use client";

import { useEffect, useState } from "react";

export default function TestApiPage() {
  const [config, setConfig] = useState<any>({});
  const [health, setHealth] = useState<any>(null);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    setConfig({
      NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
      nodeEnv: process.env.NODE_ENV,
    });

    fetch("/api/v1/health")
      .then((res) => res.json())
      .then((data) => setHealth(data))
      .catch((err) => setError(err.message));
  }, []);

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-4">API Configuration Test</h1>
      
      <div className="mb-6">
        <h2 className="text-xl font-semibold mb-2">Environment Config:</h2>
        <pre className="bg-gray-100 p-4 rounded">{JSON.stringify(config, null, 2)}</pre>
      </div>

      <div className="mb-6">
        <h2 className="text-xl font-semibold mb-2">Health Check:</h2>
        {error && <div className="text-red-600">Error: {error}</div>}
        {health && <pre className="bg-gray-100 p-4 rounded">{JSON.stringify(health, null, 2)}</pre>}
      </div>

      <div className="mb-6">
        <h2 className="text-xl font-semibold mb-2">Direct Backend Test:</h2>
        <button
          onClick={() => {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
            const healthUrl = `${apiUrl.replace('/api/v1', '')}/api/v1/health`;
            fetch(healthUrl)
              .then((res) => res.json())
              .then((data) => alert("Direct backend works: " + JSON.stringify(data)))
              .catch((err) => alert("Direct backend error: " + err.message));
          }}
          className="bg-blue-500 text-white px-4 py-2 rounded"
        >
          Test Direct Backend Connection
        </button>
      </div>
    </div>
  );
}

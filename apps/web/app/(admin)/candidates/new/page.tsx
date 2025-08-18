"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";

export default function NewCandidatePage() {
  const [name,setName]=useState("");
  const [email,setEmail]=useState("");
  const [expiresInDays, setExpiresInDays] = useState(7); // Default 1 week
  const [error,setError]=useState<string|null>(null);
  const router=useRouter();
  const submit=async()=>{
    try{
      await apiFetch("/api/v1/candidates/",{
        method:"POST",
        body:JSON.stringify({name, email, expires_in_days: expiresInDays})
      });
      router.push("/candidates");
    }catch(e:any){ setError(e.message); }
  };
  return (
    <div style={{ padding: "1rem", maxWidth: "500px" }}>
      <h1>New Candidate</h1>
      {error && <p style={{color:"red"}}>{error}</p>}
      <div style={{ marginBottom: "1rem" }}>
        <label htmlFor="name">Name:</label>
        <input 
          id="name"
          value={name} 
          onChange={e=>setName(e.target.value)} 
          placeholder="Candidate name"
          style={{ width: "100%", padding: "0.5rem", marginTop: "0.25rem" }}
        />
      </div>
      <div style={{ marginBottom: "1rem" }}>
        <label htmlFor="email">Email:</label>
        <input 
          id="email"
          type="email"
          value={email} 
          onChange={e=>setEmail(e.target.value)} 
          placeholder="candidate@example.com"
          style={{ width: "100%", padding: "0.5rem", marginTop: "0.25rem" }}
        />
      </div>
      <div style={{ marginBottom: "1rem" }}>
        <label htmlFor="expires">Link Duration:</label>
        <select 
          id="expires"
          value={expiresInDays} 
          onChange={e=>setExpiresInDays(parseInt(e.target.value))}
          style={{ width: "100%", padding: "0.5rem", marginTop: "0.25rem" }}
        >
          <option value={1}>1 Day</option>
          <option value={3}>3 Days</option>
          <option value={7}>1 Week</option>
          <option value={14}>2 Weeks</option>
          <option value={30}>1 Month</option>
        </select>
      </div>
      <button 
        onClick={submit}
        style={{ 
          padding: "0.75rem 1.5rem", 
          backgroundColor: "#007bff", 
          color: "white", 
          border: "none", 
          borderRadius: "4px",
          cursor: "pointer"
        }}
      >
        Create Candidate
      </button>
    </div>
  );
} 
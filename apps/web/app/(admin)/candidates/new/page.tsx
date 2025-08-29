"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";

export default function NewCandidatePage() {
  const [name,setName]=useState("");
  const [email,setEmail]=useState("");
  const [phone,setPhone]=useState("");
  const [linkedin,setLinkedin]=useState("");
  const [expiresInDays, setExpiresInDays] = useState(7); // Default 1 week
  const [error,setError]=useState<string|null>(null);
  const router=useRouter();
  const submit=async()=>{
    try{
      await apiFetch("/api/v1/candidates/",{
        method:"POST",
        body:JSON.stringify({name, email, phone, linkedin_url: linkedin, expires_in_days: expiresInDays})
      });
      router.push("/candidates");
    }catch(e:any){ setError(e.message); }
  };
  return (
    <div style={{ padding: "1rem", maxWidth: "500px" }}>
      <h1>Yeni Aday</h1>
      {error && <p style={{color:"red"}}>{error}</p>}
      <div style={{ marginBottom: "1rem" }}>
        <label htmlFor="name">Ad Soyad:</label>
        <input 
          id="name"
          value={name} 
          onChange={e=>setName(e.target.value)} 
          placeholder="Aday adı"
          style={{ width: "100%", padding: "0.5rem", marginTop: "0.25rem" }}
        />
      </div>
      <div style={{ marginBottom: "1rem" }}>
        <label htmlFor="phone">Telefon:</label>
        <input 
          id="phone"
          value={phone} 
          onChange={e=>setPhone(e.target.value)} 
          placeholder="05xx xxx xx xx veya +90..."
          style={{ width: "100%", padding: "0.5rem", marginTop: "0.25rem" }}
        />
      </div>
      <div style={{ marginBottom: "1rem" }}>
        <label htmlFor="linkedin">LinkedIn:</label>
        <input 
          id="linkedin"
          value={linkedin} 
          onChange={e=>setLinkedin(e.target.value)} 
          placeholder="linkedin.com/in/kullanici veya in/kullanici"
          style={{ width: "100%", padding: "0.5rem", marginTop: "0.25rem" }}
        />
      </div>
      <div style={{ marginBottom: "1rem" }}>
        <label htmlFor="email">E‑posta:</label>
        <input 
          id="email"
          type="email"
          value={email} 
          onChange={e=>setEmail(e.target.value)} 
          placeholder="aday@example.com"
          style={{ width: "100%", padding: "0.5rem", marginTop: "0.25rem" }}
        />
      </div>
      <div style={{ marginBottom: "1rem" }}>
        <label htmlFor="expires">Bağlantı Süresi:</label>
        <select 
          id="expires"
          value={expiresInDays} 
          onChange={e=>setExpiresInDays(parseInt(e.target.value))}
          style={{ width: "100%", padding: "0.5rem", marginTop: "0.25rem" }}
        >
          <option value={1}>1 Gün</option>
          <option value={3}>3 Gün</option>
          <option value={7}>1 Hafta</option>
          <option value={14}>2 Hafta</option>
          <option value={30}>1 Ay</option>
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
        Aday Oluştur
      </button>
    </div>
  );
} 
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login } from "../api/trialsApi.js";

export default function Login({ setAuth }) {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    try {
      const data = await login(email, password);
      setAuth({ loggedIn: true, userId: data.user_id, name: data.name });
      navigate("/");
    } catch (err) {
      setError("Invalid email or password");
    }
  }

  return (
    <div className="card narrow">
      <h2>Welcome back</h2>
      <p className="subtitle">Log in to manage clinical trial records.</p>
      {error && <div className="alert-error">{error}</div>}
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="email">Email</label>
          <input id="email" type="email" placeholder="you@example.com"
            value={email} onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <div className="form-group">
          <label htmlFor="password">Password</label>
          <input id="password" type="password" placeholder="Enter your password"
            value={password} onChange={(e) => setPassword(e.target.value)} required />
        </div>
        <button className="btn btn-primary" type="submit">Log in</button>
      </form>
    </div>
  );
}
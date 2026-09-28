import React, { useEffect, useState } from "react";
import { Routes, Route, Link, useNavigate } from "react-router-dom";

import Login from "./pages/Login.jsx";
import Home from "./pages/Home.jsx";
import CreateRecord from "./pages/CreateRecord.jsx";
import UpdateRecord from "./pages/UpdateRecord.jsx";
import DeleteRecord from "./pages/DeleteRecord.jsx";

import {
  me,
  logout,
  fetchTrials,
  createTrial,
  updateTrial,
  deleteTrial,
} from "./api/trialsApi.js";

export default function App() {
  const navigate = useNavigate();
  const [auth, setAuth] = useState({ loggedIn: false, userId: null, name: "" });
  const [trials, setTrials] = useState([]);
  const [loading, setLoading] = useState(false);

  // On page load: ask the backend if the cookie is still valid
  useEffect(() => {
    me()
      .then((d) => setAuth({ loggedIn: true, userId: d.user_id, name: "" }))
      .catch(() => setAuth({ loggedIn: false, userId: null, name: "" }));
  }, []);

  // Load trials whenever login state changes
  useEffect(() => {
    if (!auth.loggedIn) {
      setTrials([]);
      return;
    }
    setLoading(true);
    fetchTrials()
      .then(setTrials)
      .catch(() => setAuth({ loggedIn: false, userId: null, name: "" }))
      .finally(() => setLoading(false));
  }, [auth.loggedIn]);

  async function onAdd(newTrial) {
    const created = await createTrial(newTrial);
    setTrials((prev) => [...prev, created]);
    navigate("/");
  }

  async function onUpdate(id, updated) {
    const saved = await updateTrial(id, updated);
    setTrials((prev) => prev.map((t) => (t.id === id ? saved : t)));
    navigate("/");
  }

  async function onDelete(id) {
    await deleteTrial(id);
    setTrials((prev) => prev.filter((t) => t.id !== id));
    navigate("/");
  }

  async function handleLogout() {
    await logout();
    setAuth({ loggedIn: false, userId: null, name: "" });
    navigate("/");
  }

    return (
    <>
      <header className="navbar">
        <div className="navbar-inner">
          <span className="brand">Clinical Trial Registry</span>
          <nav className="nav-links">
            <Link to="/">Home</Link>
            {auth.loggedIn ? (
              <>
                <Link to="/create">Add Trial</Link>
                <button className="btn btn-light btn-sm" onClick={handleLogout}>
                  Logout
                </button>
              </>
            ) : (
              <Link to="/login">Login</Link>
            )}
          </nav>
        </div>
      </header>

      <main className="container">
        <Routes>
          <Route path="/" element={<Home trials={trials} loading={loading} auth={auth} />} />
          <Route path="/login" element={<Login setAuth={setAuth} />} />
          <Route path="/create" element={<CreateRecord onAdd={onAdd} />} />
          <Route path="/update/:id" element={<UpdateRecord trials={trials} onUpdate={onUpdate} />} />
          <Route path="/delete/:id" element={<DeleteRecord trials={trials} onDelete={onDelete} />} />
        </Routes>
      </main>
    </>
  );
}
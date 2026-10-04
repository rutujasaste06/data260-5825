import React, { useEffect, useState } from "react";
import { Routes, Route, Link, useNavigate } from "react-router-dom";
import { useDispatch } from "react-redux";

import Login from "./pages/Login.jsx";
import Home from "./pages/Home.jsx";
import CreateRecord from "./pages/CreateRecord.jsx";
import UpdateRecord from "./pages/UpdateRecord.jsx";
import DeleteRecord from "./pages/DeleteRecord.jsx";

import { me, logout } from "./api/trialsApi.js";
import { fetchTrials } from "./store/trialsSlice";

export default function App() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const [auth, setAuth] = useState({ loggedIn: false, userId: null, name: "" });

  // On page load: ask the backend if the cookie is still valid
  useEffect(() => {
    me()
      .then((d) => setAuth({ loggedIn: true, userId: d.user_id, name: "" }))
      .catch(() => setAuth({ loggedIn: false, userId: null, name: "" }));
  }, []);

  // Once logged in, tell Redux to load the trials
  useEffect(() => {
    if (auth.loggedIn) dispatch(fetchTrials());
  }, [auth.loggedIn, dispatch]);

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
                <button className="btn btn-light btn-sm" onClick={handleLogout}>Logout</button>
              </>
            ) : (
              <Link to="/login">Login</Link>
            )}
          </nav>
        </div>
      </header>

      <main className="container">
        <Routes>
          <Route path="/" element={<Home auth={auth} />} />
          <Route path="/login" element={<Login setAuth={setAuth} />} />
          <Route path="/create" element={<CreateRecord />} />
          <Route path="/update/:id" element={<UpdateRecord />} />
          <Route path="/delete/:id" element={<DeleteRecord />} />
        </Routes>
      </main>
    </>
  );
}
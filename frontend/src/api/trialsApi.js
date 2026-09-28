import axios from "axios";

// One shared axios instance. withCredentials makes the browser send the session cookie.
const api = axios.create({
  baseURL: "http://localhost:8425",
  withCredentials: true,
});

// ---------- Auth ----------
export const login = (email, password) =>
  api.post("/auth/login", { email, password }).then((r) => r.data);

export const logout = () => api.post("/auth/logout").then((r) => r.data);

export const me = () => api.get("/auth/me").then((r) => r.data);

// ---------- Trials CRUD ----------
export const fetchTrials = () => api.get("/trials").then((r) => r.data);

export const createTrial = (trial) =>
  api.post("/trials", trial).then((r) => r.data);

export const updateTrial = (id, trial) =>
  api.put(`/trials/${id}`, trial).then((r) => r.data);

export const deleteTrial = (id) =>
  api.delete(`/trials/${id}`).then((r) => r.data);
import React from "react";
import { Link } from "react-router-dom";
import { useSelector, useDispatch } from "react-redux";
import { deleteTrial } from "../store/trialsSlice";

export default function Home({ auth }) {
  const dispatch = useDispatch();
  const { items: trials, status, error } = useSelector((state) => state.trials);

  if (!auth.loggedIn) {
    return (
      <div className="card narrow">
        <h2>Login required</h2>
        <p className="subtitle">Please log in to view and manage trial records.</p>
        <Link className="btn btn-primary" to="/login">Go to Login</Link>
      </div>
    );
  }

  if (status === "loading") return <p className="empty">Loading...</p>;

  return (
    <div className="card">
      <div className="card-header">
        <h2>Clinical Trials</h2>
        <Link className="btn btn-primary" to="/create">+ Add Trial</Link>
      </div>
      {error && <div className="alert-error">{error}</div>}
      <table>
        <thead>
          <tr><th>ID</th><th>Trial Title</th><th>NCT Number</th><th>Slots</th><th>Sponsor</th><th>Actions</th></tr>
        </thead>
        <tbody>
          {[...trials].reverse().slice(0, 50).map((t) => (
            <tr key={t.id}>
              <td>{t.id}</td>
              <td>{t.trial_title}</td>
              <td><span className="badge">{t.nct_number}</span></td>
              <td>{t.available_slots}</td>
              <td>{t.sponsor_id ?? "-"}</td>
              <td>
                <div className="actions">
                  <Link className="btn btn-outline btn-sm" to={`/update/${t.id}`}>Edit</Link>
                  <button className="btn btn-danger btn-sm" onClick={() => dispatch(deleteTrial(t.id))}>Delete</button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
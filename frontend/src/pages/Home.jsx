import React from "react";
import { Link } from "react-router-dom";

export default function Home({ trials, loading, auth }) {
  if (!auth.loggedIn) {
    return (
      <div className="card narrow">
        <h2>Login required</h2>
        <p className="subtitle">Please log in to view and manage trial records.</p>
        <Link className="btn btn-primary" to="/login">Go to Login</Link>
      </div>
    );
  }

  if (loading) return <p className="empty">Loading...</p>;

  return (
    <div className="card">
      <div className="card-header">
        <h2>Clinical Trials</h2>
        <Link className="btn btn-primary" to="/create">+ Add Trial</Link>
      </div>

      {trials.length === 0 ? (
        <p className="empty">No trials yet. Click "Add Trial" to create one.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Trial Title</th>
              <th>NCT Number</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {trials.map((t) => (
              <tr key={t.id}>
                <td>{t.id}</td>
                <td>{t.trial_title}</td>
                <td><span className="badge">{t.nct_number}</span></td>
                <td>
                  <div className="actions">
                    <Link className="btn btn-outline btn-sm" to={`/update/${t.id}`}>Edit</Link>
                    <Link className="btn btn-danger btn-sm" to={`/delete/${t.id}`}>Delete</Link>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
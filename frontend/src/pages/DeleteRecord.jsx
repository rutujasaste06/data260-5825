import React from "react";
import { Link, useParams } from "react-router-dom";

export default function DeleteRecord({ trials, onDelete }) {
  const { id } = useParams();
  const existing = trials.find((t) => t.id === Number(id));

  if (!existing) return <p className="empty">Trial not found.</p>;

  return (
    <div className="card narrow">
      <h2>Delete Trial #{id}</h2>
      <p className="subtitle">This action cannot be undone.</p>
      <p>
        <strong>{existing.trial_title}</strong>{" "}
        <span className="badge">{existing.nct_number}</span>
      </p>
      <div className="form-actions">
        <button className="btn btn-danger" onClick={() => onDelete(Number(id))}>
          Delete Trial
        </button>
        <Link className="btn btn-outline" to="/">Cancel</Link>
      </div>
    </div>
  );
}
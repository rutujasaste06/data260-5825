import React, { useState } from "react";
import { Link, useParams } from "react-router-dom";

export default function UpdateRecord({ trials, onUpdate }) {
  const { id } = useParams();
  const existing = trials.find((t) => t.id === Number(id));

  const [trialTitle, setTrialTitle] = useState(existing ? existing.trial_title : "");
  const [nctNumber, setNctNumber] = useState(existing ? existing.nct_number : "");

  if (!existing) return <p className="empty">Trial not found.</p>;

  async function handleSubmit(e) {
    e.preventDefault();
    await onUpdate(Number(id), { trial_title: trialTitle, nct_number: nctNumber });
  }

  return (
    <div className="card narrow">
      <h2>Update Trial #{id}</h2>
      <p className="subtitle">Change the details below and save.</p>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="title">Trial Title</label>
          <input id="title" value={trialTitle}
            onChange={(e) => setTrialTitle(e.target.value)} required />
        </div>
        <div className="form-group">
          <label htmlFor="nct">NCT Number</label>
          <input id="nct" value={nctNumber}
            onChange={(e) => setNctNumber(e.target.value)} required />
        </div>
        <div className="form-actions">
          <button className="btn btn-primary" type="submit">Update Trial</button>
          <Link className="btn btn-outline" to="/">Cancel</Link>
        </div>
      </form>
    </div>
  );
}
import React, { useState } from "react";
import { Link } from "react-router-dom";

export default function CreateRecord({ onAdd }) {
  const [trialTitle, setTrialTitle] = useState("");
  const [nctNumber, setNctNumber] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    await onAdd({ trial_title: trialTitle, nct_number: nctNumber });
  }

  return (
    <div className="card narrow">
      <h2>Add Clinical Trial</h2>
      <p className="subtitle">Enter the details of the new trial.</p>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="title">Trial Title</label>
          <input id="title" placeholder="e.g. Metformin Study"
            value={trialTitle} onChange={(e) => setTrialTitle(e.target.value)} required />
        </div>
        <div className="form-group">
          <label htmlFor="nct">NCT Number</label>
          <input id="nct" placeholder="e.g. NCT04567890"
            value={nctNumber} onChange={(e) => setNctNumber(e.target.value)} required />
        </div>
        <div className="form-actions">
          <button className="btn btn-primary" type="submit">Add Trial</button>
          <Link className="btn btn-outline" to="/">Cancel</Link>
        </div>
      </form>
    </div>
  );
}
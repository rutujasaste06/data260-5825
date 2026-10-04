import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useDispatch } from "react-redux";
import { createTrial } from "../store/trialsSlice";

export default function CreateRecord() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const [trialTitle, setTrialTitle] = useState("");
  const [nctNumber, setNctNumber] = useState("");
  const [slots, setSlots] = useState(10);
  const [sponsorId, setSponsorId] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    const result = await dispatch(createTrial({
      trial_title: trialTitle,
      nct_number: nctNumber,
      available_slots: Number(slots),
      sponsor_id: sponsorId === "" ? null : Number(sponsorId),
    }));
    if (createTrial.fulfilled.match(result)) navigate("/");
    else setError(String(result.payload));
  }

  return (
    <div className="card narrow">
      <h2>Add Clinical Trial</h2>
      {error && <div className="alert-error">{error}</div>}
      <form onSubmit={handleSubmit}>
        <div className="form-group"><label>Trial Title</label>
          <input value={trialTitle} onChange={(e) => setTrialTitle(e.target.value)} required /></div>
        <div className="form-group"><label>NCT Number</label>
          <input value={nctNumber} onChange={(e) => setNctNumber(e.target.value)} required /></div>
        <div className="form-group"><label>Available Slots</label>
          <input type="number" min="0" value={slots} onChange={(e) => setSlots(e.target.value)} /></div>
        <div className="form-group"><label>Sponsor ID (optional)</label>
          <input type="number" value={sponsorId} onChange={(e) => setSponsorId(e.target.value)} /></div>
        <div className="form-actions">
          <button className="btn btn-primary" type="submit">Add Trial</button>
          <Link className="btn btn-outline" to="/">Cancel</Link>
        </div>
      </form>
    </div>
  );
}
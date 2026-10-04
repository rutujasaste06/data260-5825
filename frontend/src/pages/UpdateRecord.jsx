import React, { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { updateTrial } from "../store/trialsSlice";

export default function UpdateRecord() {
  const { id } = useParams();
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const existing = useSelector((s) => s.trials.items.find((t) => t.id === Number(id)));

  const [trialTitle, setTrialTitle] = useState(existing ? existing.trial_title : "");
  const [nctNumber, setNctNumber] = useState(existing ? existing.nct_number : "");
  const [slots, setSlots] = useState(existing ? existing.available_slots : 10);
  const [sponsorId, setSponsorId] = useState(existing && existing.sponsor_id ? existing.sponsor_id : "");
  const [error, setError] = useState("");

  if (!existing) return <p className="empty">Trial not found.</p>;

  async function handleSubmit(e) {
    e.preventDefault();
    const result = await dispatch(updateTrial({
      id: Number(id),
      data: {
        trial_title: trialTitle,
        nct_number: nctNumber,
        available_slots: Number(slots),
        sponsor_id: sponsorId === "" ? null : Number(sponsorId),
      },
    }));
    if (updateTrial.fulfilled.match(result)) navigate("/");
    else setError(String(result.payload));
  }

  return (
    <div className="card narrow">
      <h2>Update Trial #{id}</h2>
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
          <button className="btn btn-primary" type="submit">Update Trial</button>
          <Link className="btn btn-outline" to="/">Cancel</Link>
        </div>
      </form>
    </div>
  );
}
import React from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { deleteTrial } from "../store/trialsSlice";

export default function DeleteRecord() {
  const { id } = useParams();
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const existing = useSelector((s) => s.trials.items.find((t) => t.id === Number(id)));

  if (!existing) return <p className="empty">Trial not found.</p>;

  async function handleDelete() {
    await dispatch(deleteTrial(Number(id)));
    navigate("/");
  }

  return (
    <div className="card narrow">
      <h2>Delete Trial #{id}</h2>
      <p><strong>{existing.trial_title}</strong> <span className="badge">{existing.nct_number}</span></p>
      <div className="form-actions">
        <button className="btn btn-danger" onClick={handleDelete}>Delete Trial</button>
        <Link className="btn btn-outline" to="/">Cancel</Link>
      </div>
    </div>
  );
}
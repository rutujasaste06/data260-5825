const API_BASE = "http://localhost:8425";
const createSubmissionCounter = () => {
  let count = 0;
  return () => {
    count++;
    return count;
  };
};

const trackSubmission = createSubmissionCounter();

let trials = [];

const els = {
  form: document.getElementById("trialForm"),
  loadingState: document.getElementById("loadingState"),
  errorState: document.getElementById("errorState"),
  emptyState: document.getElementById("emptyState"),
  trialList: document.getElementById("trialList"),
  trialCount: document.getElementById("trialCount"),
  searchInput: document.getElementById("searchInput"),
  retryButton: document.getElementById("retryButton"),
  descField: document.getElementById("trialDescription"),
  descHint: document.getElementById("hint-trialDescription"),
};

const showState = (state) => {
  els.loadingState.hidden = state !== "loading";
  els.errorState.hidden = state !== "error";
  els.emptyState.hidden = state !== "empty";
  els.trialList.hidden = state !== "list";
};

const escapeHtml = (str) =>
  str.replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));

const renderList = (list) => {
  els.trialCount.textContent = trials.length;
  if (list.length === 0) {
    showState("empty");
    els.trialList.innerHTML = "";
    return;
  }
  showState("list");
  els.trialList.innerHTML = list
    .map(
      (t) => `
      <li class="trial-row">
        <div class="trial-row-top">
          <span class="trial-title">${escapeHtml(t.trialTitle)}</span>
          <span class="trial-phase">${escapeHtml(t.trialPhase)}</span>
        </div>
        <span class="trial-nct">${escapeHtml(t.nctNumber)}</span>
        <p class="trial-desc">${escapeHtml(t.trialDescription)}</p>
      </li>`
    )
    .join("");
};

const loadTrials = () => {
  showState("loading");
  fetch(`${API_BASE}/trials`)
    .then((res) => {
      if (!res.ok) throw new Error("Server error");
      return res.json();
    })
    .then((data) => {
      trials = data;
      renderList(trials);
    })
    .catch((err) => {
      console.error("Failed to load trials:", err);
      showState("error");
    });
};

els.retryButton.addEventListener("click", loadTrials);

els.searchInput.addEventListener("input", (e) => {
  const q = e.target.value.trim().toLowerCase();
  const filtered = q
    ? trials.filter(
        (t) =>
          t.trialTitle.toLowerCase().includes(q) ||
          t.nctNumber.toLowerCase().includes(q)
      )
    : trials;
  renderList(filtered);
});

els.descField.addEventListener("input", () => {
  els.descHint.textContent = `${els.descField.value.length} / 25 characters minimum`;
});


const validateForm = (event) => {
  event.preventDefault();

  const description = document.getElementById("trialDescription").value;
  const agreeChecked = document.getElementById("agreeTerms").checked;

  if (description.length <= 25) {
    alert("Trial Description must be more than 25 characters.");
    return;
  }

  if (!agreeChecked) {
    alert("You must agree to the terms and conditions.");
    return;
  }

  const formData = {
    trialTitle: document.getElementById("trialTitle").value,
    nctNumber: document.getElementById("nctNumber").value,
    submitterEmail: document.getElementById("submitterEmail").value,
    trialDescription: description,
    trialPhase: document.getElementById("trialPhase").value,
    agreeTerms: agreeChecked,
  };

  const jsonString = JSON.stringify(formData);
  console.log("Form data as JSON string:", jsonString);


  const parsedData = JSON.parse(jsonString);
  const { trialTitle, submitterEmail } = parsedData;
  console.log("Trial Title:", trialTitle);
  console.log("Submitter Email:", submitterEmail);

  const updatedData = { ...parsedData, submissionDate: new Date().toString() };
  console.log("Updated data with submission date:", updatedData);

  const submissionCount = trackSubmission();
  console.log("Submission count:", submissionCount);


  // --Send data to real FastAPI backend 
  fetch(`${API_BASE}/trials`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      trialTitle: formData.trialTitle,
      nctNumber: formData.nctNumber,
      submitterEmail: formData.submitterEmail,
      trialDescription: formData.trialDescription,
      trialPhase: formData.trialPhase,
    }),
  })
    .then((res) => {
      if (!res.ok) throw new Error("Failed to add trial");
      els.form.reset();
      els.descHint.textContent = "0 / 25 characters minimum";
      loadTrials();
    })
    .catch((err) => {
      console.error("Submission failed:", err);
      alert("Could not save the trial. Check that the backend is running.");
    });
};

els.form.addEventListener("submit", validateForm);


loadTrials();
// ---------- Update trial 1 ----------

document.getElementById("updateTrial1Btn").addEventListener("click", () => {
  const current = trials.find((t) => t.id === 1);

  const newTitle = prompt("Trial Title:", current ? current.trialTitle : "");
  if (!newTitle) return;

  const newNct = prompt("NCT Number:", current ? current.nctNumber : "");
  if (!newNct) return;

  const newEmail = prompt("Submitter Email:", current ? current.submitterEmail : "");
  if (!newEmail) return;

  const newDescription = prompt("Trial Description:", current ? current.trialDescription : "");
  if (!newDescription || newDescription.length <= 25) {
    alert("Trial Description must be more than 25 characters.");
    return;
  }

  const newPhase = prompt("Trial Phase (Phase I / Phase II / Phase III / Phase IV):", current ? current.trialPhase : "");
  if (!["Phase I", "Phase II", "Phase III", "Phase IV"].includes(newPhase)) {
    alert("Please enter a valid phase: Phase I, Phase II, Phase III, or Phase IV.");
    return;
  }

  fetch(`${API_BASE}/trials/1`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      trialTitle: newTitle,
      nctNumber: newNct,
      submitterEmail: newEmail,
      trialDescription: newDescription,
      trialPhase: newPhase,
    }),
  })
    .then((res) => {
      if (!res.ok) throw new Error("Update failed");
      loadTrials();
    })
    .catch((err) => {
      console.error("Update failed:", err);
      alert("Could not update trial 1.");
    });
});

// ---------- Delete highest-ID trial ----------

document.getElementById("deleteHighestBtn").addEventListener("click", () => {
  if (!confirm("Delete the trial with the highest ID?")) return;

  fetch(`${API_BASE}/trials/highest`, { method: "DELETE" })
    .then((res) => {
      if (!res.ok) throw new Error("Delete failed");
      loadTrials();
    })
    .catch((err) => {
      console.error("Delete failed:", err);
      alert("Could not delete trial.");
    });
});
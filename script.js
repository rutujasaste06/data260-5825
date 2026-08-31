const createSubmissionCounter = () => {
    let count = 0;
    return () => {
        count++;
        return count;
    };
};

const trackSubmission = createSubmissionCounter();

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
        agreeTerms: agreeChecked
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
};

document.getElementById("trialForm").addEventListener("submit", validateForm);
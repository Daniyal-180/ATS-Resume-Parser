document.addEventListener("DOMContentLoaded", () => {
  const jdForm = document.getElementById("jdForm");
  const resumeResults = document.getElementById("resumeResults");

  jdForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const formData = new FormData(jdForm);

    try {
      // Send to backend (updated route)
      const response = await fetch("/jd_parser", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const data = await response.json();

      // Clear previous results
      resumeResults.innerHTML = "";

      if (data.resumes && data.resumes.length > 0) {
        data.resumes.forEach((resume) => {
          const card = document.createElement("div");
          card.className = "resume-card";

          card.innerHTML = `
            <h3>${resume.name}</h3>
            <p><strong>Score:</strong> ${resume.score}</p>
            <p><strong>Skills:</strong> ${resume.skills}</p>
            <p><strong>Experience:</strong> ${resume.experience} years</p>
            <p><strong>Education:</strong> ${resume.education}</p>
          `;

          resumeResults.appendChild(card);
        });
      } else {
        resumeResults.innerHTML = `<p>No matching resumes found.</p>`;
      }
    } catch (error) {
      resumeResults.innerHTML = `<p style="color:red;">Error: ${error.message}</p>`;
      console.error("Error fetching resumes:", error);
    }
  });
});

document.addEventListener("DOMContentLoaded", () => {
  const jdForm = document.getElementById("jdForm");
  const resumeResults = document.getElementById("resumeResults");

  jdForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const formData = new FormData(jdForm);

    try {
      const response = await fetch("/jd_parser", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      // Parse returned HTML
      const html = await response.text();
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, "text/html");

      // Find the new resumeResults div in the response
      const newResults = doc.querySelector("#resumeResults");

      if (newResults) {
        resumeResults.innerHTML = newResults.innerHTML;
      } else {
        resumeResults.innerHTML = `<p>No matching resumes found.</p>`;
      }
    } catch (error) {
      resumeResults.innerHTML = `<p style="color:red;">Error: ${error.message}</p>`;
      console.error("Error fetching resumes:", error);
    }
  });
});

document.addEventListener("DOMContentLoaded", () => {
  const uploadForm = document.getElementById("uploadForm");
  const uploadResult = document.getElementById("uploadResult");
  const askForm = document.getElementById("askForm");
  const pdfIdInput = document.getElementById("pdfIdInput");
  const questionInput = document.getElementById("questionInput");
  const chatBox = document.getElementById("chatBox");
  const summForm = document.getElementById("summForm");
  const summResult = document.getElementById("summResult");
  const pdfIdForSumm = document.getElementById("pdfIdForSumm");

  uploadForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fileInput = document.getElementById("pdfFile");
    if (!fileInput.files.length) return alert("choose a pdf");
    const form = new FormData();
    form.append("file", fileInput.files[0]);
    const resp = await fetch("/upload", { method: "POST", body: form });
    const json = await resp.json();
    if (json.status === "ok") {
      uploadResult.innerText = `Indexed. pdf_id: ${json.pdf_id}`;
      pdfIdInput.value = json.pdf_id;
      pdfIdForSumm.value = json.pdf_id;
    } else {
      uploadResult.innerText = `Error: ${JSON.stringify(json)}`;
    }
  });

  askForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const pdf_id = pdfIdInput.value.trim();
    const q = questionInput.value.trim();
    if (!pdf_id || !q) return alert("provide pdf id and question");
    // send form
    const body = new FormData();
    body.append("pdf_id", pdf_id);
    body.append("question", q);
    const resp = await fetch("/ask", { method: "POST", body });
    const j = await resp.json();
    chatBox.innerHTML += `<div><strong class='user'>Q:</strong> ${q}</div>`;
    chatBox.innerHTML += `<div><strong class='ai'>A:</strong> ${j.answer}</div>`;
    questionInput.value = "";
  });

  summForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const pdf_id = pdfIdForSumm.value.trim();
    if (!pdf_id) return alert("provide pdf id");
    const body = new FormData();
    body.append("pdf_id", pdf_id);
    const resp = await fetch("/summarize", { method: "POST", body });
    const j = await resp.json();
    if (j.summary) summResult.innerText = j.summary;
    else summResult.innerText = JSON.stringify(j);
  });
});

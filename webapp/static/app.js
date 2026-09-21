document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-add-row]").forEach((button) => {
    const targetId = button.getAttribute("data-add-row");
    const tbody = document.getElementById(targetId);
    const template = document.getElementById(targetId + "-template");
    button.addEventListener("click", () => {
      tbody.appendChild(template.content.cloneNode(true));
    });
  });

  document.addEventListener("click", (event) => {
    if (event.target.matches(".remove-row")) {
      const tbody = event.target.closest("tbody");
      const row = event.target.closest("tr");
      if (tbody.querySelectorAll("tr").length > 1) {
        row.remove();
      } else {
        row.querySelectorAll("input").forEach((input) => (input.value = ""));
      }
    }
  });
});

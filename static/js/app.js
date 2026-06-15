document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".js-markdown").forEach((textarea) => {
        textarea.removeAttribute("required");

        if (window.EasyMDE) {
            new EasyMDE({
                element: textarea,
                spellChecker: false,
                status: false,
                minHeight: "220px"
            });
        }
    });
});

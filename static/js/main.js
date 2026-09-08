// main.js — students will add JavaScript here as features are built

(function () {
    var VIDEO_EMBED_URL = "https://www.youtube.com/embed/dQw4w9WgXcQ"; // placeholder — swap for the real demo video

    var trigger = document.getElementById("see-how-it-works-btn");
    var overlay = document.getElementById("how-it-works-overlay");
    var closeBtn = document.getElementById("how-it-works-close");
    var video = document.getElementById("how-it-works-video");

    if (!trigger || !overlay || !closeBtn || !video) return;

    function openModal() {
        video.src = VIDEO_EMBED_URL + "?autoplay=1";
        overlay.hidden = false;
    }

    function closeModal() {
        overlay.hidden = true;
        video.src = ""; // unload the iframe so the video stops playing
    }

    trigger.addEventListener("click", openModal);
    closeBtn.addEventListener("click", closeModal);

    overlay.addEventListener("click", function (event) {
        if (event.target === overlay) closeModal();
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && !overlay.hidden) closeModal();
    });
})();

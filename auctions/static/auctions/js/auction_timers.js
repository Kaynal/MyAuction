document.addEventListener("DOMContentLoaded", function() {
    // Находим все элементы таймеров (и на детальной странице, и в списках карточек)
    const countdownElements = document.querySelectorAll(".card-countdown, #countdown");
    if (countdownElements.length === 0) return;

    function updateTimers() {
        const now = new Date().getTime();

        countdownElements.forEach(function(el) {
            const endTimeStr = el.getAttribute("data-endtime");
            if (!endTimeStr) return;

            const endTime = new Date(endTimeStr).getTime();
            const distance = endTime - now;

            // Если время истекло
            if (distance < 0) {
                if (el.id === "countdown") {
                    el.innerHTML = "ЧАС ИСТЁК!";
                    if (!el.dataset.reloaded) {
                        el.dataset.reloaded = "true";
                        setTimeout(() => { location.reload(); }, 1000);
                    }
                } else {
                    el.innerHTML = "Закрито";
                    el.style.color = "#dc3545";
                }
                return;
            }

            const days = Math.floor(distance / (1000 * 60 * 60 * 24));
            const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((distance % (1000 * 60)) / 1000);

            let text = "";
            if (days > 0) text += days + "д ";
            text += hours + "г " + minutes + "м " + seconds + "с";
            
            el.innerHTML = text;
        });
    }

    updateTimers();
    setInterval(updateTimers, 1000);
});
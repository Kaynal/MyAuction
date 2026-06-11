function switchAuctionsTab(mode) {
    const tabActive = document.getElementById('tab-active');
    const tabCompleted = document.getElementById('tab-completed');
    const subtitle = document.getElementById('auctions-subtitle');
    
    const activeAuctions = document.querySelectorAll('.js-active-auction');
    const completedAuctions = document.querySelectorAll('.js-completed-auction');
    const emptyState = document.getElementById('tab-empty-state');

    if (mode === 'active') {
        // Керування класами кнопок (підсвічування)
        tabActive.classList.add('active');
        tabCompleted.classList.remove('active');
        
        // Зміна підзаголовку
        subtitle.textContent = "Active auctions that you created";
        
        // Показуємо активні, ховаємо завершені
        activeAuctions.forEach(item => item.style.display = 'flex');
        completedAuctions.forEach(item => item.style.display = 'none');
        
        // Перевірка на порожнечу у вкладці "Active"
        if (activeAuctions.length === 0) {
            emptyState.style.display = 'block';
        } else {
            emptyState.style.display = 'none';
        }

    } else if (mode === 'completed') {
        // Керування класами кнопок
        tabActive.classList.remove('active');
        tabCompleted.classList.add('active');
        
        // Зміна підзаголовку
        subtitle.textContent = "Completed auctions that you created";
        
        // Показуємо завершені, ховаємо активні
        activeAuctions.forEach(item => item.style.display = 'none');
        completedAuctions.forEach(item => item.style.display = 'flex');
        
        // Перевірка на порожнечу у вкладці "Completed"
        if (completedAuctions.length === 0) {
            emptyState.style.display = 'block';
        } else {
            emptyState.style.display = 'none';
        }
    }
}

// Ініціалізація сторінки: при першому завантаженні ховаємо завершені аукціони, 
// щоб користувач одразу бачив саме вкладку Active лотів.
document.addEventListener("DOMContentLoaded", function() {
    switchAuctionsTab('active');
});
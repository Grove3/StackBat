/**
 * Theme Management for Yamble GUI
 */

/**
 * Toggle between dark and light mode
 * @returns {boolean} True if dark mode is active, false otherwise
 */
function toggleTheme() {
    document.body.classList.toggle('dark-mode');
    const isDark = document.body.classList.contains('dark-mode');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
    return isDark;
}

/**
 * Get the current theme
 * @returns {string} 'dark' or 'light'
 */
function getCurrentTheme() {
    return document.body.classList.contains('dark-mode') ? 'dark' : 'light';
}

/**
 * Set the theme explicitly
 * @param {string} theme - 'dark' or 'light'
 */
function setTheme(theme) {
    if (theme === 'dark') {
        document.body.classList.add('dark-mode');
    } else {
        document.body.classList.remove('dark-mode');
    }
    localStorage.setItem('theme', theme);
}

/**
 * Initialize theme on page load
 */
function initializeTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    setTheme(savedTheme);
}

// Load theme preference when DOM is ready
window.addEventListener('DOMContentLoaded', initializeTheme);
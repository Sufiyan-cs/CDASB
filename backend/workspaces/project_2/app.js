// State
let todos = [];
let theme = 'dark';

// DOM Elements
const todoForm = document.getElementById('todo-form');
const todoInput = document.getElementById('todo-input');
const todoList = document.getElementById('todo-list');
const themeToggle = document.getElementById('theme-toggle');
const emptyState = document.getElementById('empty-state');
const completedCountEl = document.getElementById('completed-count');
const totalCountEl = document.getElementById('total-count');
const progressBar = document.getElementById('progress-bar');
const sunIcon = document.getElementById('sun-icon');
const moonIcon = document.getElementById('moon-icon');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadTheme();
    render();
});

// Theme Management
function loadTheme() {
    const savedTheme = localStorage.getItem('todo-theme');
    if (savedTheme) {
        theme = savedTheme;
    } else {
        theme = 'dark';
    }
    applyTheme();
}

function applyTheme() {
    const body = document.body;
    if (theme === 'light') {
        body.classList.add('light-mode');
        sunIcon.classList.remove('hidden');
        moonIcon.classList.add('hidden');
    } else {
        body.classList.remove('light-mode');
        sunIcon.classList.add('hidden');
        moonIcon.classList.remove('hidden');
    }
}

function toggleTheme() {
    theme = theme === 'light' ? 'dark' : 'light';
    localStorage.setItem('todo-theme', theme);
    applyTheme();
}

// Todo Management
function addTodo(text) {
    const todo = {
        id: Date.now(),
        text: text,
        completed: false,
        createdAt: new Date()
    };
    todos.push(todo);
    render();
}

function toggleTodo(id) {
    const todo = todos.find(t => t.id === id);
    if (todo) {
        todo.completed = !todo.completed;
        render();
    }
}

function deleteTodo(id) {
    const todoElement = document.querySelector(`[data-id="${id}"]`);
    if (todoElement) {
        todoElement.classList.add('removing');
        setTimeout(() => {
            todos = todos.filter(t => t.id !== id);
            render();
        }, 300);
    }
}

// Render
function render() {
    // Clear list
    todoList.innerHTML = '';
    
    // Show/hide empty state
    if (todos.length === 0) {
        emptyState.style.display = 'block';
    } else {
        emptyState.style.display = 'none';
    }
    
    // Render todos
    todos.forEach(todo => {
        const li = document.createElement('li');
        li.className = 'todo-item group flex items-center gap-4 p-4 hover:bg-white/5 transition-colors duration-200';
        li.setAttribute('data-id', todo.id);
        
        // Checkbox
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'checkbox-custom shrink-0';
        checkbox.checked = todo.completed;
        checkbox.addEventListener('change', () => toggleTodo(todo.id));
        
        // Text
        const textSpan = document.createElement('span');
        textSpan.className = `flex-1 text-sm transition-all duration-200 ${
            todo.completed 
                ? 'text-slate-500 line-through' 
                : 'text-white'
        }`;
        textSpan.textContent = todo.text;
        
        // Delete button
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'delete-btn p-2 rounded-lg hover:bg-red-500/10 text-slate-500 hover:text-red-400 transition-all duration-200 shrink-0';
        deleteBtn.innerHTML = `
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
            </svg>
        `;
        deleteBtn.addEventListener('click', () => deleteTodo(todo.id));
        
        li.appendChild(checkbox);
        li.appendChild(textSpan);
        li.appendChild(deleteBtn);
        todoList.appendChild(li);
    });
    
    // Update stats
    updateStats();
}

function updateStats() {
    const total = todos.length;
    const completed = todos.filter(t => t.completed).length;
    const percentage = total > 0 ? (completed / total) * 100 : 0;
    
    completedCountEl.textContent = completed;
    totalCountEl.textContent = total;
    progressBar.style.width = `${percentage}%`;
}

// Event Handlers
function handleSubmit(e) {
    e.preventDefault();
    const text = todoInput.value.trim();
    if (text) {
        addTodo(text);
        todoInput.value = '';
        todoInput.focus();
    }
}

// Event Listeners
todoForm.addEventListener('submit', handleSubmit);
themeToggle.addEventListener('click', toggleTheme);

// Keyboard shortcut - Ctrl/Cmd + Enter to focus input
document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === '/') {
        e.preventDefault();
        todoInput.focus();
    }
});

// Initial render
render();
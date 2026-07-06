(function() {
    'use strict';

    // State
    let todos = [];
    let currentTheme = 'light';

    // DOM Elements
    const themeToggle = document.getElementById('theme-toggle');
    const todoInput = document.getElementById('todo-input');
    const addTodoBtn = document.getElementById('add-todo');
    const todoList = document.getElementById('todo-list');
    const html = document.documentElement;

    // Initialize
    function init() {
        loadTheme();
        loadTodos();
        renderTodoList();
        bindEvents();
        todoInput.focus();
    }

    // Theme Management
    function loadTheme() {
        const savedTheme = localStorage.getItem('theme');
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        currentTheme = savedTheme || (prefersDark ? 'dark' : 'light');
        applyTheme(currentTheme);
    }

    function applyTheme(theme) {
        html.setAttribute('data-theme', theme);
        currentTheme = theme;
        localStorage.setItem('theme', theme);
    }

    function toggleTheme() {
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        applyTheme(newTheme);
        themeToggle.style.transform = 'scale(0.9)';
        setTimeout(() => {
            themeToggle.style.transform = '';
        }, 150);
    }

    // Todo Management
    function loadTodos() {
        const savedTodos = localStorage.getItem('todos');
        if (savedTodos) {
            try {
                todos = JSON.parse(savedTodos);
            } catch (e) {
                console.error('Failed to parse todos:', e);
                todos = [];
            }
        }
    }

    function saveTodos() {
        localStorage.setItem('todos', JSON.stringify(todos));
    }

    function generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    }

    function addTodo() {
        const text = todoInput.value.trim();
        if (!text) return;

        const todo = {
            id: generateId(),
            text: text,
            completed: false,
            createdAt: Date.now()
        };

        todos.unshift(todo);
        saveTodos();
        renderTodoList();
        todoInput.value = '';
        todoInput.focus();

        // Animate new item
        const newItem = todoList.firstElementChild;
        if (newItem) {
            newItem.style.animation = 'none';
            newItem.offsetHeight; // Trigger reflow
            newItem.style.animation = 'slideIn 0.3s ease-out';
        }
    }

    function deleteTodo(id) {
        const item = todoList.querySelector(`[data-id="${id}"]`);
        if (item) {
            item.style.animation = 'fadeOut 0.2s ease-in forwards';
            setTimeout(() => {
                todos = todos.filter(todo => todo.id !== id);
                saveTodos();
                renderTodoList();
            }, 200);
        }
    }

    function toggleTodo(id) {
        const todo = todos.find(t => t.id === id);
        if (todo) {
            todo.completed = !todo.completed;
            saveTodos();
            renderTodoList();
        }
    }

    // Rendering
    function renderTodoList() {
        todoList.innerHTML = '';

        if (todos.length === 0) {
            renderEmptyState();
            return;
        }

        const fragment = document.createDocumentFragment();

        todos.forEach((todo, index) => {
            const li = createTodoElement(todo);
            li.style.animationDelay = `${index * 50}ms`;
            fragment.appendChild(li);
        });

        todoList.appendChild(fragment);
    }

    function createTodoElement(todo) {
        const li = document.createElement('li');
        li.className = 'todo-item' + (todo.completed ? ' completed' : '');
        li.setAttribute('data-id', todo.id);

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'todo-checkbox';
        checkbox.checked = todo.completed;
        checkbox.setAttribute('aria-label', todo.completed ? 'Mark as incomplete' : 'Mark as complete');
        checkbox.addEventListener('change', () => toggleTodo(todo.id));

        const span = document.createElement('span');
        span.className = 'todo-text';
        span.textContent = todo.text;

        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'todo-delete';
        deleteBtn.setAttribute('aria-label', 'Delete todo');
        deleteBtn.innerHTML = `
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <polyline points="3 6 5 6 21 6"></polyline>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
        `;
        deleteBtn.addEventListener('click', () => deleteTodo(todo.id));

        li.appendChild(checkbox);
        li.appendChild(span);
        li.appendChild(deleteBtn);

        return li;
    }

    function renderEmptyState() {
        const li = document.createElement('li');
        li.className = 'empty-state';
        li.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M9 11l3 3L22 4"></path>
                <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path>
            </svg>
            <p>No todos yet</p>
            <span>Add your first task above</span>
        `;
        todoList.appendChild(li);
    }

    // Event Binding
    function bindEvents() {
        themeToggle.addEventListener('click', toggleTheme);

        addTodoBtn.addEventListener('click', addTodo);

        todoInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                addTodo();
            }
        });

        // Listen for system theme changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (!localStorage.getItem('theme')) {
                applyTheme(e.matches ? 'dark' : 'light');
            }
        });

        // Keyboard navigation for todo items
        todoList.addEventListener('keydown', (e) => {
            const item = e.target.closest('.todo-item');
            if (!item) return;

            if (e.key === 'Delete' || e.key === 'Backspace') {
                if (e.target.classList.contains('todo-text') || e.target.classList.contains('todo-checkbox')) {
                    e.preventDefault();
                    deleteTodo(item.dataset.id);
                }
            }
        });
    }

    // Add fadeOut animation dynamically
    const style = document.createElement('style');
    style.textContent = `
        @keyframes fadeOut {
            from { opacity: 1; transform: translateX(0); }
            to { opacity: 0; transform: translateX(-20px); }
        }
    `;
    document.head.appendChild(style);

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
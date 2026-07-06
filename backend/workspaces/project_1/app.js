// State variables
let todos = [];
let mode = 'light';

// DOM Elements
const todoList = document.getElementById('todo-list');
const todoInput = document.getElementById('todo-input');
const addTodoBtn = document.getElementById('add-todo');
const modeToggleBtn = document.getElementById('mode-toggle');
const todoForm = document.getElementById('todo-form');
const emptyState = document.getElementById('empty-state');
const todoCounter = document.getElementById('todo-counter');

// Initialize mode from localStorage if available
function initializeMode() {
    const savedMode = localStorage.getItem('todo-app-mode');
    if (savedMode) {
        mode = savedMode;
        if (mode === 'dark') {
            document.body.classList.add('dark');
        }
    } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        mode = 'dark';
        document.body.classList.add('dark');
    }
}

// Load todos from localStorage
function loadTodos() {
    const savedTodos = localStorage.getItem('todo-app-todos');
    if (savedTodos) {
        try {
            todos = JSON.parse(savedTodos);
        } catch (e) {
            todos = [];
        }
    }
}

// Save todos to localStorage
function saveTodos() {
    localStorage.setItem('todo-app-todos', JSON.stringify(todos));
}

// Update counter badge
function updateCounter() {
    const count = todos.length;
    todoCounter.textContent = `${count} item${count !== 1 ? 's' : ''}`;
    
    // Pulse animation
    todoCounter.classList.add('pulse');
    setTimeout(() => {
        todoCounter.classList.remove('pulse');
    }, 300);
}

// Toggle empty state visibility
function toggleEmptyState() {
    if (todos.length === 0) {
        emptyState.classList.remove('hidden');
        todoList.classList.add('hidden');
    } else {
        emptyState.classList.add('hidden');
        todoList.classList.remove('hidden');
    }
}

// Render todo list
function render() {
    todoList.innerHTML = '';
    
    todos.forEach((todo, index) => {
        const todoItem = document.createElement('li');
        todoItem.classList.add(
            'todo-item',
            'todo-item-enter',
            'flex',
            'items-center',
            'justify-between',
            'px-6',
            'py-4',
            'hover:bg-gray-50',
            'dark:hover:bg-gray-750',
            'transition-all',
            'duration-300',
            'group'
        );
        
        if (todo.completed) {
            todoItem.classList.add('completed');
        }
        
        // Left side: checkbox + text
        const leftDiv = document.createElement('div');
        leftDiv.classList.add('flex', 'items-center', 'space-x-3', 'flex-1', 'min-w-0');
        
        // Custom checkbox
        const checkbox = document.createElement('button');
        checkbox.classList.add(
            'w-5',
            'h-5',
            'rounded-md',
            'border-2',
            'flex',
            'items-center',
            'justify-center',
            'flex-shrink-0',
            'transition-all',
            'duration-200'
        );
        
        if (todo.completed) {
            checkbox.classList.add('bg-blue-500', 'border-blue-500');
            checkbox.innerHTML = `
                <svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"></path>
                </svg>
            `;
        } else {
            checkbox.classList.add('border-gray-300', 'dark:border-gray-500', 'hover:border-blue-400');
        }
        
        checkbox.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleTodo(index);
        });
        
        // Todo text
        const todoText = document.createElement('span');
        todoText.textContent = todo.text;
        todoText.classList.add(
            'text-sm',
            'text-gray-700',
            'dark:text-gray-200',
            'truncate',
            'transition-all',
            'duration-200'
        );
        
        if (todo.completed) {
            todoText.classList.add('line-through', 'text-gray-400', 'dark:text-gray-500');
        }
        
        leftDiv.appendChild(checkbox);
        leftDiv.appendChild(todoText);
        
        // Delete button
        const deleteBtn = document.createElement('button');
        deleteBtn.classList.add(
            'delete-btn',
            'flex-shrink-0',
            'w-8',
            'h-8',
            'rounded-lg',
            'flex',
            'items-center',
            'justify-center',
            'text-gray-400',
            'hover:text-white',
            'hover:bg-red-500',
            'transition-all',
            'duration-200'
        );
        deleteBtn.innerHTML = `
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
            </svg>
        `;
        deleteBtn.setAttribute('aria-label', 'Delete todo');
        deleteBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            deleteTodo(index);
        });
        
        todoItem.appendChild(leftDiv);
        todoItem.appendChild(deleteBtn);
        
        // Click on item to toggle completion
        todoItem.addEventListener('click', () => {
            toggleTodo(index);
        });
        
        todoList.appendChild(todoItem);
    });
    
    updateCounter();
    toggleEmptyState();
}

// Toggle todo completion
function toggleTodo(index) {
    todos[index].completed = !todos[index].completed;
    saveTodos();
    render();
}

// Delete todo
function deleteTodo(index) {
    todos.splice(index, 1);
    saveTodos();
    render();
}

// Handle form submission
function handleSubmit(e) {
    e.preventDefault();
    const text = todoInput.value.trim();
    
    if (text) {
        todos.push({
            text: text,
            completed: false,
            createdAt: new Date().toISOString()
        });
        saveTodos();
        render();
        todoInput.value = '';
        todoInput.focus();
    }
}

// Toggle dark/light mode
function toggleMode() {
    mode = mode === 'light' ? 'dark' : 'light';
    
    if (mode === 'dark') {
        document.body.classList.add('dark');
    } else {
        document.body.classList.remove('dark');
    }
    
    localStorage.setItem('todo-app-mode', mode);
}

// Event listeners
todoForm.addEventListener('submit', handleSubmit);
addTodoBtn.addEventListener('click', handleSubmit);
modeToggleBtn.addEventListener('click', toggleMode);

// Allow Enter key to submit
todoInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        handleSubmit(e);
    }
});

// Listen for system theme changes
if (window.matchMedia) {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        if (!localStorage.getItem('todo-app-mode')) {
            if (e.matches) {
                document.body.classList.add('dark');
                mode = 'dark';
            } else {
                document.body.classList.remove('dark');
                mode = 'light';
            }
        }
    });
}

// Initialize app
initializeMode();
loadTodos();
render();
todoInput.focus();
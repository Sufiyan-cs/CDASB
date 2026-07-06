let tasks = [];
let currentColumn = 'to-do';

const nextColumnMap = {
  'to-do': 'in-progress',
  'in-progress': 'done',
  'done': 'to-do'
};

const modalOverlay = document.getElementById('modal-overlay');
const taskForm = document.getElementById('task-form');
const openModalBtn = document.getElementById('open-modal-btn');
const closeModalBtn = document.getElementById('close-modal-btn');

function loadTasks() {
  const stored = localStorage.getItem('tasks');
  if (stored) {
    try {
      tasks = JSON.parse(stored);
    } catch (e) {
      tasks = [];
    }
  } else {
    tasks = [
      { id: Date.now() - 10000, title: 'Design system architecture', priority: 'high', column: 'to-do' },
      { id: Date.now() - 5000, title: 'Implement glassmorphism UI', priority: 'medium', column: 'in-progress' },
      { id: Date.now() - 1000, title: 'Deploy to production', priority: 'low', column: 'done' }
    ];
    saveTasks();
  }
}

function saveTasks() {
  localStorage.setItem('tasks', JSON.stringify(tasks));
}

function getPriorityClass(priority) {
  switch (priority) {
    case 'high': return 'priority-high';
    case 'medium': return 'priority-medium';
    case 'low': return 'priority-low';
    default: return 'priority-medium';
  }
}

function getPriorityColor(priority) {
  switch (priority) {
    case 'high': return '#ef4444';
    case 'medium': return '#f59e0b';
    case 'low': return '#10b981';
    default: return '#3b82f6';
  }
}

function createTaskElement(task) {
  const card = document.createElement('div');
  card.className = 'task-card';
  card.style.setProperty('--priority-color', getPriorityColor(task.priority));
  card.setAttribute('data-id', task.id);
  card.setAttribute('role', 'button');
  card.setAttribute('tabindex', '0');
  card.setAttribute('aria-label', 'Task: ' + task.title + '. Priority: ' + task.priority + '. Click to move to next column.');

  const title = document.createElement('div');
  title.className = 'task-title';
  title.textContent = task.title;

  const meta = document.createElement('div');
  meta.className = 'task-meta';

  const tag = document.createElement('span');
  tag.className = 'priority-tag ' + getPriorityClass(task.priority);
  tag.textContent = task.priority;

  const deleteBtn = document.createElement('button');
  deleteBtn.className = 'delete-btn';
  deleteBtn.setAttribute('aria-label', 'Delete task');
  deleteBtn.innerHTML = '<svg width=\'14\' height=\'14\' viewBox=\'0 0 24 24\' fill=\'none\' stroke=\'currentColor\' stroke-width=\'2.5\' stroke-linecap=\'round\' stroke-linejoin=\'round\'><polyline points=\'3 6 5 6 21 6\'></polyline><path d=\'M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2\'></path></svg>';

  deleteBtn.addEventListener('click', function(e) {
    e.stopPropagation();
    deleteTask(task.id);
  });

  const handleMove = function() {
    const next = nextColumnMap[task.column];
    if (next) {
      moveTask(task.id, next);
    }
  };

  card.addEventListener('click', handleMove);
  card.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleMove();
    }
  });

  meta.appendChild(tag);
  card.appendChild(title);
  card.appendChild(meta);
  card.appendChild(deleteBtn);

  return card;
}

function render() {
  const todoList = document.querySelector('#to-do .task-list');
  const inprogressList = document.querySelector('#in-progress .task-list');
  const doneList = document.querySelector('#done .task-list');

  todoList.innerHTML = '';
  inprogressList.innerHTML = '';
  doneList.innerHTML = '';

  const counts = { 'to-do': 0, 'in-progress': 0, 'done': 0 };

  tasks.forEach(function(task) {
    counts[task.column] = (counts[task.column] || 0) + 1;
    const el = createTaskElement(task);
    if (task.column === 'to-do') {
      todoList.appendChild(el);
    } else if (task.column === 'in-progress') {
      inprogressList.appendChild(el);
    } else if (task.column === 'done') {
      doneList.appendChild(el);
    }
  });

  document.querySelector('#to-do .task-count').textContent = counts['to-do'];
  document.querySelector('#in-progress .task-count').textContent = counts['in-progress'];
  document.querySelector('#done .task-count').textContent = counts['done'];

  [todoList, inprogressList, doneList].forEach(function(list) {
    if (list.children.length === 0) {
      const empty = document.createElement('div');
      empty.className = 'empty-state';
      empty.textContent = 'No tasks yet';
      list.appendChild(empty);
    }
  });
}

function addTask(title, priority) {
  const newTask = {
    id: Date.now(),
    title: title.trim(),
    priority: priority,
    column: 'to-do'
  };
  tasks.push(newTask);
  saveTasks();
  render();
}

function moveTask(taskId, newColumn) {
  const task = tasks.find(function(t) { return t.id === taskId; });
  if (task && newColumn) {
    task.column = newColumn;
    saveTasks();
    render();
  }
}

function deleteTask(taskId) {
  tasks = tasks.filter(function(t) { return t.id !== taskId; });
  saveTasks();
  render();
}

function addTaskModal() {
  modalOverlay.classList.add('active');
  document.getElementById('task-title').focus();
  document.body.style.overflow = 'hidden';
}

function closeTaskModal() {
  modalOverlay.classList.remove('active');
  document.body.style.overflow = '';
  taskForm.reset();
}

openModalBtn.addEventListener('click', addTaskModal);
closeModalBtn.addEventListener('click', closeTaskModal);

modalOverlay.addEventListener('click', function(e) {
  if (e.target === modalOverlay) {
    closeTaskModal();
  }
});

document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape' && modalOverlay.classList.contains('active')) {
    closeTaskModal();
  }
});

taskForm.addEventListener('submit', function(e) {
  e.preventDefault();
  const titleInput = document.getElementById('task-title');
  const priorityInput = document.getElementById('task-priority');

  const title = titleInput.value.trim();
  const priority = priorityInput.value;

  if (!title) return;

  addTask(title, priority);
  closeTaskModal();
});

loadTasks();
render();